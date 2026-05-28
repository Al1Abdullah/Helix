import httpx
from helix.config import fda as fda_config

_SAFE_FALLBACK = {"results": [], "error": "no_data"}


class FdaClient:
    def __init__(self):
        self._base_url = fda_config.base_url
        self._headers = {"User-Agent": "Helix/1.0 (clinical trial research tool)"}

    async def search(self, name: str, limit: int = 5) -> dict:
        """Search FDA drug labels by brand or generic name."""
        query = name.replace(" ", "+")
        url = (
            f"{self._base_url}/label.json"
            f"?search=openfda.brand_name:{query}+openfda.generic_name:{query}"
            f"&limit={limit}"
        )
        return await self._get(url)

    async def searchByIndication(self, condition: str, limit: int = 5) -> dict:
        """Search FDA drug labels by indication (used in synthesis pipeline)."""
        query = f'"{condition}"'.replace(" ", "+")
        url = (
            f"{self._base_url}/label.json"
            f"?search=indications_and_usage:{query}"
            f"&limit={limit}"
        )
        return await self._get(url)

    async def _get(self, url: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, headers=self._headers)
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict):
                    return _SAFE_FALLBACK
                return data
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"results": [], "error": "not_found"}
            return {"results": [], "error": f"http_{e.response.status_code}"}
        except Exception:
            return _SAFE_FALLBACK
