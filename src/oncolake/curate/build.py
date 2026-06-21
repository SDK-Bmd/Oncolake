"""Zone curated : materialise le Parquet de staging dans une table DuckDB interrogeable.

DuckDB lit le Parquet directement depuis MinIO via httpfs (secret configure dans storage).
"""
from ..config import settings
from ..storage import get_duckdb


def build_curated() -> int:
    """Cree/rafraichit la table protein_features depuis le Parquet de staging. Retourne le nb de lignes."""
    con = get_duckdb()
    staging_uri = f"s3://{settings.staging_bucket}/features.parquet"
    con.execute(f"""
        CREATE OR REPLACE TABLE protein_features AS
        SELECT * FROM read_parquet('{staging_uri}');
    """)
    n = con.execute("SELECT count(*) FROM protein_features").fetchone()[0]
    con.close()
    return n
