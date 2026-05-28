"""Unit tests for Formatter and _parse_age — no network calls."""
import pytest
from helix.utils.formatter import Formatter, _parse_age


# --- _parse_age ---

def test_parse_years():
    assert _parse_age("18 Years") == 18

def test_parse_years_large():
    assert _parse_age("75 Years") == 75

def test_parse_months():
    assert _parse_age("6 Months") == 0  # 6 // 12 = 0

def test_parse_months_large():
    assert _parse_age("24 Months") == 2

def test_parse_empty():
    assert _parse_age("") is None

def test_parse_none():
    assert _parse_age(None) is None

def test_parse_invalid():
    assert _parse_age("N/A") is None


# --- Formatter.shapeTrialResults ---

def test_shape_trials_basic(sample_trials_response):
    results = Formatter().shapeTrialResults(sample_trials_response)
    assert len(results) == 2

def test_shape_trials_first_trial(sample_trials_response):
    t = Formatter().shapeTrialResults(sample_trials_response)[0]
    assert t["id"] == "NCT00000001"
    assert t["min_age"] == 18
    assert t["max_age"] == 65
    assert t["phase"] == ["PHASE3"]
    assert t["status"] == "RECRUITING"
    assert "clinicaltrials.gov/study/NCT00000001" in t["url"]

def test_shape_trials_empty():
    assert Formatter().shapeTrialResults({}) == []

def test_shape_trials_bad_input():
    assert Formatter().shapeTrialResults(None) == []
    assert Formatter().shapeTrialResults("bad") == []


# --- Formatter.shapePaperResults ---

def test_shape_papers_basic(sample_pubmed_summaries):
    fmt = Formatter()
    papers = fmt.shapePaperResults(["12345678", "87654321"], sample_pubmed_summaries)
    assert len(papers) == 2

def test_shape_papers_fields(sample_pubmed_summaries):
    p = Formatter().shapePaperResults(["12345678"], sample_pubmed_summaries)[0]
    assert p["id"] == "12345678"
    assert "Metformin" in p["title"]
    assert p["year"] == 2023
    assert "pubmed.ncbi.nlm.nih.gov/12345678" in p["url"]

def test_shape_papers_empty():
    assert Formatter().shapePaperResults([], {}) == []


# --- Formatter.shapeDrugResults ---

def test_shape_drugs_basic(sample_fda_response):
    drugs = Formatter().shapeDrugResults(sample_fda_response)
    assert len(drugs) == 1

def test_shape_drugs_fields(sample_fda_response):
    d = Formatter().shapeDrugResults(sample_fda_response)[0]
    assert d["brand_name"] == "GLUCOPHAGE"
    assert d["generic_name"] == "METFORMIN HYDROCHLORIDE"
    assert "ORAL" in d["route"]

def test_shape_drugs_empty():
    assert Formatter().shapeDrugResults({"results": []}) == []

def test_shape_trials_no_raw_field(sample_trials_response):
    """Shaped trials must not contain the raw API response field (memory hygiene)."""
    results = Formatter().shapeTrialResults(sample_trials_response)
    for trial in results:
        assert "raw" not in trial, "raw field must not be present in shaped trial dicts"

def test_shape_trials_sex_field_present(sample_trials_response):
    """Shaped trial must include a sex field for downstream sex filtering."""
    t = Formatter().shapeTrialResults(sample_trials_response)[0]
    assert "sex" in t
