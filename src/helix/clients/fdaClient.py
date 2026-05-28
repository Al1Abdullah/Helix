import subprocess
import json
from helix.config.fda import baseUrl

class FdaClient:
    def __init__(self):
        self.userAgent = "Mozilla/5.0"

    def searchByIndication(self, condition: str, limit: int = 5):
        query = f'"{condition}"'.replace(" ", "+")
        url = (
            f"{baseUrl}/label.json"
            f"?search=indications_and_usage:{query}"
            f"&limit={limit}"
        )

        result = subprocess.run(
            ["curl", "-s", "-H", f"User-Agent: {self.userAgent}", url],
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout)
