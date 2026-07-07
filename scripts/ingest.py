import argparse
import sys
from oncolake.ingest.run import run

def main() -> int:
    p = argparse.ArgumentParser(description="Ingestion OncoLake -> zone raw.")
    p.add_argument("--limit", type=int, default=None,
                   help="nombre de proteines par classe (pour tester vite)")
    run(limit=p.parse_args().limit)
    return 0

if __name__ == "__main__":
    sys.exit(main())