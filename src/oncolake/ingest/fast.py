from oncolake.schemas import ProteinFeatures

def ingest_fast(items: list[dict]) -> list[dict]:
    """Version optimisée : télécharge + extrait les features d'un batch en parallèle.
    items : [{"accession": "...", "sequence": "..."}, ...]
    retour : liste de lignes de features (mêmes clés que features_for_record).
    Objectif : >= 30 % plus rapide que la version naïve.
    """