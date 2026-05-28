import subprocess
import json
from helix.config import pubmed

class PubMedClient:
    def __init__(self):
        self.userAgent = "Mozilla/5.0"

    def search(self, topic: str, yearFrom: int = None, yearTo: int = None, limit: int = 10) -> list[str]:
        query = topic.replace(" ", "+")
        if yearFrom and yearTo:
            query += f"+AND+{yearFrom}:{yearTo}[pdat]"

        url = (
            f"{pubmed.baseUrl}/esearch.fcgi"
            f"?db=pubmed&term={query}&retmax={limit}&retmode=json"
        )

        result = subprocess.run(
            ["curl", "-s", "-H", f"User-Agent: {self.userAgent}", url],
            capture_output=True, text=True,
        )

        data = json.loads(result.stdout)
        return data["esearchresult"]["idlist"]

    def fetchSummaries(self, ids: list[str]) -> dict:
        idString = ",".join(ids)
        url = (
            f"{pubmed.baseUrl}/esummary.fcgi"
            f"?db=pubmed&id={idString}&retmode=json"
        )

        result = subprocess.run(
            ["curl", "-s", "-H", f"User-Agent: {self.userAgent}", url],
            capture_output=True, text=True,
        )

        return json.loads(result.stdout)
