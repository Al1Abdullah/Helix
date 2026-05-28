import httpx
from helix.config import pubmed as pubmed_config


class PubMedClient:
    def __init__(self):
        self._base_url = pubmed_config.base_url
        self._headers = {"User-Agent": "Helix/1.0 (clinical trial research tool)"}

    async def search(
        self,
        topic: str,
        year_from: int = None,
        year_to: int = None,
        limit: int = 10,
    ) -> list[str]:
        """Search PubMed and return a list of article IDs."""
        query = topic
        if year_from and year_to:
            query += f" AND {year_from}:{year_to}[pdat]"
        elif year_from:
            query += f" AND {year_from}:3000[pdat]"

        params = {
            "db": "pubmed",
            "term": query,
            "retmax": limit,
            "retmode": "json",
            "email": pubmed_config.email,
        }
        if pubmed_config.api_key:
            params["api_key"] = pubmed_config.api_key

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    f"{self._base_url}/esearch.fcgi",
                    params=params,
                    headers=self._headers,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("esearchresult", {}).get("idlist", [])
        except Exception:
            return []

    async def fetchSummaries(self, ids: list[str]) -> dict:
        """Fetch metadata summaries for a list of PubMed IDs."""
        if not ids:
            return {}

        params = {
            "db": "pubmed",
            "id": ",".join(ids),
            "retmode": "json",
            "email": pubmed_config.email,
        }
        if pubmed_config.api_key:
            params["api_key"] = pubmed_config.api_key

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    f"{self._base_url}/esummary.fcgi",
                    params=params,
                    headers=self._headers,
                )
                response.raise_for_status()
                return response.json()
        except Exception:
            return {}
