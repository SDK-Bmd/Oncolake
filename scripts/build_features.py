"""Raw -> Staging. Manifeste + .cif  ->  table de features (Parquet).

Fait passer les donnees de la zone raw (brut) a la zone staging (nettoye + structure),

    python scripts/build_features.py                       # politique par defaut (drop)
    python scripts/build_features.py --dual-label oncogene # autres : suppressor, both
"""
import argparse
import sys 
from oncolake.config.settings import settings
from oncolake.features.extract import features_for_record
from oncolake.features.staging import build_features
from oncolake.lake import storage



def main() -> int:
    parser = argparse.ArgumentParser(description="Etape 4 : features -> staging.")
    parser.add_argument("--dual-label", default="drop",
                        choices=["drop", "oncogene", "suppressor", "both"],
                        help="strategie pour les proteines a double label (defaut: drop)")
    args = parser.parse_args()
    build_features(dual_label_policy=args.dual_label)
    return 0


if __name__ == "__main__":
    sys.exit(main())