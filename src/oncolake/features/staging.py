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

    seen: set[str] = set()
    out: list[dict] = []
    for r in records:
        acc = r["accession"]
        if acc in dual:
            if acc in seen:
                continue          
            seen.add(acc)
            r = {**r, "label": target}
        out.append(r)
    return out



def build_features(dual_label_policy: str = "drop",
                   disorder_threshold: int = 70) -> pl.DataFrame:

    manifest = json.loads(storage.get_bytes(settings.bucket_raw, MANIFEST_KEY))
    print(f"[manifest] {len(manifest)} entrees")

    records = resolve_dual_labels(manifest, dual_label_policy)
    kept = [r for r in records if r.get("has_structure")]
    dropped = [r for r in records if not r.get("has_structure")]
    for r in dropped:
        print(f"[skip] pas de structure : {r['accession']} ({r['gene']})")
    print(f"[filter] {len(kept)} gardees, {len(dropped)} sans structure")

    rows: list[dict] = []
    for r in kept:
        cif = storage.get_bytes(settings.bucket_raw, r["cif_key"])
        rows.append(features_for_record(r, cif, disorder_threshold))

    df = pl.DataFrame(rows)
    buf = io.BytesIO()
    df.write_parquet(buf)
    storage.put_bytes(settings.bucket_staging, STAGING_KEY, buf.getvalue())
    print(f"[staging] {STAGING_KEY} ecrit : {df.height} lignes, {df.width} colonnes")
    return df