from helix.clients.fdaClient import FdaClient
from helix.utils.formatter import Formatter
from helix.cache import drugs_cache
from helix.logger import get_logger

_client = FdaClient()
_fmt    = Formatter()
_log    = get_logger(__name__)


async def lookupDrug(name: str, limit: int = 5) -> list[dict]:
    """Look up FDA drug info. Cached 1 hr. Never raises."""
    key = f"drugs:{name.lower().strip()}:{limit}"
    cached = await drugs_cache.get(key)
    if cached is not None:
        _log.info("cache_hit", extra={"tool": "fda", "drug_name": name})
        return cached
    try:
        raw = await _client.search(name, limit)
        if raw.get("error") or not raw.get("results"):
            return []
        result = _fmt.shapeDrugResults(raw)
        await drugs_cache.set(key, result)
        _log.info("fetched", extra={"tool": "fda", "drug_name": name, "count": len(result)})
        return result
    except Exception as e:
        _log.warning("error", extra={"tool": "fda", "error": str(e)})
        return [{"brand_name": "", "generic_name": f"[error: {e}]", "manufacturer": "", "route": [], "indications": "", "warnings": ""}]
