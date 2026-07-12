"""Random Forest oncogene vs suppresseur (zone curated -> modele).
"""

from oncolake.lake.warehouse import get_duckdb
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

import json
from pathlib import Path

import joblib
from sklearn.dummy import DummyClassifier
from sklearn.model_selection import cross_val_score


def train(test_size=0.25, random_state=42, n_estimators=300):
  df = load_curated()
  X, y = make_xy(df)
  X_train, X_test, y_train, y_test = split_data(X, y, test_size, random_state)
  clf = train_model(X_train, y_train, n_estimators, random_state)
  test_acc = clf.score(X_test, y_test)
  cv_acc = cross_val_score(clf, X, y, cv=5).mean()
  baseline = cross_val_score(DummyClassifier(strategy="most_frequent"), X, y, cv=5).mean()

  metrics = {
      "test_accuracy": round(float(test_acc), 4),
      "cv_accuracy":   round(float(cv_acc), 4),
      "baseline_accuracy": round(float(baseline), 4),
      "n_samples":  int(len(y)),
      "n_features": int(X.shape[1]),
  }

  Path("metrics.json").write_text(json.dumps(metrics, indent=2))
  Path("data").mkdir(exist_ok=True)
  joblib.dump(clf, "data/model.joblib")
  print(metrics)
  return metrics

def feature_names(df):
    return [c for c in df.columns if c not in ("accession", "gene", "label")]

def train_model(X_train, y_train, n_estimators=300, random_state=42):
    clf = RandomForestClassifier(n_estimators = n_estimators,  random_state=random_state)  
    clf.fit(X_train, y_train)                                                       
    return clf

def split_data(X, y, test_size=0.25, random_state=42):
  X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=random_state, stratify=y)
  return X_train, X_test, y_train, y_test

def load_curated():
  con = get_duckdb(read_only=True)
  df = con.execute("SELECT * FROM protein_features").pl()
  con.close()
  return df

def make_xy(df):
  drop_cols = ["accession", "gene", "label"]   
  X = df.drop(drop_cols).to_numpy()       
  y = df["label"].to_numpy()   
  return X, y

if __name__ == "__main__":
  train()