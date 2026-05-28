import asyncio
from helix.tools.eligibility import matchEligibility
from helix.tools.pubmed import searchPapers
from helix.clients.fdaClient import FdaClient

fdaClient = FdaClient()

def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))

def safe_int(x):
    if x is None:
        return None
    if isinstance(x, int):
        return x
    if isinstance(x, str):
        digits = "".join(ch for ch in x if ch.isdigit())
        return int(digits) if digits else None
    return None

def normalize_phase(phase):
    if isinstance(phase, str):
        return [phase]
    if isinstance(phase, list):
        return phase
    return []

def compute_drivers(trial, age, condition, papers):
    title = (trial.get("title") or "").lower()
    summary = (trial.get("summary") or "").lower()

    condition_tokens = set(condition.lower().split())
    title_tokens = set(title.split())

    condition_overlap = len(condition_tokens & title_tokens)
    condition_match = clamp(condition_overlap / max(1, len(condition_tokens)))

    min_age = safe_int(trial.get("minimumAge"))
    max_age = safe_int(trial.get("maximumAge"))

    eligibility_fit = 1.0
    if min_age is not None and age < min_age:
        eligibility_fit = 0.0
    if max_age is not None and age > max_age:
        eligibility_fit = 0.0

    evidence_hits = 0
    for p in papers:
        ptokens = set((p.get("title") or "").lower().split())
        if len(ptokens & condition_tokens) > 0:
            evidence_hits += 1

    evidence_support = clamp(evidence_hits / max(1, len(papers)))

    phase = normalize_phase(trial.get("phase"))
    if any(p in ["PHASE3", "PHASE4"] for p in phase):
        trial_phase_maturity = 1.0
    elif "PHASE2" in phase:
        trial_phase_maturity = 0.6
    elif "PHASE1" in phase:
        trial_phase_maturity = 0.2
    else:
        trial_phase_maturity = 0.5

    return {
        "condition_match": round(condition_match, 3),
        "eligibility_fit": eligibility_fit,
        "evidence_support": round(evidence_support, 3),
        "trial_phase_maturity": trial_phase_maturity,
        "condition_overlap_raw": condition_overlap,
        "evidence_hits_raw": evidence_hits,
    }

def compute_score(drivers):
    return round(
        100 * (
            0.35 * drivers["condition_match"] +
            0.30 * drivers["eligibility_fit"] +
            0.20 * drivers["evidence_support"] +
            0.15 * drivers["trial_phase_maturity"]
        ),
        2
    )

def compute_risk_flags(drivers):
    flags = []

    if drivers["eligibility_fit"] == 0.0:
        flags.append("INELIGIBLE_AGE")

    if drivers["condition_match"] < 0.3:
        flags.append("LOW_CONDITION_MATCH")

    if drivers["trial_phase_maturity"] <= 0.2:
        flags.append("EARLY_STAGE_TRIAL")

    if drivers["evidence_support"] < 0.2:
        flags.append("WEAK_EVIDENCE_SUPPORT")

    return flags

def buildTrialProfile(trial, age, condition, papers, drugs):
    drivers = compute_drivers(trial, age, condition, papers)
    score = compute_score(drivers)
    risk_flags = compute_risk_flags(drivers)
    phase = normalize_phase(trial.get("phase"))

    return {
        "id": trial.get("id"),
        "title": trial.get("title"),
        "eligibilityScore": score,
        "drivers": drivers,
        "riskFlags": risk_flags,
        "signals": {
            "condition_overlap_raw": drivers["condition_overlap_raw"],
            "evidence_hits_raw": drivers["evidence_hits_raw"],
        },
        "standardOfCareAlignment": (
            "late-stage"
            if any(p in ["PHASE3", "PHASE4"] for p in phase)
            else "early/experimental"
        )
    }

def buildClinicalInsight(profiles, condition):
    if not profiles:
        return {
            "total_trials": 0,
            "top_score": 0,
            "average_score": 0,
            "condition": condition
        }

    scores = [p["eligibilityScore"] for p in profiles]

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

    drugs_raw = fdaClient.search(condition, limit=3)
    drugs = drugs_raw.get("results", []) if isinstance(drugs_raw, dict) else []

    profiles = [
        buildTrialProfile(t, age, condition, papers, drugs)
        for t in trials
    ]

    return {
        "clinicalInsight": buildClinicalInsight(profiles, condition),
        "trialProfiles": profiles
    }
