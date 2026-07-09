"""Verification de la connexion a MinIO et du bon fonctionnement du stockage.

A lancer chez toi, MinIO devant tourner (docker compose up -d minio minio-setup) :

    python scripts/check_minio.py

Le script :
  1. verifie que MinIO repond,
  2. s'assure que les 3 buckets existent,
  3. fait un aller-retour ecriture / lecture / suppression sur un objet test,
  4. affiche les stats par zone.

Aucun effet de bord persistant : l'objet test est supprime a la fin.
"""

import sys

from oncolake.config.settings import settings
from oncolake.lake import storage


def main() -> int:
    print(f"Endpoint MinIO : {settings.s3_endpoint_url}")
    if not storage.ping():
        print("ECHEC : MinIO ne repond pas. Le conteneur tourne-t-il ?")
        print("  -> docker compose up -d minio minio-setup")
        return 1
    print("OK   : MinIO repond.")
    storage.ensure_buckets()
    for bucket in settings.buckets:
        present = storage.bucket_exists(bucket)
        print(f"{'OK  ' if present else 'MANQUE'} : bucket '{bucket}'")

  
    test_key = "_healthcheck/test.txt"
    test_data = b"oncolake connection ok"
    try:
        storage.put_bytes(settings.bucket_raw, test_key, test_data)
        readback = storage.get_bytes(settings.bucket_raw, test_key)
        assert readback == test_data, "Donnees relues differentes des donnees ecrites"
        print("OK   : ecriture + lecture verifiees.")
    except (storage.StorageError, AssertionError) as exc:
        print(f"ECHEC : aller-retour objet -> {exc}")
        return 1
    finally:
        try:
            storage.get_s3_client().delete_object(
                Bucket=settings.bucket_raw, Key=test_key
            )
        except Exception:
            pass

    # 4. Stats par zone
    print("\nRemplissage des zones :")
    for bucket in settings.buckets:
        print(f"  {bucket:10s} : {storage.count_objects(bucket)} objet(s)")

    print("\nTout est operationnel.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
