import httpx
from helix.config import fda

class FdaClient:
    def __init__(self):
        self.headers = {"User-Agent": "Mozilla/5.0"}

    def search(self, name: str, limit: int = 10) -> dict:
        params = {
            "search": f"openfda.brand_name:{name} OR openfda.generic_name:{name}",
            "limit": limit,
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{fda.baseUrl}/label.json",
                params=params,
                headers=self.headers,
            )
            if response.status_code == 404:
                return {"results": []}
            response.raise_for_status()
            return response.json()
