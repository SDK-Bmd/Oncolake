"""Random Forest oncogene vs suppresseur (zone curated -> modele).
"""

import json
import joblib
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from oncolake.lake.warehouse import get_duckdb
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


DROP_COLS = ["accession", "gene", "label"]   # identifiants : jamais en features (fuite)


def load_curated():
    con = get_duckdb(read_only=True)
    df = con.execute("SELECT * FROM protein_features").pl()
    con.close()
    return df


def feature_names(df) -> list[str]:
    return [c for c in df.columns if c not in DROP_COLS]


def make_xy(df):
    X = df.drop(DROP_COLS).to_numpy()
    y = df["label"].to_numpy()
    return X, y


def build_model(n_estimators: int = 300, random_state: int = 42, max_depth: int | None = 5):
    """Random Forest regle pour un petit jeu de donnees.

    max_depth limite : sans plafond, 300 arbres sur ~300 exemples memorisent le bruit.
    class_weight='balanced' : les classes sont desequilibrees (225 / 179).
    """
    return RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        class_weight="balanced",
        random_state=random_state,
        n_jobs=-1,
    )


def train(test_size: float = 0.25, random_state: int = 42, n_estimators: int = 300,
          max_depth: int | None = 5) -> dict:
    df = load_curated()
    X, y = make_xy(df)
    names = feature_names(df)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y)

    clf = build_model(n_estimators, random_state, max_depth)
    clf.fit(X_train, y_train)

    # cross validation
    cv_rf = cross_val_score(clf, X, y, cv=5)
    cv_dummy = cross_val_score(DummyClassifier(strategy="most_frequent"), X, y, cv=5)
    # Regression logistique :
    logreg = make_pipeline(StandardScaler(),
                           LogisticRegression(max_iter=2000, class_weight="balanced"))
    cv_lr = cross_val_score(logreg, X, y, cv=5)

    # --- Diagnostic sur le holdout
    y_pred = clf.predict(X_test)
    cm = confusion_matrix(y_test, y_pred, labels=sorted(set(y)))
    report = classification_report(y_test, y_pred, zero_division=0)

    # --- Importance des features
    importances = sorted(zip(names, clf.feature_importances_),
                         key=lambda t: t[1], reverse=True)

    metrics = {
        "test_accuracy": round(float(clf.score(X_test, y_test)), 4),
        "cv_accuracy": round(float(cv_rf.mean()), 4),
        "cv_std": round(float(cv_rf.std()), 4),
        "baseline_accuracy": round(float(cv_dummy.mean()), 4),
        "logreg_cv_accuracy": round(float(cv_lr.mean()), 4),
        "beats_baseline": bool(cv_rf.mean() > cv_dummy.mean()),
        "n_samples": int(len(y)),
        "n_features": int(X.shape[1]),
        "confusion_matrix": cm.tolist(),
        "classes": sorted(set(y)),
        "top_features": [{"feature": f, "importance": round(float(i), 4)}
                         for f, i in importances[:10]],
    }

    # --- Metric
    print(f"\nRandom Forest   (CV 5 plis) : {cv_rf.mean():.3f} (+/- {cv_rf.std():.3f})")
    print(f"Regression log. (CV 5 plis) : {cv_lr.mean():.3f}")
    print(f"Baseline classe majoritaire : {cv_dummy.mean():.3f}")
    print(f"-> le modele bat la baseline : {'OUI' if metrics['beats_baseline'] else 'NON'}")
    print("\nMatrice de confusion (lignes = reel, colonnes = predit)")
    print(f"  classes : {metrics['classes']}")
    print(cm)
    print("\n" + report)
    print("Top 10 features :")
    for f, i in importances[:10]:
        print(f"  {f:24s} {i:.4f}")
    uniform = 1.0 / len(names)
    top = importances[0][1]
    print(f"\nImportance : {uniform:.4f} | max observee : {top:.4f}")
    if top < 2 * uniform:
        print("  -> aucune feature ne se distingue")

    (ROOT /"metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (ROOT /"data").mkdir(exist_ok=True)
    joblib.dump(clf, ROOT /"data" /"model.joblib")

    return metrics


if __name__ == "__main__":
    train()