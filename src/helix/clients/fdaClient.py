import subprocess
import json
from helix.config import fda

class FdaClient:
    def __init__(self):
        self.userAgent = "Mozilla/5.0"

    def search(self, name: str, limit: int = 10) -> dict:
        query = name.replace(" ", "+")
        url = (
            f"{fda.baseUrl}/label.json"
            f"?search=openfda.brand_name:{query}+OR+openfda.generic_name:{query}"
            f"&limit={limit}"
        )

        result = subprocess.run(
            ["curl", "-s", "-H", f"User-Agent: {self.userAgent}", url],
            capture_output=True, text=True,
        )

        return json.loads(result.stdout)
