from helix.clients.pubmedClient import PubMedClient
from helix.utils.formatter import Formatter

_client = PubMedClient()
_formatter = Formatter()


async def searchPapers(
    topic: str,
    yearFrom: int = None,
    yearTo: int = None,
    limit: int = 10,
) -> list[dict]:
    """
    Search PubMed for research papers on a topic.
    Returns a list of canonical Paper dicts (never raises).
    """
    try:
        ids = await _client.search(topic, year_from=yearFrom, year_to=yearTo, limit=limit)
        if not ids:
            return []
        summaries = await _client.fetchSummaries(ids)
        return _formatter.shapePaperResults(ids, summaries)
    except Exception as err:
        return [{"id": "", "title": f"[search error: {err}]", "abstract": "", "authors": [], "journal": "", "year": 0, "url": ""}]
