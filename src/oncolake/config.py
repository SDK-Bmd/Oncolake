"""Configuration centralisee via pydantic-settings (lit .env, prefixe ONCOLAKE_)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="ONCOLAKE_", extra="ignore")

    # MinIO / S3
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    raw_bucket: str = "oncolake-raw"
    staging_bucket: str = "oncolake-staging"

    # DuckDB (zone curated)
    duckdb_path: str = "data/curated.duckdb"

    @property
    def s3_endpoint_url(self) -> str:
        scheme = "https" if self.minio_secure else "http"
        return f"{scheme}://{self.minio_endpoint}"


settings = Settings()
