import argparse
import sys
from oncolake.ingest.run import run
import time
from oncolake import bench

def main() -> int:
    parser = argparse.ArgumentParser(description="Ingestion OncoLake -> zone raw.")
    parser.add_argument("--limit", type=int, default=None,
                        help="nombre de proteines par classe (pour tester vite)")
    args = parser.parse_args()

    t0 = time.perf_counter()
    manifest = run(limit=args.limit)
    elapsed = time.perf_counter() - t0

    bench.log_run("ingest", elapsed, {
        "n_proteins": len(manifest),
        "n_with_structure": sum(m["has_structure"] for m in manifest),
    })
    print(f"[bench] ingest : {elapsed:.2f}s -> logs/ingest.json")
    return 0

if __name__ == "__main__":
    sys.exit(main())