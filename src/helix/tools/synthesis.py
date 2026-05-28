"""
Helix synthesis pipeline — deterministic weighted vector scoring.

final_score = 100 * (
    0.35 * condition_match +
    0.30 * eligibility_fit +
    0.20 * evidence_support +
    0.15 * trial_phase_maturity
)
All sub-scores normalized to [0, 1]. Results cached 5 min per
(condition, age, location, sex).

v1.3.0: expanded_from populated in ClinicalInsight when abbreviation is resolved.
v1.2.0: synonym expansion + sex param + _hard_gate sex check.
v1.1.0: eligibility_fit computes age-window centrality (was hardcoded 1.0).
"""
import asyncio
import time
from helix.utils.synonyms import expand
from helix.tools.eligibility import matchEligibility
from helix.tools.pubmed import searchPapers
from helix.clients.fdaClient import FdaClient
from helix.utils.formatter import Formatter
from helix.config.weights import WEIGHTS
from helix.cache import synthesis_cache
from helix.logger import get_logger
from helix.models import (
    TrialProfile, ScoreVector, ExplainabilityVector,
    ClinicalInsight, SynthesisResult, ExcludedTrial,
)

_fda = FdaClient()
_fmt = Formatter()
_log = get_logger(__name__)


def _phase_score(phase: list) -> float:
    if not isinstance(phase, list):
        return 0.5
    if any(p in ["PHASE3", "PHASE4"] for p in phase):
        return 1.0
    if "PHASE2" in phase:
        return 0.6
    if "PHASE1" in phase:
        return 0.3
    return 0.5


def _norm(value: float, max_val: float) -> float:
    return min(float(value) / float(max_val), 1.0) if max_val > 0 else 0.0


def _hard_gate(trial: dict, age: int, sex: str = None) -> tuple[bool, str]:
    mn, mx = trial.get("min_age"), trial.get("max_age")
    if isinstance(mn, int) and age < mn:
        return False, f"age {age} below min {mn}"
    if isinstance(mx, int) and age > mx:
        return False, f"age {age} above max {mx}"
    if sex:
        trial_sex = (trial.get("sex") or "ALL").upper()
        if trial_sex != "ALL" and trial_sex != sex.upper():
            return False, f"sex mismatch: trial={trial_sex}, patient={sex.upper()}"
    if not trial.get("id"):
        return False, "missing trial ID"
    if not trial.get("title"):
        return False, "missing trial title"
    return True, ""


def _eligibility_fit_score(trial: dict, age: int) -> float:
    """
    Age-window centrality score. Center=1.0, edge=0.5, open enrollment=0.75.
    Range: [0.5, 1.0]. Hard gate already excluded out-of-window patients.
    """
    mn = trial.get("min_age")
    mx = trial.get("max_age")
    if mn is None and mx is None:
        return 0.75
    lo = mn if mn is not None else 0
    hi = mx if mx is not None else 120
    center = (lo + hi) / 2.0
    half_width = max((hi - lo) / 2.0, 1.0)
    dist = abs(age - center) / half_width
    return round(max(0.5, 1.0 - dist * 0.5), 4)


def buildTrialProfile(trial: dict, age: int, condition: str, papers: list, drugs: list) -> dict:
    cond_tok  = set((condition or "").lower().split())
    title_tok = set((trial.get("title") or "").lower().split())
    overlap   = len(cond_tok & title_tok)
    cond_m    = _norm(overlap, max(len(cond_tok), 1))

    ev_hits = 0
    for p in papers:
        if not isinstance(p, dict):
            continue
        title_match    = bool(set((p.get("title") or "").lower().split()) & cond_tok)
        abstract_match = bool(set((p.get("abstract") or "").lower().split()) & cond_tok)
        if title_match or abstract_match:
            ev_hits += 1
    ev_m = _norm(ev_hits, max(len(papers), 1))

    phase   = trial.get("phase") or []
    phase_m = _phase_score(phase)
    elig_m  = _eligibility_fit_score(trial, age)

    score = round(100.0 * (
        WEIGHTS["condition_match"]        * cond_m
        + WEIGHTS["eligibility_fit"]      * elig_m
        + WEIGHTS["evidence_support"]     * ev_m
        + WEIGHTS["trial_phase_maturity"] * phase_m
    ), 2)

    mn, mx = trial.get("min_age"), trial.get("max_age")
    age_pen = 0.0
    if isinstance(mn, int) and age < mn:
        age_pen = round((mn - age) / max(mn, 1), 3)
    elif isinstance(mx, int) and age > mx:
        age_pen = round((age - mx) / max(age, 1), 3)

    flags = []
    if cond_m  < 0.2: flags.append("LOW_CONDITION_MATCH")
    if phase_m <= 0.3: flags.append("EARLY_STAGE_TRIAL")
    if ev_m    < 0.1: flags.append("LOW_EVIDENCE_SUPPORT")

    return TrialProfile(
        id=trial.get("id") or "",
        title=trial.get("title") or "",
        url=trial.get("url") or "",
        phase=phase,
        final_score=score,
        score_vector=ScoreVector(
            condition_match=round(cond_m, 4),
            eligibility_fit=round(elig_m, 4),
            evidence_support=round(ev_m, 4),
            trial_phase_maturity=round(phase_m, 4),
        ),
        explainability_vector=ExplainabilityVector(
            condition_overlap_raw=overlap,
            evidence_hits_raw=ev_hits,
            age_penalty=age_pen,
            phase_penalty=round(1.0 - phase_m, 3),
        ),
        risk_flags=flags,
    ).model_dump()


def buildClinicalInsight(
    profiles: list,
    condition: str,
    expanded_from: str = None,
) -> dict:
    if not profiles:
        return ClinicalInsight(
            condition=condition or "",
            expanded_from=expanded_from,
        ).model_dump()
    scores = [p.get("final_score", 0.0) for p in profiles]
    return ClinicalInsight(
        total_trials=len(profiles),
        top_score=round(max(scores), 2),
        average_score=round(sum(scores) / len(scores), 2),
        condition=condition or "",
        expanded_from=expanded_from,
    ).model_dump()


async def synthesizeEvidence(
    condition: str,
    age: int,
    location: str = None,
    sex: str = None,
) -> dict:
    """Full cross-database synthesis. Cached 5 min per (condition, age, location, sex)."""
    # Expand abbreviation and record original for response transparency
    original = condition.strip()
    condition = expand(original)
    expanded_from = original if condition != original else None

    key = f"synthesis:{condition.lower()}:{age}:{location or ''}:{sex or ''}"
    cached = await synthesis_cache.get(key)
    if cached is not None:
        _log.info("cache_hit", extra={"tool": "synthesis", "condition": condition, "age": age})
        return cached

    t0 = time.monotonic()
    # Pass sex=None so ALL trials (including sex-mismatched) come back from
    # matchEligibility. The _hard_gate below is the sole sex authority inside
    # synthesis, ensuring sex-rejected trials appear in excludedTrials.
    trials, papers = await asyncio.gather(
        matchEligibility(condition, age, location, limit=16, sex=None),
        searchPapers(condition, limit=5),
    )

    try:
        drugs_raw = await _fda.searchByIndication(condition, limit=3)
        drugs = _fmt.shapeDrugResults(drugs_raw) if isinstance(drugs_raw, dict) else []
    except Exception:
        drugs = []

    eligible, excluded = [], []
    for t in (trials or []):
        ok, reason = _hard_gate(t, age, sex)
        if ok:
            eligible.append(t)
        else:
            excluded.append(ExcludedTrial(
                id=t.get("id") or "",
                title=t.get("title") or "",
                exclusion_reason=reason,
            ).model_dump())

    profiles = sorted(
        [buildTrialProfile(t, age, condition, papers or [], drugs) for t in eligible],
        key=lambda p: p.get("final_score", 0.0),
        reverse=True,
    )

    result = SynthesisResult(
        clinicalInsight=buildClinicalInsight(profiles, condition, expanded_from),
        trialProfiles=profiles,
        excludedTrials=excluded,
    ).model_dump()

    elapsed = round((time.monotonic() - t0) * 1000, 1)
    _log.info("synthesis_done", extra={
        "condition": condition, "age": age, "sex": sex or "any",
        "expanded_from": expanded_from,
        "scored": len(profiles), "excluded": len(excluded), "ms": elapsed,
    })

    await synthesis_cache.set(key, result)
    return result
