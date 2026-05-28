from mcp.server.fastmcp import FastMCP
from helix.tools.trials import findTrials
from helix.tools.pubmed import searchPapers
from helix.tools.fda import lookupDrug
from helix.tools.eligibility import matchEligibility
from helix.tools.synthesis import synthesizeEvidence
from helix.config import server as server_config

mcp = FastMCP(server_config.name)


@mcp.tool()
async def find_trials(
    condition: str, location: str = None, limit: int = 10
) -> list[dict]:
    """Find active clinical trials matching a medical condition."""
    return await findTrials(condition, location, limit)


@mcp.tool()
async def search_papers(
    topic: str, yearFrom: int = None, yearTo: int = None, limit: int = 10
) -> list[dict]:
    """Search PubMed for peer-reviewed research papers."""
    return await searchPapers(topic, yearFrom, yearTo, limit)


@mcp.tool()
async def lookup_drug(name: str, limit: int = 5) -> list[dict]:
    """Look up FDA drug information by brand or generic name."""
    return await lookupDrug(name, limit)


@mcp.tool()
async def match_eligibility(
    condition: str, age: int, location: str = None, limit: int = 10
) -> list[dict]:
    """Match a patient profile to clinical trials ranked by eligibility fit."""
    return await matchEligibility(condition, age, location, limit)


@mcp.tool()
async def synthesize_evidence(
    condition: str, age: int, location: str = None
) -> dict:
    """
    Cross-database clinical evidence synthesis.

    Runs trial matching, PubMed research, and FDA drug lookup simultaneously
    and returns a single fused report with per-trial explainability vectors.

    Args:
        condition: Medical condition (e.g. "Type 2 Diabetes")
        age: Patient age in years
        location: Optional location filter (e.g. "London, UK")
    """
    return await synthesizeEvidence(condition, age, location)


def run():
    mcp.run()


if __name__ == "__main__":
    run()
