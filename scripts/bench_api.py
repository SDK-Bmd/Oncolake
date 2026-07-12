"""Benchmark des endpoints /ingest vs /ingest_fast (batch de 1 et de 100).

Prerequis : l'API doit tourner dans un AUTRE terminal :
    python -m uvicorn oncolake.api.main:app --reload

Puis :
    python scripts/bench_api.py
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

import requests

API = "http://localhost:8000"
BATCH_SIZES = (1, 100)
REPEATS = 3          # on moyenne pour lisser le bruit reseau

# Racine du projet = dossier parent de scripts/ -> chemins independants du repertoire courant
ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data" / "raw" / "manifest.json"
REPORT = ROOT / "logs" / "endpoint_benchmark.md"


def load_items() -> list[dict]:
    """Les proteines AVEC structure, au format attendu par les endpoints."""
    if not MANIFEST.exists():
        sys.exit(f"Manifeste introuvable : {MANIFEST}\n"
                 f"Lance d'abord l'ingestion :  python scripts/ingest.py")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return [{"accession": m["accession"], "sequence": m["sequence"]}
            for m in manifest if m["has_structure"]]


def call(endpoint: str, payload: dict) -> float:
    """Appelle un endpoint et renvoie le temps mesure cote pipeline."""
    r = requests.post(f"{API}/{endpoint}", json=payload, timeout=600)
    r.raise_for_status()
    return r.json()["elapsed_seconds"]


def bench(endpoint: str, payload: dict) -> float:
    """Moyenne de REPEATS appels."""
    return mean(call(endpoint, payload) for _ in range(REPEATS))


def write_report(rows: list[tuple]) -> Path:
    """rows = [(taille, t_ingest, t_fast, gain), ...] -> logs/endpoint_benchmark.md"""
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    lines = [
        "# Benchmark des endpoints -- /ingest vs /ingest_fast",
        "",
        "",
        "| Taille du lot | `/ingest` (s) | `/ingest_fast` (s) | Gain |",
        "|---|---|---|---|",
    ]
    for n, t_slow, t_fast, gain in rows:
        lines.append(f"| {n} element{'s' if n > 1 else ''} "
                     f"| {t_slow:.3f} | {t_fast:.3f} | {gain:.1f} % |")

    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return REPORT


def main() -> int:
    items = load_items()

    rows = []
    for n in BATCH_SIZES:
        if len(items) < n:
            print(f"[warn] seulement {len(items)} proteines disponibles pour un lot de {n}")
        payload = {"items": items[:n]}
        try:
            t_slow = bench("ingest", payload)
            t_fast = bench("ingest_fast", payload)
        except requests.ConnectionError:
            sys.exit(f"API injoignable sur {API}.\n"
                     f"Demarre-la dans un autre terminal :\n"
                     f"    python -m uvicorn oncolake.api.main:app --reload")
        gain = 100 * (t_slow - t_fast) / t_slow if t_slow else 0.0
        rows.append((n, t_slow, t_fast, gain))
        print(f"batch {n:3d} : ingest={t_slow:.2f}s  ingest_fast={t_fast:.2f}s  gain={gain:.0f}%")

    report = write_report(rows)
    print(f"\nRapport ecrit -> {report}")
    print()
    print(report.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())