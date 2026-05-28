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
    title = trial.get("title", "").lower()
    summary = trial.get("summary", "").lower()

    score += min(sum(1 for w in conditionWords if w in title) * 15, 40)
    score += min(sum(1 for w in conditionWords if w in summary) * 5, 20)

    phase = trial.get("phase", [])
    if any(p in ["PHASE3", "PHASE4"] for p in phase):
        score += 10

    return min(score, 100)


async def matchEligibility(condition: str, age: int, location: str = None, limit: int = 10):
    raw = await client.search(condition, location, limit * 2)
    trials = formatter.shapeTrialResults(raw)

    scored = []
    for t in trials:
        s = scoreMatch(t, age, condition)
        if s > 0:
            scored.append({**t, "matchScore": s})

    scored.sort(key=lambda x: x["matchScore"], reverse=True)
    return scored[:limit]
