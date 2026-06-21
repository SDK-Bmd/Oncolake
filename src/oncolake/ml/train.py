"""Random Forest oncogene vs suppresseur (zone curated -> modele). Polars -> numpy -> sklearn.

TODO etape 5 : remplir train() :
  - lire protein_features depuis DuckDB en Polars (con.execute(...).pl())
  - X = features numeriques .to_numpy() ; y = label
  - train/test split, RandomForestClassifier(n_estimators=...)
  - matrice de confusion + feature_importances_ + flagging des cas incertains
  - dump metrics.json (lu par DVC)
"""
