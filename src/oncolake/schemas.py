"""Contrats Pydantic a chaque frontiere de zone. Source unique de verite du schema."""
from typing import Literal 

from pydantic import BaseModel, Field

Label = Literal["oncogene", "tumor_suppressor"]

# 20 acides amines standards : noms de colonnes pour la composition.
AA20 = "ACDEFGHIKLMNPQRSTVWY"


class ProteinRaw(BaseModel):
    """Sortie de l'ingestion UniProt (zone raw)."""
    accession: str
    gene: str | None = None
    sequence: str
    label: Label


class ProteinFeatures(BaseModel):
    """Vecteur de features (zone staging/curated). Une ligne du dataset ML."""
    accession: str
    gene: str | None = None
    label: Label
    seq_length: int
    n_residues_structure: int
    plddt_mean: float
    pct_low_confidence: float = Field(..., description="% residus pLDDT < seuil (proxy desordre)")
    radius_of_gyration: float
    aa_composition: dict[str, float] = Field(default_factory=dict)


# --- I/O de l'API gateway -------------------------------------------------
class IngestItem(BaseModel):
    accession: str
    sequence: str


class IngestRequest(BaseModel):
    """Batch de sequences pour /ingest et /ingest_fast."""
    items: list[IngestItem]


class IngestResponse(BaseModel):
    n_processed: int
    elapsed_seconds: float
    features: list[ProteinFeatures]
