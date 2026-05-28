import httpx
from helix.config import trials

class TrialsClient:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        }

    async def search(self, condition: str, location: str = None, limit: int = 10) -> dict:
        params = {
            "query.cond": condition,
            "pageSize": limit,
            "format": "json",
        }
        if location:
            params["query.locn"] = location

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{trials.baseUrl}/studies",
                params=params,
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()
