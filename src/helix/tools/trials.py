from helix.clients.trialsClient import TrialsClient
from helix.utils.formatter import Formatter


client = TrialsClient()
formatter = Formatter()


async def findTrials(
    condition: str, location: str = None, limit: int = 10
) -> list[dict]:
    """
    Find active clinical trials for a condition.
    Returns structured trial data any AI model can reason about.
    """
    try:
        raw = await client.search(condition, location, limit)
        return formatter.shapeTrialResults(raw)
    except Exception as error:
        return [{"error": str(error), "condition": condition}]
