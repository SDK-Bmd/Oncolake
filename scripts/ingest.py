"""Stage 1 du pipeline : ingestion -> zone raw (MinIO).

Usage (MinIO doit tourner : docker compose up -d minio minio-setup) :

    python scripts/ingest.py                # tout (~1200 proteines)
    python scripts/ingest.py --limit 20     # 20 par classe, pour un test rapide

Pour chaque classe (oncogene KW-0656 / suppressor KW-0043) :
  1. interroge UniProt  -> accession, gene, sequence, label
  2. depose le JSON brut UniProt        dans  raw/uniprot/{label}.json
  3. telecharge le .cif AlphaFold       dans  raw/alphafold/{accession}.cif
  4. ecrit le manifeste (pont staging)  dans  raw/manifest.json

Les proteines sans structure AlphaFold sont logguees et marquees
has_structure=false dans le manifeste (elles seront ecartees au staging).
"""
import argparse
import json
import sys

from oncolake.config.settings import settings
from oncolake.ingest import alphafold, uniprot
from oncolake.lake import storage

# Mots-cles UniProt -> label du projet
KEYWORDS = {
    "oncogene": "KW-0656",          # Proto-oncogene
    "tumor_suppressor": "KW-0043",  # Tumor suppressor
}


def run(limit: int | None = None) -> list[dict]:
    storage.ensure_buckets()
    manifest: list[dict] = []

    for label, keyword_id in KEYWORDS.items():
        print(f"[uniprot] {label} ({keyword_id}) ...")
        records = uniprot.search_by_keyword(keyword_id, label, limit=limit)
        print(f"          {len(records)} proteines")

        # Zone raw : JSON UniProt brut, tel quel.
        storage.put_bytes(
            settings.bucket_raw,
            f"uniprot/{label}.json",
            json.dumps(records, ensure_ascii=False).encode("utf-8"),
        )

        # Zone raw : structures AlphaFold.
        for rec in records:
            acc = rec["accession"]
            cif = alphafold.fetch_cif(acc)
            has_structure = cif is not None
            if has_structure:
                storage.put_bytes(settings.bucket_raw, f"alphafold/{acc}.cif", cif)
            else:
                print(f"          [no structure] {acc} ({rec['gene']})")
            manifest.append({
                "accession": acc,
                "gene": rec["gene"],
                "label": label,
                "sequence": rec["sequence"],
                "has_structure": has_structure,
                "cif_key": f"alphafold/{acc}.cif" if has_structure else None,
            })

    # Manifeste : la table d'index que le staging consommera.
    storage.put_bytes(
        settings.bucket_raw,
        "manifest.json",
        json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"),
    )

    n_struct = sum(m["has_structure"] for m in manifest)
    print(f"\n[manifest] {len(manifest)} proteines | "
          f"{n_struct} avec structure | {len(manifest) - n_struct} sans.")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingestion OncoLake -> zone raw.")
    parser.add_argument("--limit", type=int, default=None,
                        help="nombre de proteines par classe (pour tester vite)")
    run(limit=parser.parse_args().limit)
    return 0


if __name__ == "__main__":
    sys.exit(main())