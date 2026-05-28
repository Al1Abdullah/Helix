from helix.clients.pubmedClient import PubMedClient
from helix.utils.formatter import Formatter


client = PubMedClient()
formatter = Formatter()


async def searchPapers(
    topic: str, yearFrom: int = None, yearTo: int = None, limit: int = 10
) -> list[dict]:
    """
    Search PubMed for research papers on a topic.
    Returns structured paper data any AI model can reason about.
    """
    try:
        ids = client.search(topic, yearFrom, yearTo, limit)
        if not ids:
            return []
        summaries = client.fetchSummaries(ids)
        return formatter.shapePaperResults(ids, summaries)
    except Exception as error:
        return [{"error": str(error), "topic": topic}]
