import asyncio
from helix.tools.fda import lookupDrug


async def main():
    print("Looking up Metformin in FDA database...\n")
    results = await lookupDrug("metformin", limit=2)

    for drug in (results or []):
        print(f"Brand      : {drug.get('brand_name', 'N/A')}")
        print(f"Generic    : {drug.get('generic_name', 'N/A')}")
        print(f"Maker      : {drug.get('manufacturer', 'N/A')}")
        print(f"Route      : {drug.get('route', [])}")
        print(f"Indications: {(drug.get('indications') or '')[:150]}")
        print("---")


asyncio.run(main())
