"""Version optimisee : telecharge + extrait les features d'un batch EN PARALLELE.

Meme sortie que la boucle naive de /ingest, mais les telechargements AlphaFold
(I/O-bound) sont parallelises via ThreadPool -> >= 30 % plus rapide sur un batch.
C'est le levier le plus rentable ici (comme au TP2) ; Numba viserait les calculs
CPU de l'extraction, secondaires face au temps reseau.
"""
from concurrent.futures import ThreadPoolExecutor

from oncolake.features.extract import features_for_record
from oncolake.ingest import alphafold


def _process_one(item) -> dict | None:
    """Telecharge le .cif et extrait les features d'un element. None si pas de structure."""
    cif = alphafold.fetch_cif(item.accession)
    if cif is None:
        return None
    record = {"accession": item.accession, "sequence": item.sequence,
              "gene": None, "label": None}
    return features_for_record(record, cif)


def ingest_fast(items, max_workers: int = 16) -> list[dict]:
    """Traite un batch en parallele. items : liste d'objets .accession / .sequence."""
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        results = pool.map(_process_one, items)   # map preserve l'ordre du batch
    return [r for r in results if r is not None]