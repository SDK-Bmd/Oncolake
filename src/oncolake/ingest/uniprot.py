"""Ingestion UniProt -> zone raw. Porte depuis le notebook de faisabilite (valide)."""
import requests

from ..schemas import Label

UNIPROT_BASE = "https://rest.uniprot.org/uniprotkb"
_session = requests.Session()
_session.headers.update({"User-Agent": "OncoLake/0.1"})


def search_by_keyword(keyword_id: str, label: Label, organism_id: int = 9606,
                      reviewed: bool = True, limit: int | None = None) -> list[dict]:
    """Liste des proteines portant un mot-cle (KW-0656 / KW-0043), avec accession + sequence."""
    parts = [f"(keyword:{keyword_id})", f"(organism_id:{organism_id})"]
    if reviewed:
        parts.append("(reviewed:true)")
    params = {
        "query": " AND ".join(parts),
        "format": "json",
        "fields": "accession,gene_primary,sequence",
        "size": 500,
    }
    rows, url = [], f"{UNIPROT_BASE}/search"
    while url:
        r = _session.get(url, params=params, timeout=60)
        r.raise_for_status()
        for item in r.json().get("results", []):
            gene = (item.get("genes") or [{}])[0].get("geneName", {}).get("value")
            rows.append({
                "accession": item["primaryAccession"],
                "gene": gene,
                "sequence": item.get("sequence", {}).get("value"),
                "label": label,
            })
            if limit and len(rows) >= limit:
                return rows
        # pagination via le header Link "next"
        url = r.links.get("next", {}).get("url")
        params = None
    return rows
