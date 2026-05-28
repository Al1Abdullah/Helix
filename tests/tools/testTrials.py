import asyncio
from helix.tools.trials import findTrials


async def main():
    print("Searching for diabetes trials...\n")
    results = await findTrials("Type 2 Diabetes", limit=3)

    for trial in (results or []):
        print(f"ID     : {trial.get('id', 'N/A')}")
        print(f"Title  : {trial.get('title', 'N/A')}")
        print(f"Status : {trial.get('status', 'N/A')}")
        print(f"Phase  : {trial.get('phase', [])}")
        print(f"URL    : {trial.get('url', '')}")
        print("---")


asyncio.run(main())
