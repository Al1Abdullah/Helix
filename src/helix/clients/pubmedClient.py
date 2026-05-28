import httpx
from helix.config import pubmed

class PubMedClient:
    def __init__(self):
        self.headers = {"User-Agent": "Mozilla/5.0"}

    def search(self, topic: str, yearFrom: int = None, yearTo: int = None, limit: int = 10) -> list[str]:
        query = topic
        if yearFrom and yearTo:
            query += f" AND {yearFrom}:{yearTo}[pdat]"

        params = {
            "db": "pubmed",
            "term": query,
            "retmax": limit,
            "retmode": "json",
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{pubmed.baseUrl}/esearch.fcgi",
                params=params,
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()["esearchresult"]["idlist"]

    def fetchSummaries(self, ids: list[str]) -> dict:
        params = {
            "db": "pubmed",
            "id": ",".join(ids),
            "retmode": "json",
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{pubmed.baseUrl}/esummary.fcgi",
                params=params,
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()
