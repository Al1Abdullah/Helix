"""NCBI PubMed E-utilities client — esearch + esummary + efetch for full abstracts."""
import asyncio
import xml.etree.ElementTree as ET
import httpx
from helix.config import pubmed as pubmed_config
from helix.logger import get_logger

_log = get_logger(__name__)
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


class PubMedClient:
    def __init__(self):
        self._base = pubmed_config.base_url

    def _params(self) -> dict:
        p = {"email": pubmed_config.email}
        if pubmed_config.api_key:
            p["api_key"] = pubmed_config.api_key
        return p

    async def search(self, topic: str, year_from: int = None, year_to: int = None, limit: int = 10) -> list[str]:
        """Search PubMed and return list of article IDs."""
        q = topic
        if year_from and year_to:
            q += f" AND {year_from}:{year_to}[pdat]"
        elif year_from:
            q += f" AND {year_from}:3000[pdat]"
        params = {**self._params(), "db": "pubmed", "term": q, "retmax": limit, "retmode": "json"}
        last = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=20.0) as c:
                    r = await c.get(f"{self._base}/esearch.fcgi", params=params, headers=_HEADERS)
                    r.raise_for_status()
                    return r.json().get("esearchresult", {}).get("idlist", [])
            except Exception as e:
                last = e
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
        _log.warning("pubmed_search_exhausted", extra={"topic": topic, "error": str(last)})
        return []

    async def fetchSummaries(self, ids: list[str]) -> dict:
        """Fetch metadata (title, authors, journal, year) for a list of PMIDs."""
        if not ids:
            return {}
        params = {**self._params(), "db": "pubmed", "id": ",".join(ids), "retmode": "json"}
        last = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=20.0) as c:
                    r = await c.get(f"{self._base}/esummary.fcgi", params=params, headers=_HEADERS)
                    r.raise_for_status()
                    return r.json()
            except Exception as e:
                last = e
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
        _log.warning("pubmed_fetch_exhausted", extra={"ids": len(ids), "error": str(last)})
        return {}

    async def fetchAbstracts(self, ids: list[str]) -> dict[str, str]:
        """
        Fetch full abstract text via efetch (XML).
        Returns {pmid: abstract_text}. Uses stdlib xml.etree — no extra deps.
        Structured abstracts (with section labels) are joined with spaces.
        Capped at 800 chars to stay token-efficient.
        """
        if not ids:
            return {}
        params = {
            **self._params(),
            "db": "pubmed",
            "id": ",".join(ids),
            "rettype": "abstract",
            "retmode": "xml",
        }
        last = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=30.0) as c:
                    r = await c.get(f"{self._base}/efetch.fcgi", params=params, headers=_HEADERS)
                    r.raise_for_status()
                    root = ET.fromstring(r.text)
                    result: dict[str, str] = {}
                    for article in root.iter("PubmedArticle"):
                        pmid_el = article.find(".//PMID")
                        if pmid_el is None or not pmid_el.text:
                            continue
                        pmid = pmid_el.text.strip()
                        parts = []
                        for el in article.iter("AbstractText"):
                            label = el.get("Label", "")
                            text = (el.text or "").strip()
                            if label and text:
                                parts.append(f"{label}: {text}")
                            elif text:
                                parts.append(text)
                        if parts:
                            result[pmid] = " ".join(parts)[:800]
                    return result
            except Exception as e:
                last = e
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
        _log.warning("pubmed_abstracts_exhausted", extra={"ids": len(ids), "error": str(last)})
        return {}
