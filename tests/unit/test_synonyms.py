"""Unit tests for condition synonym expansion — no I/O."""
import pytest
from helix.utils.synonyms import expand


def test_uppercase_abbreviation():
    assert expand("T2D") == "Type 2 Diabetes"

def test_lowercase_abbreviation():
    assert expand("nsclc") == "Non-Small Cell Lung Cancer"

def test_mixed_case_abbreviation():
    assert expand("COPD") == "Chronic Obstructive Pulmonary Disease"

def test_passthrough_canonical_name():
    assert expand("Type 2 Diabetes") == "Type 2 Diabetes"

def test_passthrough_unknown_string():
    assert expand("XYZ123") == "XYZ123"

def test_strips_leading_trailing_whitespace():
    assert expand("  t2d  ") == "Type 2 Diabetes"

def test_hiv():
    assert expand("HIV") == "Human Immunodeficiency Virus"

def test_afib():
    assert expand("afib") == "Atrial Fibrillation"

def test_empty_string_passthrough():
    assert expand("") == ""

def test_ra_rheumatoid_arthritis():
    assert expand("RA") == "Rheumatoid Arthritis"
