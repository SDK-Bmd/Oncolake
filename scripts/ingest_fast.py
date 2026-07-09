"""/ingest_fast : ingestion optimisee par telechargements AFDB paralleles (ThreadPool).

Les .cif sont telecharges en parallele, l'ingestion est I/O-bound. 
Chronometre, journalise dans logs/ingest_fast.json, et
si logs/ingest.json existe, genere logs/comparison.md.

    python scripts/ingest.py                          # 1) la baseline naive (-> logs/ingest.json)
    python scripts/ingest_fast.py                     # 2) la version rapide + le comparatif
    python scripts/ingest_fast.py --limit 50 --workers 8 

"""
import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from oncolake import bench
from oncolake.config.settings import settings
from oncolake.ingest import alphafold, uniprot
from oncolake.lake import storage

KEYWORDS = {
    "oncogene": "KW-0656",
    "tumor_suppressor": "KW-0043",
}


def _fetch_and_store(rec: dict) -> dict:
    """Telecharge + stocke le .cif d'une proteine, renvoie son entree de manifeste.

    Execute dans un thread. Le client boto3 (storage) est thread-safe pour les
    appels ; ThreadPoolExecutor.map preserve l'ordre -> manifeste deterministe.
    """
    acc = rec["accession"]
    cif = alphafold.fetch_cif(acc)
    has_structure = cif is not None
    if has_structure:
        storage.put_bytes(settings.bucket_raw, f"alphafold/{acc}.cif", cif)
    return {
        "accession": acc,
        "gene": rec["gene"],
        "label": rec["label"],
        "sequence": rec["sequence"],
        "has_structure": has_structure,
        "cif_key": f"alphafold/{acc}.cif" if has_structure else None,
    }


def run_fast(limit: int | None = None, max_workers: int = 16) -> list[dict]:
    storage.ensure_buckets()
    manifest: list[dict] = []

    for label, keyword_id in KEYWORDS.items():
        print(f"[uniprot] {label} ({keyword_id}) ...")
        records = uniprot.search_by_keyword(keyword_id, label, limit=limit)
        print(f"          {len(records)} proteines")
        storage.put_bytes(
            settings.bucket_raw, f"uniprot/{label}.json",
            json.dumps(records, ensure_ascii=False).encode("utf-8"),
        )

        # Telechargements AlphaFold en parallele 
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            results = list(pool.map(_fetch_and_store, records))

        for r in results:
            if not r["has_structure"]:
                print(f"          [no structure] {r['accession']} ({r['gene']})")
        manifest.extend(results)

    storage.put_bytes(
        settings.bucket_raw, "manifest.json",
        json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"),
    )
    n_struct = sum(m["has_structure"] for m in manifest)
    print(f"\n[manifest] {len(manifest)} proteines | {n_struct} avec structure | "
          f"{len(manifest) - n_struct} sans.")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="/ingest_fast : ingestion parallele.")
    parser.add_argument("--limit", type=int, default=None,
                        help="proteines par classe (utiliser la MEME valeur que pour ingest)")
    parser.add_argument("--workers", type=int, default=16,
                        help="nombre de threads de telechargement (defaut: 16)")
    args = parser.parse_args()

    t0 = time.perf_counter()
    manifest = run_fast(limit=args.limit, max_workers=args.workers)
    elapsed = time.perf_counter() - t0

    bench.log_run("ingest_fast", elapsed, {
        "n_proteins": len(manifest),
        "n_with_structure": sum(m["has_structure"] for m in manifest),
        "max_workers": args.workers,
    })
    print(f"[bench] ingest_fast : {elapsed:.2f}s -> logs/ingest_fast.json")

    baseline = bench.load_run("ingest")
    if baseline:
        report = bench.write_comparison(baseline, bench.load_run("ingest_fast"))
        print(f"[bench] rapport comparatif -> {report}\n")
        print(report.read_text(encoding="utf-8"))
    else:
        print("[bench] aucun log 'ingest' trouve.")
        print("        Lance d'abord la baseline :  python scripts/ingest.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())