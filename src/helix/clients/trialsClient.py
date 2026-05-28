import httpx
from helix.config import trials as trials_config

_SAFE_FALLBACK = {"studies": []}


class TrialsClient:
    def __init__(self):
        self._base_url = trials_config.base_url
        self._headers = {"User-Agent": "Helix/1.0 (clinical trial research tool)"}

    async def search(
        self, condition: str, location: str = None, limit: int = 10
    ) -> dict:
        """Search ClinicalTrials.gov for recruiting trials matching a condition."""
        params = {
            "query.cond": condition,
            "filter.overallStatus": "RECRUITING,NOT_YET_RECRUITING",
            "pageSize": min(limit, trials_config.max_limit),
            "format": "json",
        }
        if location:
            params["query.locn"] = location

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    f"{self._base_url}/studies",
                    params=params,
                    headers=self._headers,
                )
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict):
                    return _SAFE_FALLBACK
                return data
        except Exception:
            return _SAFE_FALLBACK
