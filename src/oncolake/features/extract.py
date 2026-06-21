"""Extraction de features (zone staging). gemmi pour parser le .cif, Polars pour la table."""
import gemmi
import numpy as np
import polars as pl

from ..schemas import AA20


def amino_acid_composition(sequence: str) -> dict[str, float]:
    n = len(sequence) or 1
    return {f"aa_{a}": sequence.count(a) / n for a in AA20}


def structure_features(cif_bytes: bytes, disorder_threshold: int = 70) -> dict:
    """pLDDT (B-factor des CA) + rayon de giration depuis le contenu .cif."""
    structure = gemmi.read_structure_from_string(
        cif_bytes.decode("utf-8"), format=gemmi.CoorFormat.Mmcif
    )
    model = structure[0]
    plddt, coords = [], []
    for chain in model:
        for res in chain:
            ca = res.find_atom("CA", "*")
            if ca is not None:
                plddt.append(ca.b_iso)
                coords.append([ca.pos.x, ca.pos.y, ca.pos.z])
    plddt = np.asarray(plddt)
    coords = np.asarray(coords)
    center = coords.mean(axis=0)
    rg = float(np.sqrt(((coords - center) ** 2).sum(axis=1).mean()))
    return {
        "n_residues_structure": int(len(plddt)),
        "plddt_mean": float(plddt.mean()),
        "pct_low_confidence": float((plddt < disorder_threshold).mean() * 100),
        "radius_of_gyration": rg,
    }


def _read(cif_bytes: bytes) -> gemmi.Structure:
    return gemmi.read_structure_from_string(cif_bytes.decode("utf-8"), format=gemmi.CoorFormat.Mmcif)


def build_feature_frame(records: list[dict]) -> pl.DataFrame:
    """Assemble une liste de dicts de features en DataFrame Polars (ecrit ensuite en Parquet)."""
    return pl.DataFrame(records)
