"""Ingestion UniProt : proteines humaines labellisees oncogene / suppresseur de tumeur.

Porte du notebook de faisabilite, avec pagination complete via le header Link: next
(UniProt renvoie 500 resultats par page ; il y en a ~1200 au total).
"""
import requests

UNIPROT_BASE = "https://rest.uniprot.org/uniprotkb"

_session = requests.Session()
_session.headers.update({"User-Agent": "OncoLake/0.1"})


def search_by_keyword(keyword_id: str, label: str, organism_id: int = 9606,
                      reviewed: bool = True, limit: int | None = None) -> list[dict]:
    """Retourne [{accession, gene, sequence, label}, ...] pour un mot-cle UniProt.

    keyword_id : KW-0656 (Proto-oncogene) ou KW-0043 (Tumor suppressor).
    limit      : nombre max de proteines (pratique pour tester ; None = tout).
    """
    parts = [f"(keyword:{keyword_id})", f"(organism_id:{organism_id})"]
    if reviewed:
        parts.append("(reviewed:true)")
    params: dict | None = {
        "query": " AND ".join(parts),
        "format": "json",
        "fields": "accession,gene_primary,sequence",
        "size": 500,
    }
    rows: list[dict] = []
    url = f"{UNIPROT_BASE}/search"
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
        url = r.links.get("next", {}).get("url")  # pagination
        params = None  
    return rows