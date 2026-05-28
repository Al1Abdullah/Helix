from helix.clients.pubmedClient import PubMedClient
from helix.utils.formatter import Formatter
from helix.cache import papers_cache
from helix.logger import get_logger

_client = PubMedClient()
_fmt    = Formatter()
_log    = get_logger(__name__)


async def searchPapers(topic: str, yearFrom: int = None, yearTo: int = None, limit: int = 10) -> list[dict]:
    """
    Search PubMed for papers. Fetches full abstracts via efetch.
    Cached 10 min. Never raises.
    """
    key = f"papers:{topic.lower().strip()}:{yearFrom}:{yearTo}:{limit}"
    cached = await papers_cache.get(key)
    if cached is not None:
        _log.info("cache_hit", extra={"tool": "pubmed", "topic": topic})
        return cached
    try:
        ids = await _client.search(topic, year_from=yearFrom, year_to=yearTo, limit=limit)
        if not ids:
            return []

        # Fetch metadata and full abstracts concurrently
        import asyncio
        summaries, abstracts = await asyncio.gather(
            _client.fetchSummaries(ids),
            _client.fetchAbstracts(ids),
        )

        result = _fmt.shapePaperResults(ids, summaries)

        # Enrich with full abstracts (efetch returns what esummary can't)
        for paper in result:
            pid = paper.get("id", "")
            if pid in abstracts:
                paper["abstract"] = abstracts[pid]

        await papers_cache.set(key, result)
        _log.info("fetched", extra={"tool": "pubmed", "topic": topic, "count": len(result), "with_abstracts": sum(1 for p in result if p.get("abstract"))})
        return result
    except Exception as e:
        _log.warning("error", extra={"tool": "pubmed", "error": str(e)})
        return [{"id": "", "title": f"[error: {e}]", "abstract": "", "authors": [], "journal": "", "year": 0, "url": ""}]
