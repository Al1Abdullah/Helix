from helix.clients.trialsClient import TrialsClient
from helix.utils.formatter import Formatter
from helix.utils.synonyms import expand

_client = TrialsClient()
_formatter = Formatter()


def _legacy_score(trial: dict, age: int, condition: str) -> int:
    """
    Lightweight pre-filter score (0–100 integer).
    Used ONLY for initial ranking before the synthesis pipeline runs.
    The authoritative scoring happens in synthesis.py (vector-based).
    Returns 0 if the patient is outside the age window (hard rejection).
    """
    min_age = trial.get("min_age")
    max_age = trial.get("max_age")

    if isinstance(min_age, int) and age < min_age:
        return 0
    if isinstance(max_age, int) and age > max_age:
        return 0

    score = 40
    cond_words = condition.lower().split()
    title   = (trial.get("title") or "").lower()
    summary = (trial.get("summary") or "").lower()

    score += min(sum(1 for w in cond_words if w in title) * 15, 40)
    score += min(sum(1 for w in cond_words if w in summary) * 5, 20)

    phase = trial.get("phase") or []
    if any(p in ["PHASE3", "PHASE4"] for p in phase):
        score += 10

    return min(score, 100)


async def matchEligibility(
    condition: str,
    age: int,
    location: str = None,
    limit: int = 10,
    sex: str = None,
) -> list[dict]:
    """
    Fetch trials and return those passing basic age and sex eligibility,
    ordered by lightweight pre-filter score descending.
    v1.2.0: synonym expansion + sex filtering added.
    """
    condition = expand(condition)
    raw = await _client.search(condition, location, limit * 2)
    trials = _formatter.shapeTrialResults(raw)

    scored = []
    for t in trials:
        # Sex hard gate — skip before expensive scoring
        if sex:
            trial_sex = (t.get("sex") or "ALL").upper()
            if trial_sex != "ALL" and trial_sex != sex.upper():
                continue
        s = _legacy_score(t, age, condition)
        if s > 0:
            scored.append({**t, "match_score_legacy": s})

    scored.sort(key=lambda x: x.get("match_score_legacy", 0), reverse=True)
    return scored[:limit]
