import asyncio
from helix.tools.eligibility import matchEligibility
from helix.tools.pubmed import searchPapers
from helix.clients.fdaClient import FdaClient
from helix.config.weights import WEIGHTS

fdaClient = FdaClient()


def _phase_score(phase):
    phase = phase if isinstance(phase, list) else []
    if any(p in ["PHASE3", "PHASE4"] for p in phase):
        return 1.0
    if any(p in ["PHASE2"] for p in phase):
        return 0.6
    if any(p in ["PHASE1"] for p in phase):
        return 0.3
    return 0.5


def _normalize(x, max_val):
    if max_val == 0:
        return 0.0
    return min(x / max_val, 1.0)


def buildTrialProfile(trial: dict, age: int, condition: str, papers: list, drugs: list):

    score_raw = trial.get("matchScore", 0)

    min_age = trial.get("minimumAge")
    max_age = trial.get("maximumAge")

    eligible = True
    if isinstance(min_age, int) and age < min_age:
        eligible = False
    if isinstance(max_age, int) and age > max_age:
        eligible = False

    title = trial.get("title", "")
    text = (title + " " + trial.get("summary", "")).lower()

    cond_tokens = set(condition.lower().split())
    title_tokens = set(title.lower().split())

    condition_overlap = len(cond_tokens & title_tokens)
    condition_match = _normalize(condition_overlap, max(len(cond_tokens), 1))

    evidence_hits = 0
    for p in papers:
        pt = set(p.get("title", "").lower().split())
        if len(pt & cond_tokens) > 0:
            evidence_hits += 1

    evidence_support = _normalize(evidence_hits, max(len(papers), 1))

    eligibility_fit = 1.0 if eligible else 0.0
    phase_maturity = _phase_score(trial.get("phase", []))

    # WEIGHTED SCORE (real pipeline)
    score = (
        WEIGHTS["condition_match"] * condition_match +
        WEIGHTS["eligibility_fit"] * eligibility_fit +
        WEIGHTS["evidence_support"] * evidence_support +
        WEIGHTS["trial_phase_maturity"] * phase_maturity
    ) * 100

    risk_flags = []
    if not eligible:
        risk_flags.append("INELIGIBLE_AGE")
    if condition_match < 0.2:
        risk_flags.append("LOW_CONDITION_MATCH")
    if phase_maturity <= 0.3:
        risk_flags.append("EARLY_STAGE_TRIAL")

    return {
        "id": trial.get("id"),
        "score": round(score, 2),
        "drivers": {
            "condition_match": round(condition_match, 3),
            "eligibility_fit": eligibility_fit,
            "evidence_support": round(evidence_support, 3),
            "trial_phase_maturity": round(phase_maturity, 3),
        },
        "signals": {
            "condition_overlap_raw": condition_overlap,
            "evidence_hits_raw": evidence_hits,
        },
        "riskFlags": risk_flags
    }


def buildClinicalInsight(profiles, condition):
    if not profiles:
        return {
            "total_trials": 0,
            "top_score": 0,
            "average_score": 0,
            "condition": condition
        }

    scores = [p["score"] for p in profiles]
    return {
        "total_trials": len(profiles),
        "top_score": max(scores),
        "average_score": round(sum(scores) / len(scores), 2),
        "condition": condition
    }


async def synthesizeEvidence(condition: str, age: int, location: str = None) -> dict:

    trials, papers = await asyncio.gather(
        matchEligibility(condition, age, location, limit=8),
        searchPapers(condition, limit=5),
    )

    drugs_raw = fdaClient.searchByIndication(condition, limit=3)
    drugs = drugs_raw.get("results", []) if isinstance(drugs_raw, dict) else []

    profiles = [
        buildTrialProfile(t, age, condition, papers, drugs)
        for t in trials
    ]

    return {
        "clinicalInsight": buildClinicalInsight(profiles, condition),
        "trialProfiles": profiles
    }
