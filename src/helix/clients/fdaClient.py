import subprocess
import json
from helix.config import fda


class FdaClient:
    def __init__(self):
        self.userAgent = "Mozilla/5.0"

    def search(self, name: str, limit: int = 10) -> list[dict]:
        query = name.replace(" ", "+")
        url = (
            f"{fda.baseUrl}/label.json"
            f"?search=openfda.brand_name:{query}+OR+openfda.generic_name:{query}"
            f"&limit={limit}"
        )

        result = subprocess.run(
            ["curl", "-s", "-H", f"User-Agent: {self.userAgent}", url],
            capture_output=True,
            text=True,
        )

        data = json.loads(result.stdout)
        return data.get("results", [])

    def searchByIndication(self, condition: str, limit: int = 5) -> list[dict]:
        query = f'"{condition}"'.replace(" ", "+")
        url = (
            f"{fda.baseUrl}/label.json"
            f"?search=indications_and_usage:{query}"
            f"&limit={limit}"
        )

        result = subprocess.run(
            ["curl", "-s", "-H", f"User-Agent: {self.userAgent}", url],
            capture_output=True,
            text=True,
        )

        data = json.loads(result.stdout)
        return data.get("results", [])
