from pathlib import Path
import yaml
from oncolake.features.staging import build_features

OUT = Path("data/staging/features.parquet")

def main():
    params = yaml.safe_load(Path("params.yaml").read_text())["features"]
    df = build_features(                             
        dual_label_policy=params.get("dual_label", "drop"),
        disorder_threshold=params["plddt_disorder_threshold"],
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(OUT)                           

if __name__ == "__main__":
    main()