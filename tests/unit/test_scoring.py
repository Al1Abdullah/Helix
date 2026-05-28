"""Unit tests for synthesis scoring functions — pure logic, no I/O."""
import pytest
from helix.tools.synthesis import (
    _phase_score,
    _norm,
    _hard_gate,
    _eligibility_fit_score,
    buildClinicalInsight,
)


# --- _phase_score ---

def test_phase_score_p4():
    assert _phase_score(["PHASE4"]) == 1.0

def test_phase_score_p3():
    assert _phase_score(["PHASE3"]) == 1.0

def test_phase_score_p2():
    assert _phase_score(["PHASE2"]) == 0.6

def test_phase_score_p1():
    assert _phase_score(["PHASE1"]) == 0.3

def test_phase_score_empty():
    assert _phase_score([]) == 0.5

def test_phase_score_not_list():
    assert _phase_score(None) == 0.5


# --- _norm ---

def test_norm_zero_value():
    assert _norm(0, 10) == 0.0

def test_norm_full():
    assert _norm(10, 10) == 1.0

def test_norm_clamp():
    assert _norm(15, 10) == 1.0

def test_norm_zero_max():
    assert _norm(5, 0) == 0.0

def test_norm_partial():
    assert abs(_norm(5, 10) - 0.5) < 1e-9


# --- _hard_gate ---

def test_hard_gate_passes():
    t = {"id": "NCT001", "title": "Test Trial", "min_age": 18, "max_age": 65}
    ok, reason = _hard_gate(t, 45)
    assert ok is True
    assert reason == ""

def test_hard_gate_age_too_young():
    t = {"id": "NCT001", "title": "Test", "min_age": 18}
    ok, reason = _hard_gate(t, 16)
    assert ok is False
    assert "below" in reason

def test_hard_gate_age_too_old():
    t = {"id": "NCT001", "title": "Test", "max_age": 65}
    ok, reason = _hard_gate(t, 70)
    assert ok is False
    assert "above" in reason

def test_hard_gate_missing_id():
    t = {"id": "", "title": "Test"}
    ok, reason = _hard_gate(t, 45)
    assert ok is False
    assert "ID" in reason

def test_hard_gate_missing_title():
    t = {"id": "NCT001", "title": ""}
    ok, reason = _hard_gate(t, 45)
    assert ok is False
    assert "title" in reason

def test_hard_gate_no_age_constraints():
    t = {"id": "NCT001", "title": "Test", "min_age": None, "max_age": None}
    ok, _ = _hard_gate(t, 99)
    assert ok is True

def test_hard_gate_sex_mismatch():
    t = {"id": "NCT001", "title": "Test", "sex": "MALE"}
    ok, reason = _hard_gate(t, 45, sex="FEMALE")
    assert ok is False
    assert "sex mismatch" in reason

def test_hard_gate_sex_all_passes_any_patient():
    t = {"id": "NCT001", "title": "Test", "sex": "ALL"}
    ok, _ = _hard_gate(t, 45, sex="FEMALE")
    assert ok is True

def test_hard_gate_sex_match_passes():
    t = {"id": "NCT001", "title": "Test", "sex": "FEMALE"}
    ok, _ = _hard_gate(t, 45, sex="FEMALE")
    assert ok is True

def test_hard_gate_no_sex_filter_skips_check():
    t = {"id": "NCT001", "title": "Test", "sex": "MALE"}
    ok, _ = _hard_gate(t, 45, sex=None)
    assert ok is True


# --- _eligibility_fit_score ---

def test_elig_fit_center():
    t = {"min_age": 30, "max_age": 50}
    assert _eligibility_fit_score(t, 40) == 1.0

def test_elig_fit_at_min_edge():
    t = {"min_age": 30, "max_age": 50}
    assert _eligibility_fit_score(t, 30) == 0.5

def test_elig_fit_at_max_edge():
    t = {"min_age": 30, "max_age": 50}
    assert _eligibility_fit_score(t, 50) == 0.5

def test_elig_fit_open_enrollment():
    t = {"min_age": None, "max_age": None}
    assert _eligibility_fit_score(t, 45) == 0.75

def test_elig_fit_range_is_0_5_to_1():
    t = {"min_age": 18, "max_age": 80}
    for age in [18, 30, 49, 65, 80]:
        score = _eligibility_fit_score(t, age)
        assert 0.5 <= score <= 1.0, f"score {score} out of range for age {age}"

def test_elig_fit_only_min_age():
    t = {"min_age": 18, "max_age": None}
    score = _eligibility_fit_score(t, 50)
    assert 0.5 <= score <= 1.0

def test_elig_fit_only_max_age():
    t = {"min_age": None, "max_age": 65}
    score = _eligibility_fit_score(t, 30)
    assert 0.5 <= score <= 1.0


# --- buildClinicalInsight ---

def test_build_insight_empty():
    r = buildClinicalInsight([], "diabetes")
    assert r["total_trials"] == 0
    assert r["condition"] == "diabetes"
    assert r["top_score"] == 0.0

def test_build_insight_scores():
    profiles = [{"final_score": 80.0}, {"final_score": 60.0}, {"final_score": 70.0}]
    r = buildClinicalInsight(profiles, "cancer")
    assert r["total_trials"] == 3
    assert r["top_score"] == 80.0
    assert r["average_score"] == 70.0
    assert r["condition"] == "cancer"

def test_build_insight_expanded_from_set():
    """expanded_from is passed through to the response when abbreviation was resolved."""
    profiles = [{"final_score": 75.0}]
    r = buildClinicalInsight(profiles, "Type 2 Diabetes", expanded_from="T2D")
    assert r["expanded_from"] == "T2D"
    assert r["condition"] == "Type 2 Diabetes"

def test_build_insight_no_expansion():
    """expanded_from is None when no abbreviation was resolved."""
    profiles = [{"final_score": 75.0}]
    r = buildClinicalInsight(profiles, "Type 2 Diabetes", expanded_from=None)
    assert r["expanded_from"] is None

# --- sex exclusion transparency (v1.4.0) ---

def test_hard_gate_trial_female_patient_male():
    """Inverse sex mismatch: trial requires FEMALE, patient is MALE."""
    t = {"id": "NCT001", "title": "Test", "sex": "FEMALE"}
    ok, reason = _hard_gate(t, 45, sex="MALE")
    assert ok is False
    assert "sex mismatch" in reason
    assert "FEMALE" in reason
    assert "MALE" in reason

def test_hard_gate_no_sex_field_defaults_to_all():
    """Trial with no sex field should be treated as ALL and pass any patient."""
    t = {"id": "NCT001", "title": "Test"}  # no "sex" key
    ok, _ = _hard_gate(t, 45, sex="MALE")
    assert ok is True

def test_build_insight_zero_top_score_when_empty():
    """Empty profile list should return top_score=0.0, not crash."""
    r = buildClinicalInsight([], "NSCLC", expanded_from="nsclc")
    assert r["top_score"] == 0.0
    assert r["expanded_from"] == "nsclc"
    assert r["condition"] == "NSCLC"

def test_hard_gate_age_exactly_at_min_passes():
    """Age exactly equal to min_age is valid (inclusive boundary)."""
    t = {"id": "NCT001", "title": "Test", "min_age": 18, "max_age": 65}
    ok, _ = _hard_gate(t, 18)
    assert ok is True

def test_hard_gate_age_exactly_at_max_passes():
    """Age exactly equal to max_age is valid (inclusive boundary)."""
    t = {"id": "NCT001", "title": "Test", "min_age": 18, "max_age": 65}
    ok, _ = _hard_gate(t, 65)
    assert ok is True
