"""Raw -> Staging. Manifeste + .cif  ->  table de features (Parquet).

Fait passer les donnees de la zone raw (brut) a la zone staging (nettoye + structure),
(Raw -> Staging = nettoyage, regles de qualite, harmonisation du
format). S'appuie sur les helpers deja valides de features/extract.py.

    python scripts/build_features.py                       # politique par defaut (drop)
    python scripts/build_features.py --dual-label oncogene # autres : suppressor, both
"""
import argparse
import io
import json
import sys
from collections import Counter

import polars as pl

from oncolake.config.settings import settings
from oncolake.features.extract import features_for_record
from oncolake.lake import storage

MANIFEST_KEY = "manifest.json"
STAGING_KEY = "features.parquet"

# label force selon la politique choisie (pour les cas autres que 'drop')
_FORCED_LABEL = {"oncogene": "oncogene", "suppressor": "tumor_suppressor", "both": "both"}


def resolve_dual_labels(records: list[dict], policy: str) -> list[dict]:
    """Traite les proteines portant les DEUX labels (meme accession, 2 entrees).

    Ces doublons violent l'unicite de l'accession (contrainte de la zone Staging,
    TP3). Politiques :
      drop       -> on les ecarte (labels contradictoires pour une tache binaire)
      oncogene   -> on force le label 'oncogene'
      suppressor -> on force le label 'tumor_suppressor'
      both        -> on les fusionne en une 3e classe 'both'
    """
    counts = Counter(r["accession"] for r in records)
    dual = {acc for acc, c in counts.items() if c > 1}
    if not dual:
        return records

    print(f"[dual-label] {len(dual)} proteine(s) a double label -> politique '{policy}'")

    if policy == "drop":
        return [r for r in records if r["accession"] not in dual]

    target = _FORCED_LABEL.get(policy)
    if target is None:
        raise ValueError(f"politique double-label inconnue : {policy}")

    # collapse : une seule entree par accession en double, label force
    seen: set[str] = set()
    out: list[dict] = []
    for r in records:
        acc = r["accession"]
        if acc in dual:
            if acc in seen:
                continue          # 2e occurrence -> ignoree
            seen.add(acc)
            r = {**r, "label": target}
        out.append(r)
    return out


def build_features(dual_label_policy: str = "drop",
                   disorder_threshold: int = 70) -> pl.DataFrame:
    # 1. Lire le manifeste depuis la zone raw
    manifest = json.loads(storage.get_bytes(settings.bucket_raw, MANIFEST_KEY))
    print(f"[manifest] {len(manifest)} entrees")

    # 2. Resoudre les proteines double-label (unicite de l'accession)
    records = resolve_dual_labels(manifest, dual_label_policy)

    # 3. Ecarter proprement les proteines sans structure (les geantes)
    kept = [r for r in records if r.get("has_structure")]
    dropped = [r for r in records if not r.get("has_structure")]
    for r in dropped:
        print(f"[skip] pas de structure : {r['accession']} ({r['gene']})")
    print(f"[filter] {len(kept)} gardees, {len(dropped)} sans structure")

    # 4. Extraction des features (boucle naive ; l'optimisation viendra a l'etape 7)
    rows: list[dict] = []
    for r in kept:
        cif = storage.get_bytes(settings.bucket_raw, r["cif_key"])
        rows.append(features_for_record(r, cif, disorder_threshold))

    # 5. Assembler la table (Polars : list[dict] -> DataFrame, colonnes inferees des cles)
    df = pl.DataFrame(rows)

    # 6. Ecrire en Parquet -> zone staging.
    #    write_parquet ecrit dans un BytesIO (writer natif Polars, pas besoin de pyarrow).
    buf = io.BytesIO()
    df.write_parquet(buf)
    storage.put_bytes(settings.bucket_staging, STAGING_KEY, buf.getvalue())
    print(f"[staging] {STAGING_KEY} ecrit : {df.height} lignes, {df.width} colonnes")
    return df


def main() -> int:
    parser = argparse.ArgumentParser(description="Etape 4 : features -> staging.")
    parser.add_argument("--dual-label", default="drop",
                        choices=["drop", "oncogene", "suppressor", "both"],
                        help="strategie pour les proteines a double label (defaut: drop)")
    args = parser.parse_args()
    build_features(dual_label_policy=args.dual_label)
    return 0


if __name__ == "__main__":
    sys.exit(main())