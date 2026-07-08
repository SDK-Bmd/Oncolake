"""Stage DVC : train. DuckDB -> Random Forest -> metrics.json."""
from pathlib import Path
import yaml
from oncolake.ml.train import train

def main():
    params = yaml.safe_load(Path("params.yaml").read_text())["train"]
    train(**params) 

if __name__ == "__main__":
    main()