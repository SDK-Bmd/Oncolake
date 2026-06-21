"""Telechargement des structures AlphaFold -> zone raw. Porte depuis la faisabilite.

On interroge l'API (pas l'URL fichier en dur) : robuste au passage v4 -> v6.
"""
import requests

AFDB_API = "https://alphafold.ebi.ac.uk/api/prediction"
_session = requests.Session()
_session.headers.update({"User-Agent": "OncoLake/0.1"})


def fetch_cif(accession: str) -> bytes | None:
    """Retourne le contenu du .cif courant, ou None si pas de structure (a loguer/ecarter)."""
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
