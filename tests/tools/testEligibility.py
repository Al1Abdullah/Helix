import asyncio
from helix.tools.eligibility import matchEligibility

async def main():
    print("Matching 45-year-old diabetic patient to trials...\n")
    results = await matchEligibility("Type 2 Diabetes", age=45, limit=3)

    for trial in results:
        print(f"Score  : {trial['matchScore']}/100")
        print(f"ID     : {trial['id']}")
        print(f"Title  : {trial['title']}")
        print(f"Ages   : {trial['minimumAge']} — {trial['maximumAge']}")
        print(f"URL    : {trial['url']}")
        print("---")

asyncio.run(main())
