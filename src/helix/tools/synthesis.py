"""
Helix synthesis pipeline — deterministic weighted vector scoring.

final_score = 100 * (
    0.35 * condition_match +
    0.30 * eligibility_fit +
    0.20 * evidence_support +
    0.15 * trial_phase_maturity
)
All sub-scores normalized to [0, 1]. Results cached 5 min.
"""
import asyncio
import time
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


def _hard_gate(trial: dict, age: int) -> tuple[bool, str]:
    mn, mx = trial.get("min_age"), trial.get("max_age")
    if isinstance(mn, int) and age < mn:
        return False, f"age {age} below min {mn}"
    if isinstance(mx, int) and age > mx:
        return False, f"age {age} above max {mx}"
    if not trial.get("id"):
        return False, "missing trial ID"
    if not trial.get("title"):
        return False, "missing trial title"
    return True, ""


def buildTrialProfile(trial: dict, age: int, condition: str, papers: list, drugs: list) -> dict:
    cond_tok  = set((condition or "").lower().split())
    title_tok = set((trial.get("title") or "").lower().split())
    overlap   = len(cond_tok & title_tok)
    cond_m    = _norm(overlap, max(len(cond_tok), 1))

    ev_hits   = sum(1 for p in papers if isinstance(p, dict) and (set((p.get("title") or "").lower().split()) & cond_tok))
    ev_m      = _norm(ev_hits, max(len(papers), 1))

    phase     = trial.get("phase") or []
    phase_m   = _phase_score(phase)
    elig_m    = 1.0

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
    if cond_m    < 0.2: flags.append("LOW_CONDITION_MATCH")
    if phase_m   <= 0.3: flags.append("EARLY_STAGE_TRIAL")
    if ev_m      < 0.1: flags.append("LOW_EVIDENCE_SUPPORT")

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


def buildClinicalInsight(profiles: list, condition: str) -> dict:
    if not profiles:
        return ClinicalInsight(condition=condition or "").model_dump()
    scores = [p.get("final_score", 0.0) for p in profiles]
    return ClinicalInsight(
        total_trials=len(profiles),
        top_score=round(max(scores), 2),
        average_score=round(sum(scores) / len(scores), 2),
        condition=condition or "",
    ).model_dump()


async def synthesizeEvidence(condition: str, age: int, location: str = None) -> dict:
    """Full cross-database synthesis. Cached 5 min per (condition, age, location)."""
    key = f"synthesis:{condition.lower().strip()}:{age}:{location or ''}"
    cached = await synthesis_cache.get(key)
    if cached is not None:
        _log.info("cache_hit", extra={"tool": "synthesis", "condition": condition, "age": age})
        return cached

    t0 = time.monotonic()
    trials, papers = await asyncio.gather(
        matchEligibility(condition, age, location, limit=8),
        searchPapers(condition, limit=5),
    )

    try:
        drugs_raw = await _fda.searchByIndication(condition, limit=3)
        drugs = _fmt.shapeDrugResults(drugs_raw) if isinstance(drugs_raw, dict) else []
    except Exception:
        drugs = []

    eligible, excluded = [], []
    for t in (trials or []):
        ok, reason = _hard_gate(t, age)
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
        clinicalInsight=buildClinicalInsight(profiles, condition),
        trialProfiles=profiles,
        excludedTrials=excluded,
    ).model_dump()

    elapsed = round((time.monotonic() - t0) * 1000, 1)
    _log.info("synthesis_done", extra={
        "condition": condition, "age": age,
        "scored": len(profiles), "excluded": len(excluded), "ms": elapsed,
    })

    await synthesis_cache.set(key, result)
    return result
