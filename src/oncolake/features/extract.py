"""Extraction de features (zone staging). gemmi pour parser le .cif, Polars pour la table."""
import gemmi
import os
import tempfile
import polars as pl 
import numpy as np  

from oncolake.schemas import AA20


def amino_acid_composition(sequence: str) -> dict[str, float]:
    n = len(sequence) or 1
    return {f"aa_{a}": sequence.count(a) / n for a in AA20}


def structure_features(cif_bytes: bytes, disorder_threshold: int = 70) -> dict:
    """pLDDT (B-factor des CA) + rayon de giration depuis le contenu d'un .cif."""
    with tempfile.NamedTemporaryFile(suffix=".cif", delete=False) as tmp:
        tmp.write(cif_bytes)
        path = tmp.name
    try:
        structure = gemmi.read_structure(path)  
    finally:
        os.unlink(path)

    model = structure[0]
    plddt, coords = [], []
    for chain in model:
        for residue in chain:
            ca = residue.find_atom("CA", "*")
            if ca is not None:
                plddt.append(ca.b_iso)
                coords.append([ca.pos.x, ca.pos.y, ca.pos.z])

    plddt_arr = np.asarray(plddt)

    if not plddt:
        raise ValueError("aucun atome CA dans la structure")

    coords_arr = np.asarray(coords)
    center = coords_arr.mean(axis=0)
    rg = float(np.sqrt(((coords_arr - center) ** 2).sum(axis=1).mean()))

    return {
        "n_residues_structure": int(len(plddt_arr)),
        "plddt_mean": float(plddt_arr.mean()),
        "pct_low_confidence": float((plddt_arr < disorder_threshold).mean() * 100),
        "radius_of_gyration": rg,
    }


def build_feature_frame(records: list[dict]) -> pl.DataFrame:
    """Assemble une liste de dicts de features en DataFrame Polars (ecrit ensuite en Parquet)."""
    return pl.DataFrame(records)

def features_for_record(record: dict, cif_bytes: bytes,
                        disorder_threshold: int = 70) -> dict:
    """Assemble une ligne APLATIE : structure + composition + metadonnees."""
    row = structure_features(cif_bytes, disorder_threshold)
    row.update(amino_acid_composition(record["sequence"]))
    row.update({
        "accession": record["accession"],
        "gene": record["gene"],
        "label": record["label"],
        "seq_length": len(record["sequence"]),
    })
    return row
