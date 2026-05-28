import asyncio
from helix.tools.trials import findTrials

async def main():
    print("Searching for diabetes trials...\n")
    results = await findTrials("Type 2 Diabetes", limit=3)

    for trial in results:
        print(f"ID     : {trial['id']}")
        print(f"Title  : {trial['title']}")
        print(f"Status : {trial['status']}")
        print(f"URL    : {trial['url']}")
        print("---")

asyncio.run(main())
