from helix.clients.trialsClient import TrialsClient
from helix.utils.formatter import Formatter

client = TrialsClient()
formatter = Formatter()


def parseAge(ageString: str) -> int | None:
    if not ageString:
        return None
    lower = ageString.lower()
    try:
        if "month" in lower:
            return int(lower.split()[0]) // 12
        return int(lower.split()[0])
    except (ValueError, IndexError):
        return None


def scoreMatch(trial: dict, age: int, condition: str) -> int:
    minAge = parseAge(trial.get("minimumAge", ""))
    maxAge = parseAge(trial.get("maximumAge", ""))

    if minAge is not None and age < minAge:
        return 0
    if maxAge is not None and age > maxAge:
        return 0

    score = 40

    conditionWords = condition.lower().split()
    titleLower = trial.get("title", "").lower()
    summaryLower = trial.get("summary", "").lower()

    titleMatches = sum(1 for word in conditionWords if word in titleLower)
    summaryMatches = sum(1 for word in conditionWords if word in summaryLower)

    score += min(titleMatches * 15, 40)
    score += min(summaryMatches * 5, 20)

    return min(score, 100)


async def matchEligibility(
    condition: str, age: int, location: str = None, limit: int = 10
) -> list[dict]:
    try:
        raw = await client.search(condition, location, limit * 2)
    except Exception:
        return []

    trials = formatter.shapeTrialResults(raw)

    scored = []
    for trial in trials:
        score = scoreMatch(trial, age, condition)
        if score > 0:
            scored.append({**trial, "matchScore": score})

    scored.sort(key=lambda t: t["matchScore"], reverse=True)
    return scored[:limit]
