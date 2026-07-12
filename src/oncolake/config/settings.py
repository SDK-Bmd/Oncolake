"""Configuration centralisee de l'application.

Toute la config passe par ici, chargee depuis les variables d'environnement
(ou un fichier .env a la racine) via pydantic-settings. Avantage : un seul
endroit de verite, type et valide, plutot que des os.getenv() eparpilles.

Usage :  from oncolake.config.settings import settings
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Parametres de l'application, charges depuis l'environnement / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Acces S3 / MinIO ---
    # Depuis la machine hote (scripts, tests) : http://localhost:9000
    # Depuis un conteneur docker            : http://minio:9000
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"

    bucket_raw: str = "raw"
    bucket_staging: str = "staging"
    bucket_curated: str = "curated"

    duckdb_path: str = str(ROOT / "data" / "curated.duckdb")
    
    @property
    def buckets(self) -> list[str]:
        """Les trois zones, pratique pour iterer (creation, stats, checks)."""
        return [self.bucket_raw, self.bucket_staging, self.bucket_curated]


# Instance unique importable partout dans le projet.
settings = Settings()
