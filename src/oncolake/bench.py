"""Chronometrage et comparaison des variantes d'ingestion (/ingest vs /ingest_fast).

Chaque variante ecrit son temps d'execution dans logs/{variant}.json. Quand
ingest_fast tourne, s'il trouve le log de ingest, il genere logs/comparison.md
avec l'acceleration et le gain de performance (objectif : +30 %).
"""
import json
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path("logs")


def log_run(variant: str, elapsed: float, stats: dict) -> Path:
    """Ecrit le releve chronometre d'une variante -> logs/{variant}.json."""
    LOG_DIR.mkdir(exist_ok=True)
    entry = {
        "variant": variant,
        "elapsed_seconds": round(elapsed, 3),
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        **stats,
    }
    path = LOG_DIR / f"{variant}.json"
    path.write_text(json.dumps(entry, indent=2), encoding="utf-8")
    return path


def load_run(variant: str) -> dict | None:
    """Relit le log d'une variante s'il existe, sinon None."""
    path = LOG_DIR / f"{variant}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _throughput(entry: dict) -> float:
    """Debit en proteines par seconde."""
    return entry.get("n_proteins", 0) / (entry.get("elapsed_seconds", 0) or 1e-9)


def write_comparison(baseline: dict, fast: dict) -> Path:
    """Genere logs/comparison.md a partir des deux releves (baseline = ingest)."""
    t0 = baseline["elapsed_seconds"]
    t1 = fast["elapsed_seconds"] or 1e-9
    speedup = t0 / t1
    gain = (t0 - t1) / t0 * 100 if t0 else 0.0

    lines = [
        "# Comparaison de performance -- /ingest vs /ingest_fast",
        "",
        f"_Genere le {datetime.now(timezone.utc).isoformat(timespec='seconds')}_",
        "",
        "| Variante | Temps (s) | Proteines | Structures | Debit (prot/s) | Workers |",
        "|---|---|---|---|---|---|",
        f"| `ingest` (naif, sequentiel) | {t0:.2f} | {baseline.get('n_proteins', '?')} "
        f"| {baseline.get('n_with_structure', '?')} | {_throughput(baseline):.1f} | 1 |",
        f"| `ingest_fast` (ThreadPool) | {t1:.2f} | {fast.get('n_proteins', '?')} "
        f"| {fast.get('n_with_structure', '?')} | {_throughput(fast):.1f} | {fast.get('max_workers', '?')} |",
        "",
        f"- **Acceleration : x{speedup:.2f}**",
        f"- **Gain de performance : {gain:.1f} %**",
    ]

    # Garde-fous pour une comparaison honnete.
    if baseline.get("n_proteins") != fast.get("n_proteins"):
        lines += ["", "> ATTENTION : les deux runs n'ont pas le meme nombre de proteines. "
                  "Relance avec le MEME `--limit` pour une comparaison equitable."]
    elif baseline.get("n_with_structure") != fast.get("n_with_structure"):
        lines += ["", "> ATTENTION : le nombre de structures differe -> la version parallele a "
                  "probablement ete limitee par l'API (429). Baisse `--workers`."]

    LOG_DIR.mkdir(exist_ok=True)
    path = LOG_DIR / "comparison.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path