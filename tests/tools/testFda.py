import asyncio
from helix.tools.fda import lookupDrug

async def main():
    print("Looking up Metformin in FDA database...\n")
    results = await lookupDrug("metformin", limit=2)

    for drug in results:
        print(f"Brand      : {drug['brandName']}")
        print(f"Generic    : {drug['genericName']}")
        print(f"Maker      : {drug['manufacturer']}")
        print(f"Route      : {drug['route']}")
        print(f"Indications: {drug['indications'][:150]}")
        print("---")

asyncio.run(main())
