import subprocess
import json
from helix.config.trials import baseUrl

class TrialsClient:
    def __init__(self):
        self.userAgent = "Mozilla/5.0"

    async def search(self, condition: str, location: str = None, limit: int = 10):
        url = (
            f"{baseUrl}/studies"
            f"?query.cond={condition.replace(' ', '+')}"
            f"&filter.overallStatus=RECRUITING,NOT_YET_RECRUITING"
            f"&pageSize={limit}"
            f"&format=json"
        )

        if location:
            url += f"&query.locn={location.replace(' ', '+')}"

        result = subprocess.run(
            ["curl", "-s", "-H", f"User-Agent: {self.userAgent}", url],
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout)
