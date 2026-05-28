from mcp.server.fastmcp import FastMCP
from helix.tools.trials import findTrials
from helix.tools.pubmed import searchPapers
from helix.tools.fda import lookupDrug
from helix.tools.eligibility import matchEligibility
from helix.tools.synthesis import synthesizeEvidence
from helix.tools.health import checkHealth
from helix.config import server as server_config

mcp = FastMCP(server_config.name)


@mcp.tool()
async def find_trials(condition: str, location: str = None, limit: int = 10) -> list[dict]:
    """Find active clinical trials matching a medical condition.
    Abbreviations like T2D, NSCLC, COPD are automatically expanded.

    Args:
        condition: Medical condition or abbreviation (e.g. "T2D", "Type 2 Diabetes").
        location: Optional location filter (e.g. "Boston, MA").
        limit: Max results (default 10).
    """
    return await findTrials(condition, location, limit)


@mcp.tool()
async def search_papers(topic: str, yearFrom: int = None, yearTo: int = None, limit: int = 10) -> list[dict]:
    """Search PubMed for peer-reviewed research papers.
    Abbreviations like T2D, NSCLC, COPD are automatically expanded.

    Args:
        topic: Research topic or abbreviation.
        yearFrom: Start year filter (optional).
        yearTo: End year filter (optional).
        limit: Max results (default 10).
    """
    return await searchPapers(topic, yearFrom, yearTo, limit)


@mcp.tool()
async def lookup_drug(name: str, limit: int = 5) -> list[dict]:
    """Look up FDA drug information by brand or generic name."""
    return await lookupDrug(name, limit)


@mcp.tool()
async def match_eligibility(
    condition: str,
    age: int,
    location: str = None,
    limit: int = 10,
    sex: str = None,
) -> list[dict]:
    """Match a patient profile to clinical trials ranked by eligibility fit.
    Abbreviations like T2D, NSCLC, COPD are automatically expanded.

    Args:
        condition: Medical condition or abbreviation (e.g. "T2D", "NSCLC").
        age: Patient age in years.
        location: Optional location filter (e.g. "Boston, MA").
        limit: Max results (default 10).
        sex: Optional patient sex filter: MALE or FEMALE.
    """
    return await matchEligibility(condition, age, location, limit, sex)


@mcp.tool()
async def synthesize_evidence(
    condition: str,
    age: int,
    location: str = None,
    sex: str = None,
) -> dict:
    """Cross-database clinical evidence synthesis.
    Queries ClinicalTrials.gov, PubMed, and openFDA concurrently.
    Returns scored, ranked trials with full explainability vectors.
    Abbreviations like T2D, NSCLC, COPD are automatically expanded.
    Response includes expanded_from when an abbreviation was resolved.

    Args:
        condition: Medical condition or abbreviation (e.g. "T2D", "NSCLC").
        age: Patient age in years.
        location: Optional location filter (e.g. "London, UK").
        sex: Optional patient sex filter: MALE or FEMALE.
    """
    return await synthesizeEvidence(condition, age, location, sex)


@mcp.tool()
async def health_check() -> dict:
    """Check live connectivity and latency to all 3 external APIs."""
    return await checkHealth()


def run():
    mcp.run()


if __name__ == "__main__":
    run()
