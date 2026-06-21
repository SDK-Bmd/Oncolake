"""Tests unitaires des features (sans reseau)."""
from oncolake.features.extract import amino_acid_composition


def test_aa_composition_sums_to_one():
    comp = amino_acid_composition("ACDEFGHIKLMNPQRSTVWY")  # un de chaque
    assert abs(sum(comp.values()) - 1.0) < 1e-9
    assert comp["aa_A"] == 1 / 20


def test_aa_composition_empty():
    comp = amino_acid_composition("")
    assert sum(comp.values()) == 0.0
