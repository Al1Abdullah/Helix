from mcp.server.fastmcp import FastMCP
from helix.tools.trials import findTrials
from helix.tools.pubmed import searchPapers
from helix.tools.fda import lookupDrug
from helix.config import server

mcp = FastMCP(server.name)

@mcp.tool()
async def find_trials(condition: str, location: str = None, limit: int = 10) -> list[dict]:
    """
    Find active clinical trials matching a medical condition.

    Args:
        condition: Medical condition (e.g. "Type 2 Diabetes")
        location: Optional location filter (e.g. "London, UK")
        limit: Number of results, default 10
    """
    return await findTrials(condition, location, limit)

@mcp.tool()
async def search_papers(topic: str, yearFrom: int = None, yearTo: int = None, limit: int = 10) -> list[dict]:
    """
    Search PubMed for peer-reviewed research papers.

    Args:
        topic: Research topic (e.g. "Alzheimer's disease treatment")
        yearFrom: Start year filter (e.g. 2020)
        yearTo: End year filter (e.g. 2025)
        limit: Number of results, default 10
    """
    return await searchPapers(topic, yearFrom, yearTo, limit)

@mcp.tool()
async def lookup_drug(name: str, limit: int = 5) -> list[dict]:
    """
    Look up FDA drug information by brand or generic name.

    Args:
        name: Drug name (e.g. "metformin" or "Ozempic")
        limit: Number of results, default 5
    """
    return await lookupDrug(name, limit)

def run():
    mcp.run()

if __name__ == "__main__":
    run()

@mcp.tool()
async def match_eligibility(condition: str, age: int, location: str = None, limit: int = 10) -> list[dict]:
    """
    Match a patient profile to clinical trials ranked by eligibility fit.

    Args:
        condition: Medical condition (e.g. "Type 2 Diabetes")
        age: Patient age in years
        location: Optional location filter
        limit: Number of results, default 10
    """
    from helix.tools.eligibility import matchEligibility
    return await matchEligibility(condition, age, location, limit)
