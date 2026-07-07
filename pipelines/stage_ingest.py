import json
from pathlib import Path
import yaml
from oncolake.ingest.run import run

OUT = Path("data/raw/manifest.json")

def main():
    limit = yaml.safe_load(Path("params.yaml").read_text())["ingest"]["limit_per_class"]
    manifest = run(limit=limit)                       # ecrit MinIO raw
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))  # out DVC local

if __name__ == "__main__":
    main()