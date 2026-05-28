"""openFDA drug label client — retry with exponential backoff, 4xx short-circuit."""
import asyncio
import httpx
from helix.config import fda as fda_config
from helix.logger import get_logger

_log = get_logger(__name__)
_FALLBACK = {"results": [], "error": "no_data"}
_NO_RETRY = {400, 401, 403, 404, 422}
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, if Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


class FdaClient:
    def __init__(self):
        self._base = fda_config.base_url

    async def search(self, name: str, limit: int = 5) -> dict:
        q = name.replace(" ", "+")
        url = f"{self._base}/label.json?search=openfda.brand_name:{q}+openfda.generic_name:{q}&limit={limit}"
        return await self._get(url, f"drug:{name}")

    async def searchByIndication(self, condition: str, limit: int = 5) -> dict:
        q = f'"{condition}"'.replace(" ", "+")
        url = f"{self._base}/label.json?search=indications_and_usage:{q}&limit={limit}"
        return await self._get(url, f"indication:{condition}")

    async def _get(self, url: str, ctx: str = "") -> dict:
        last = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=15.0) as c:
                    r = await c.get(url, headers=_HEADERS)
                    r.raise_for_status()
                    d = r.json()
                    return d if isinstance(d, dict) else _FALLBACK
            except httpx.HTTPStatusError as e:
                if e.response.status_code in _NO_RETRY:
                    return {"results": [], "error": f"http_{e.response.status_code}"}
                last = e
            except Exception as e:
                last = e
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)
        _log.warning("fda_exhausted", extra={"ctx": ctx, "error": str(last)})
        return _FALLBACK
