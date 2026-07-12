"""Version optimisée d' /ingest : téléchargements + extraction en parallèle."""
from concurrent.futures import ThreadPoolExecutor

from oncolake.ingest import alphafold
from oncolake.features.extract import features_for_record


def _process_item(item: dict, disorder_threshold: int = 70) -> dict | None:
    """Télécharge la structure d'un item et en extrait les features (None si absente).
    Exécuté dans un thread ; ThreadPoolExecutor.map préserve l'ordre."""
    cif = alphafold.fetch_cif(item.accession)   
    if cif is None:
        return None
    record = {"accession": item.accession, "sequence": item.sequence,
              "gene": None, "label": None}
    return features_for_record(record, cif, disorder_threshold)


def ingest_fast(items: list[dict], max_workers: int = 16) -> list[dict]:
    """Traite un batch d'items {accession, sequence} en parallèle et renvoie les features."""
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        results = pool.map(_process_item, items)
    return [r for r in results if r is not None] 