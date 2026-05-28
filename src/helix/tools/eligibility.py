from helix.clients.trialsClient import TrialsClient
from helix.utils.formatter import Formatter

client = TrialsClient()
formatter = Formatter()

def scoreMatch(trial: dict, age: int, condition: str) -> int:
    """
    Scores how well a trial matches a patient profile.
    Returns 0-100. Higher is better fit.
    """
    score = 50

    minAge = trial.get("minimumAge", "")
    maxAge = trial.get("maximumAge", "")

    if minAge:
        try:
            minYears = int(minAge.replace(" Years", "").replace(" Year", "").strip())
            if age < minYears:
                return 0
            score += 20
        except ValueError:
            pass

    if maxAge:
        try:
            maxYears = int(maxAge.replace(" Years", "").replace(" Year", "").strip())
            if age > maxYears:
                return 0
            score += 20
        except ValueError:
            pass

    conditionLower = condition.lower()
    titleLower = trial.get("title", "").lower()
    summaryLower = trial.get("summary", "").lower()

    if conditionLower in titleLower:
        score += 20
    elif any(word in titleLower for word in conditionLower.split()):
        score += 10

    if conditionLower in summaryLower:
        score += 10

    return min(score, 100)


async def matchEligibility(condition: str, age: int, location: str = None, limit: int = 10) -> list[dict]:
    """
    Match a patient profile against clinical trials and rank by eligibility fit.
    Returns trials sorted by match score, highest first.
    """
    raw = await client.search(condition, location, limit * 2)
    trials = formatter.shapeTrialResults(raw)

    scored = []
    for trial in trials:
        score = scoreMatch(trial, age, condition)
        if score > 0:
            scored.append({**trial, "matchScore": score})

    scored.sort(key=lambda t: t["matchScore"], reverse=True)
    return scored[:limit]
