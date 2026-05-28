from helix.clients.fdaClient import FdaClient
from helix.utils.formatter import Formatter


client = FdaClient()
formatter = Formatter()


async def lookupDrug(name: str, limit: int = 5) -> list[dict]:
    """
    Look up FDA drug information by brand or generic name.
    Returns indications, warnings, manufacturer and route.
    """
    try:
        raw = client.search(name, limit)
        if "error" in raw or not raw.get("results"):
            return []
        return formatter.shapeDrugResults(raw)
    except Exception as error:
        return [{"error": str(error), "name": name}]
