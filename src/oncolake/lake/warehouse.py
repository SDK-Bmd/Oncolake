"""Connexion DuckDB configuree pour lire le Parquet de staging depuis MinIO (httpfs)."""
from urllib.parse import urlparse
import duckdb
from oncolake.config.settings import settings


def get_duckdb(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    parsed = urlparse(settings.s3_endpoint_url)   # http://localhost:9000
    endpoint = parsed.netloc                       # -> localhost:9000
    use_ssl = parsed.scheme == "https"

    con = duckdb.connect(settings.duckdb_path, read_only=read_only)
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute(f"""
        CREATE OR REPLACE SECRET minio_secret (
            TYPE s3,
            KEY_ID '{settings.s3_access_key}',
            SECRET '{settings.s3_secret_key}',
            ENDPOINT '{endpoint}',
            URL_STYLE 'path',
            USE_SSL {str(use_ssl).lower()}
        );
    """)
    return con