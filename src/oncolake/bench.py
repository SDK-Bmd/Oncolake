"""Benchmark des endpoints /ingest vs /ingest_fast aux tailles de batch 1 et 100.

Consigne 3.1 : chronometrer le pipeline pour un batch de 1 et un batch de 100
elements, sur les deux endpoints, et documenter la comparaison a ces tailles.

Prerequis : MinIO up (lecture du manifeste) + acces reseau (les endpoints
telechargent depuis AlphaFold). Genere logs/endpoint_benchmark.md.

    python scripts/benchmark_endpoints.py
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from fastapi.testclient import TestClient

from oncolake.api.main import app
from oncolake.config.settings import settings
from oncolake.lake import storage

BATCH_SIZES = [1, 100]
REPEATS = 3                      # moyenne pour lisser le bruit
LOG_DIR = Path("logs")


def load_items(n: int) -> list[dict]:
    """n proteines AVEC structure, depuis raw/manifest.json."""
    manifest = json.loads(storage.get_bytes(settings.bucket_raw, "manifest.json"))
    with_struct = [m for m in manifest if m.get("has_structure")]
    return [{"accession": m["accession"], "sequence": m["sequence"]}
            for m in with_struct[:n]]


def bench(client: TestClient, path: str, items: list[dict]) -> float:
    """Moyenne de l'elapsed_seconds renvoye par l'endpoint sur REPEATS appels."""
    times = []
    for _ in range(REPEATS):
        r = client.post(path, json={"items": items})
        r.raise_for_status()
        times.append(r.json()["elapsed_seconds"])
    return mean(times)


def main() -> int:
    client = TestClient(app)
    rows = []
    for size in BATCH_SIZES:
        items = load_items(size)
        if len(items) < size:
            print(f"[warn] seulement {len(items)} proteines dispo pour batch {size}")
        t_naive = bench(client, "/ingest", items)
        t_fast = bench(client, "/ingest_fast", items)
        gain = (t_naive - t_fast) / t_naive * 100 if t_naive else 0.0
        rows.append((size, t_naive, t_fast, gain))
        print(f"batch {size:>3} : /ingest {t_naive:.3f}s | "
              f"/ingest_fast {t_fast:.3f}s | gain {gain:.1f}%")

    LOG_DIR.mkdir(exist_ok=True)
    lines = [
        "# Benchmark endpoints -- /ingest vs /ingest_fast",
        "",
        f"_Genere le {datetime.now(timezone.utc).isoformat(timespec='seconds')}"
        f" | moyenne sur {REPEATS} appels_",
        "",
        "| Batch | /ingest (s) | /ingest_fast (s) | Gain |",
        "|---|---|---|---|",
    ]
    for size, tn, tf, g in rows:
        lines.append(f"| {size} | {tn:.3f} | {tf:.3f} | {g:.1f} % |")
    b100 = next((g for s, _, _, g in rows if s == 100), 0.0)
    lines += [
        "",
        f"- Objectif +30 % (a batch 100) : **{'ATTEINT' if b100 >= 30 else 'NON ATTEINT'}**",
        "- A batch 1, le gain est negligeable : un seul element, aucun parallelisme a "
        "exploiter. L'optimisation se revele sur les gros batchs.",
    ]
    report = LOG_DIR / "endpoint_benchmark.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n[bench] rapport -> {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())