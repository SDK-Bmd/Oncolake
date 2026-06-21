"""Stage DVC : curate. staging Parquet -> table DuckDB."""
from oncolake.curate.build import build_curated

if __name__ == "__main__":
    n = build_curated()
    print(f"curated : {n} lignes dans protein_features")
