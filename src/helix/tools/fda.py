from helix.clients.fdaClient import FdaClient
from helix.utils.formatter import Formatter

_client = FdaClient()
_formatter = Formatter()


async def lookupDrug(name: str, limit: int = 5) -> list[dict]:
    """
    Look up FDA drug information by brand or generic name.
    Returns a list of canonical Drug dicts (never raises).
    """
    try:
        raw = await _client.search(name, limit)
        if raw.get("error") or not raw.get("results"):
            return []
        return _formatter.shapeDrugResults(raw)
    except Exception as err:
        return [{"brand_name": "", "generic_name": f"[error: {err}]", "manufacturer": "", "route": [], "indications": "", "warnings": ""}]
