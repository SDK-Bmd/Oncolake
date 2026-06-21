"""Telechargement des structures AlphaFold (.cif) via l'API officielle.

On passe par /api/prediction/{accession} (qui renvoie l'URL du fichier courant)
plutot que de coder en dur un numero de version : robuste au passage v4 -> v6.
"""
import requests

AFDB_API = "https://alphafold.ebi.ac.uk/api/prediction"

_session = requests.Session()
_session.headers.update({"User-Agent": "OncoLake/0.1"})


def fetch_cif(accession: str) -> bytes | None:
    """Contenu du .cif courant pour une accession, ou None si pas de structure.

    Le None est attendu et normal : toutes les proteines n'ont pas de prediction
    AlphaFold. L'appelant doit logguer et ecarter proprement (robustesse = bareme).
    """
    try:
        meta = _session.get(f"{AFDB_API}/{accession}", timeout=30)
        meta.raise_for_status()
        entries = meta.json()
        if not entries or not entries[0].get("cifUrl"):
            return None
        cif = _session.get(entries[0]["cifUrl"], timeout=60)
        cif.raise_for_status()
        return cif.content
    except requests.HTTPError:
        return None