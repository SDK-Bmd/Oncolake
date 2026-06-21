"""Acces stockage : objets MinIO (boto3) et connexion DuckDB configuree pour MinIO."""
import boto3
import duckdb

from .config import settings


def get_s3_client():
    """Client boto3 pointe sur MinIO (S3-compatible)."""
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        region_name="us-east-1",
    )


def put_object(bucket: str, key: str, data: bytes) -> None:
    get_s3_client().put_object(Bucket=bucket, Key=key, Body=data)


def get_object(bucket: str, key: str) -> bytes:
    return get_s3_client().get_object(Bucket=bucket, Key=key)["Body"].read()


def get_duckdb(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Connexion DuckDB avec le secret S3 pour lire le Parquet de staging depuis MinIO.

    Pattern CREATE SECRET (httpfs) : remplace l'ancien SET s3_* deprecie.
    Pour MinIO : URL_STYLE 'path' + USE_SSL false.
    """
    con = duckdb.connect(settings.duckdb_path, read_only=read_only)
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute(f"""
        CREATE OR REPLACE SECRET minio_secret (
            TYPE s3,
            KEY_ID '{settings.minio_access_key}',
            SECRET '{settings.minio_secret_key}',
            ENDPOINT '{settings.minio_endpoint}',
            URL_STYLE 'path',
            USE_SSL {str(settings.minio_secure).lower()}
        );
    """)
    return con
