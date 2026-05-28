import asyncio
from helix.tools.eligibility import matchEligibility


async def main():
    print("Matching 45-year-old diabetic patient to trials...\n")
    results = await matchEligibility("Type 2 Diabetes", age=45, limit=3)

    for trial in (results or []):
        print(f"Legacy Score : {trial.get('match_score_legacy', 'N/A')}/100")
        print(f"ID           : {trial.get('id', 'N/A')}")
        print(f"Title        : {trial.get('title', 'N/A')}")
        print(f"Age Range    : {trial.get('min_age_raw', '?')} — {trial.get('max_age_raw', '?')}")
        print(f"URL          : {trial.get('url', '')}")
        print("---")


asyncio.run(main())
