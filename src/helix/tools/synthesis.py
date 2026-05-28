"""
Helix synthesis pipeline — deterministic, vector-based clinical evidence scoring.

Score formula (weighted sum → [0, 100]):
  final_score = 100 * (
      0.35 * condition_match +
      0.30 * eligibility_fit +
      0.20 * evidence_support +
      0.15 * trial_phase_maturity
  )

All sub-scores are normalized to [0, 1] before weighting.
"""

import asyncio
from helix.tools.eligibility import matchEligibility
from helix.tools.pubmed import searchPapers
from helix.clients.fdaClient import FdaClient
from helix.utils.formatter import Formatter
from helix.config.weights import WEIGHTS

_fda_client = FdaClient()
_formatter = Formatter()


# ---------------------------------------------------------------------------
# Sub-score helpers
# ---------------------------------------------------------------------------

def _phase_maturity_score(phase: list) -> float:
    """Map trial phase list to a [0, 1] maturity score."""
    if not isinstance(phase, list):
        return 0.5
    if any(p in ["PHASE3", "PHASE4"] for p in phase):
        return 1.0
    if any(p == "PHASE2" for p in phase):
        return 0.6
    if any(p == "PHASE1" for p in phase):
        return 0.3
    return 0.5  # unknown phase gets neutral score


def _normalize(value: float, max_val: float) -> float:
    """Clamp value/max_val to [0, 1]. Returns 0.0 if max_val is 0."""
    if not max_val or max_val <= 0:
        return 0.0
    return min(float(value) / float(max_val), 1.0)


# ---------------------------------------------------------------------------
# Hard eligibility check (MUST run before scoring)
# ---------------------------------------------------------------------------

def _passes_hard_eligibility(trial: dict, age: int) -> tuple[bool, str]:
    """
    Returns (True, "") if patient passes hard eligibility.
    Returns (False, reason_string) if trial must be excluded.
    """
    min_age = trial.get("min_age")
    max_age = trial.get("max_age")

    if isinstance(min_age, int) and age < min_age:
        return False, f"age {age} below minimum {min_age}"
    if isinstance(max_age, int) and age > max_age:
        return False, f"age {age} above maximum {max_age}"
    if not trial.get("id"):
        return False, "missing trial ID"
    if not trial.get("title"):
        return False, "missing trial title"

    return True, ""


# ---------------------------------------------------------------------------
# Core profile builder
# ---------------------------------------------------------------------------

def buildTrialProfile(
    trial: dict,
    age: int,
    condition: str,
    papers: list,
    drugs: list,
) -> dict:
    """
    Build a fully-scored trial profile with explainability vectors.
    Assumes the trial has already PASSED hard eligibility.
    """
    # --- Condition match ---
    cond_tokens = set((condition or "").lower().split())
    title_tokens = set((trial.get("title") or "").lower().split())
    condition_overlap = len(cond_tokens & title_tokens)
    condition_match = _normalize(condition_overlap, max(len(cond_tokens), 1))

    # --- Evidence support ---
    evidence_hits = 0
    for paper in papers:
        if not isinstance(paper, dict):
            continue
        paper_tokens = set((paper.get("title") or "").lower().split())
        if paper_tokens & cond_tokens:
            evidence_hits += 1
    evidence_support = _normalize(evidence_hits, max(len(papers), 1))

    # --- Eligibility fit (1.0 = passed hard filter, which is always True here) ---
    eligibility_fit = 1.0

    # --- Phase maturity ---
    phase = trial.get("phase") or []
    phase_maturity = _phase_maturity_score(phase)

    # --- Weighted final score (0–100) ---
    final_score = round(
        100.0 * (
            WEIGHTS["condition_match"] * condition_match
            + WEIGHTS["eligibility_fit"] * eligibility_fit
            + WEIGHTS["evidence_support"] * evidence_support
            + WEIGHTS["trial_phase_maturity"] * phase_maturity
        ),
        2,
    )

    # --- Explainability penalties ---
    min_age = trial.get("min_age")
    max_age = trial.get("max_age")
    age_penalty = 0.0
    if isinstance(min_age, int) and age < min_age:
        age_penalty = round((min_age - age) / max(min_age, 1), 3)
    elif isinstance(max_age, int) and age > max_age:
        age_penalty = round((age - max_age) / max(age, 1), 3)

    phase_penalty = round(1.0 - phase_maturity, 3)

    # --- Risk flags ---
    risk_flags = []
    if condition_match < 0.2:
        risk_flags.append("LOW_CONDITION_MATCH")
    if phase_maturity <= 0.3:
        risk_flags.append("EARLY_STAGE_TRIAL")
    if evidence_support < 0.1:
        risk_flags.append("LOW_EVIDENCE_SUPPORT")

    return {
        "id": trial.get("id") or "",
        "title": trial.get("title") or "",
        "url": trial.get("url") or "",
        "phase": phase,
        "final_score": final_score,
        "score_vector": {
            "condition_match": round(condition_match, 4),
            "eligibility_fit": round(eligibility_fit, 4),
            "evidence_support": round(evidence_support, 4),
            "trial_phase_maturity": round(phase_maturity, 4),
        },
        "explainability_vector": {
            "condition_overlap_raw": condition_overlap,
            "evidence_hits_raw": evidence_hits,
            "age_penalty": age_penalty,
            "phase_penalty": phase_penalty,
        },
        "risk_flags": risk_flags,
    }


# ---------------------------------------------------------------------------
# Clinical insight summary
# ---------------------------------------------------------------------------

def buildClinicalInsight(profiles: list, condition: str) -> dict:
    """Aggregate summary statistics over all scored profiles."""
    if not profiles:
        return {
            "total_trials": 0,
            "top_score": 0.0,
            "average_score": 0.0,
            "condition": condition or "",
        }

    scores = [p.get("final_score", 0.0) for p in profiles]
    return {
        "total_trials": len(profiles),
        "top_score": round(max(scores), 2),
        "average_score": round(sum(scores) / len(scores), 2),
        "condition": condition or "",
    }


# ---------------------------------------------------------------------------
# Main synthesis entry point
# ---------------------------------------------------------------------------

async def synthesizeEvidence(
    condition: str, age: int, location: str = None
) -> dict:
    """
    Cross-database clinical evidence synthesis.

    Steps:
      1. Fetch candidate trials + PubMed papers concurrently.
      2. Fetch FDA drug context for the condition.
      3. Hard eligibility filter — split into eligible/excluded.
      4. Score eligible trials with deterministic vector model.
      5. Return structured report with explainability.

    Returns:
      {
        "clinicalInsight": { total_trials, top_score, average_score, condition },
        "trialProfiles":   [ ... scored trial profiles ... ],
        "excludedTrials":  [ ... debug list of rejected trials ... ]
      }
    """
    # Step 1: concurrent fetch
    trials, papers = await asyncio.gather(
        matchEligibility(condition, age, location, limit=8),
        searchPapers(condition, limit=5),
    )

    # Step 2: FDA drug context (fire-and-forget safe)
    try:
        drugs_raw = await _fda_client.searchByIndication(condition, limit=3)
        drugs = _formatter.shapeDrugResults(drugs_raw) if isinstance(drugs_raw, dict) else []
    except Exception:
        drugs = []

    # Step 3: hard eligibility split
    eligible_trials = []
    excluded_trials = []

    for trial in (trials or []):
        passed, reason = _passes_hard_eligibility(trial, age)
        if passed:
            eligible_trials.append(trial)
        else:
            excluded_trials.append({
                "id": trial.get("id") or "",
                "title": trial.get("title") or "",
                "exclusion_reason": reason,
            })

    # Step 4: score eligible trials
    profiles = [
        buildTrialProfile(t, age, condition, papers or [], drugs)
        for t in eligible_trials
    ]

    # Sort by score descending for easy reading
    profiles.sort(key=lambda p: p.get("final_score", 0.0), reverse=True)

    # Step 5: assemble report
    return {
        "clinicalInsight": buildClinicalInsight(profiles, condition),
        "trialProfiles": profiles,
        "excludedTrials": excluded_trials,
    }
