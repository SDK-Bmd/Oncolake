"""Acces au stockage objet (MinIO via l'API S3).

Encapsule boto3 pour que le reste du code ne manipule jamais les details de
connexion : on appelle put_bytes/get_bytes/list_keys, pas boto3 directement.
MinIO etant 100% compatible S3, ce meme code tournerait tel quel sur un vrai
AWS S3 en changeant uniquement l'endpoint dans la config.

Les fonctions levent des exceptions explicites (StorageError) au lieu de
laisser remonter des erreurs boto3 brutes, pour faciliter la gestion d'erreurs
en amont (API, pipeline).
"""

import io

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError, EndpointConnectionError

from oncolake.config.settings import settings


class StorageError(Exception):
    """Erreur de stockage cote OncoLake (connexion, objet absent, etc.)."""

_client = None


def get_s3_client():
    """Retourne un client boto3 pointant vers MinIO (cree une seule fois)."""
    global _client
    if _client is None:
        _client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",  
        )
    return _client


def ping() -> bool:
    """Verifie que MinIO repond. Renvoie True/False, ne leve pas.

    Utilise par l'endpoint /health et le script de verification.
    """
    try:
        get_s3_client().list_buckets()
        return True
    except (ClientError, EndpointConnectionError, Exception):
        return False


def bucket_exists(bucket: str) -> bool:
    """Indique si un bucket existe et est accessible."""
    try:
        get_s3_client().head_bucket(Bucket=bucket)
        return True
    except ClientError:
        return False
    except EndpointConnectionError as exc:
        raise StorageError(f"MinIO injoignable a {settings.s3_endpoint_url}") from exc


def ensure_buckets() -> None:
    """Cree les 3 buckets s'ils n'existent pas deja (idempotent).

    Filet de securite : normalement minio-setup les cree au demarrage, mais
    cette fonction permet de (re)garantir leur presence depuis le code.
    """
    client = get_s3_client()
    for bucket in settings.buckets:
        if not bucket_exists(bucket):
            try:
                client.create_bucket(Bucket=bucket)
            except ClientError as exc:
                raise StorageError(f"Impossible de creer le bucket '{bucket}'") from exc

def put_bytes(bucket: str, key: str, data: bytes) -> None:
    """Depose un objet binaire (ex. un .cif, un .json) dans un bucket."""
    try:
        get_s3_client().put_object(Bucket=bucket, Key=key, Body=io.BytesIO(data))
    except (ClientError, EndpointConnectionError) as exc:
        raise StorageError(f"Echec d'ecriture de '{key}' dans '{bucket}'") from exc


def get_bytes(bucket: str, key: str) -> bytes:
    """Recupere un objet binaire depuis un bucket.

    Leve StorageError si l'objet n'existe pas (cas a gerer en amont).
    """
    try:
        resp = get_s3_client().get_object(Bucket=bucket, Key=key)
        return resp["Body"].read()
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in ("NoSuchKey", "404"):
            raise StorageError(f"Objet introuvable : '{key}' dans '{bucket}'") from exc
        raise StorageError(f"Echec de lecture de '{key}' dans '{bucket}'") from exc
    except EndpointConnectionError as exc:
        raise StorageError(f"MinIO injoignable a {settings.s3_endpoint_url}") from exc


def object_exists(bucket: str, key: str) -> bool:
    """Indique si un objet precis existe dans un bucket."""
    try:
        get_s3_client().head_object(Bucket=bucket, Key=key)
        return True
    except ClientError:
        return False


def list_keys(bucket: str, prefix: str = "") -> list[str]:
    """Liste les cles d'un bucket (optionnellement filtrees par prefixe).

    Gere la pagination : renvoie TOUTES les cles, pas seulement les 1000
    premieres (limite par defaut de l'API S3).
    """
    try:
        paginator = get_s3_client().get_paginator("list_objects_v2")
        keys: list[str] = []
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            keys.extend(obj["Key"] for obj in page.get("Contents", []))
        return keys
    except (ClientError, EndpointConnectionError) as exc:
        raise StorageError(f"Echec du listage de '{bucket}'") from exc


def count_objects(bucket: str) -> int:
    """Compte les objets d'un bucket (pour l'endpoint /stats)."""
    return len(list_keys(bucket))
