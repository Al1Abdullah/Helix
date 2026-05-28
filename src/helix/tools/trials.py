from helix.clients.trialsClient import TrialsClient
from helix.utils.formatter import Formatter
from helix.utils.synonyms import expand
from helix.cache import trials_cache
from helix.logger import get_logger

_client = TrialsClient()
_fmt    = Formatter()
_log    = get_logger(__name__)


async def findTrials(
    condition: str,
    location: str = None,
    limit: int = 10,
    sex: str = None,
) -> list[dict]:
    """Find active clinical trials. Synonym-expanded, cached 3 min. Never raises.

    Args:
        condition: Medical condition or abbreviation.
        location: Optional location filter.
        limit: Max results to return.
        sex: Optional sex filter: MALE or FEMALE. Applied post-fetch.
    """
    condition = expand(condition)
    key = f"trials:{condition.lower().strip()}:{location or ''}:{limit}:{sex or ''}"
    cached = await trials_cache.get(key)
    if cached is not None:
        _log.info("cache_hit", extra={"tool": "trials", "condition": condition})
        return cached
    try:
        # Fetch extra when sex-filtering so we hit the requested limit after exclusions
        fetch_limit = limit * 2 if sex else limit
        raw = await _client.search(condition, location, fetch_limit)
        result = _fmt.shapeTrialResults(raw)
        if sex:
            result = [
                t for t in result
                if (t.get("sex") or "ALL").upper() in ("ALL", sex.upper())
            ]
            result = result[:limit]
        await trials_cache.set(key, result)
        _log.info(
            "fetched",
            extra={"tool": "trials", "condition": condition, "count": len(result)},
        )
        return result
    except Exception as e:
        _log.warning("error", extra={"tool": "trials", "error": str(e)})
        return [{"id": "", "title": f"[error: {e}]", "status": "", "phase": [], "url": ""}]
