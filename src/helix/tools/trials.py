from helix.clients.trialsClient import TrialsClient
from helix.utils.formatter import Formatter

_client = TrialsClient()
_formatter = Formatter()


async def findTrials(
    condition: str, location: str = None, limit: int = 10
) -> list[dict]:
    """
    Find active clinical trials for a condition.
    Returns a list of canonical Trial dicts (never raises).
    """
    try:
        raw = await _client.search(condition, location, limit)
        return _formatter.shapeTrialResults(raw)
    except Exception as err:
        return [{"id": "", "title": f"[search error: {err}]", "status": "", "phase": [], "url": ""}]
