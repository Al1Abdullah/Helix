from mcp.server.fastmcp import FastMCP
from helix.tools.trials import findTrials
from helix.config import server

mcp = FastMCP(server.name)

@mcp.tool()
async def find_trials(condition: str, location: str = None, limit: int = 10) -> list[dict]:
    """
    Find active clinical trials matching a medical condition.

    Args:
        condition: Medical condition to search for (e.g. "Type 2 Diabetes")
        location: Optional location filter (e.g. "London, UK")
        limit: Number of results to return (default 10, max 50)
    """
    return await findTrials(condition, location, limit)

def run():
    mcp.run()

if __name__ == "__main__":
    run()
