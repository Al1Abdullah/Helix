"""ClinicalTrials.gov v2 client — curl_cffi Chrome impersonation bypasses WAF 403."""
import asyncio
from helix.config import trials as trials_config
from helix.logger import get_logger

_log = get_logger(__name__)
_FALLBACK = {"studies": []}

try:
    from curl_cffi.requests import AsyncSession as _Curl
    _USE_CURL = True
except ImportError:
    _USE_CURL = False

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
}


class TrialsClient:
    def __init__(self):
        self._base = trials_config.base_url

    async def search(self, condition: str, location: str = None, limit: int = 10) -> dict:
        params = {
            "query.cond": condition,
            "filter.overallStatus": "RECRUITING,NOT_YET_RECRUITING",
            "pageSize": min(limit, trials_config.max_limit),
            "format": "json",
        }
        if location:
            params["query.locn"] = location
        url = f"{self._base}/studies"
        last = None
        for attempt in range(3):
            try:
                if _USE_CURL:
                    async with _Curl(impersonate="chrome120") as s:
                        r = await s.get(url, params=params, headers=_HEADERS, timeout=20)
                        r.raise_for_status()
                        d = r.json()
                        return d if isinstance(d, dict) else _FALLBACK
                else:
                    import httpx
                    async with httpx.AsyncClient(timeout=20.0) as c:
                        r = await c.get(url, params=params, headers=_HEADERS)
                        r.raise_for_status()
                        d = r.json()
                        return d if isinstance(d, dict) else _FALLBACK
            except Exception as e:
                last = e
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)
        _log.warning("trials_exhausted", extra={"condition": condition, "error": str(last)})
        return _FALLBACK
