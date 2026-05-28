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


# --- _eligibility_fit_score ---

def test_elig_fit_center():
    """Patient at exact center of window → 1.0."""
    t = {"min_age": 30, "max_age": 50}
    assert _eligibility_fit_score(t, 40) == 1.0

def test_elig_fit_at_min_edge():
    """Patient at minimum edge → 0.5."""
    t = {"min_age": 30, "max_age": 50}
    assert _eligibility_fit_score(t, 30) == 0.5

def test_elig_fit_at_max_edge():
    """Patient at maximum edge → 0.5."""
    t = {"min_age": 30, "max_age": 50}
    assert _eligibility_fit_score(t, 50) == 0.5

def test_elig_fit_open_enrollment():
    """No age constraints → 0.75 (inclusive but not tailored)."""
    t = {"min_age": None, "max_age": None}
    assert _eligibility_fit_score(t, 45) == 0.75

def test_elig_fit_range_is_0_5_to_1():
    """Score is always in [0.5, 1.0] for any valid in-window age."""
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
