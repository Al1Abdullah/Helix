from helix.clients.trialsClient import TrialsClient
from helix.utils.formatter import Formatter
from helix.utils.synonyms import expand
from helix.cache import trials_cache
from helix.logger import get_logger

_client = TrialsClient()
_fmt    = Formatter()
_log    = get_logger(__name__)


async def findTrials(condition: str, location: str = None, limit: int = 10) -> list[dict]:
    """Find active clinical trials. Synonym-expanded, cached 3 min. Never raises."""
    condition = expand(condition)
    key = f"trials:{condition.lower().strip()}:{location or ''}:{limit}"
    cached = await trials_cache.get(key)
    if cached is not None:
        _log.info("cache_hit", extra={"tool": "trials", "condition": condition})
        return cached
    try:
        raw = await _client.search(condition, location, limit)
        result = _fmt.shapeTrialResults(raw)
        await trials_cache.set(key, result)
        _log.info("fetched", extra={"tool": "trials", "condition": condition, "count": len(result)})
        return result
    except Exception as e:
        _log.warning("error", extra={"tool": "trials", "error": str(e)})
        return [{"id": "", "title": f"[error: {e}]", "status": "", "phase": [], "url": ""}]
