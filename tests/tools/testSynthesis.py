import asyncio
from helix.tools.synthesis import synthesizeEvidence

async def main():
    result = await synthesizeEvidence("Type 2 Diabetes", age=45)

    print("\nCLINICAL INSIGHT")
    print(result["clinicalInsight"])

    print("\nTRIAL PROFILES\n")

    for t in result["trialProfiles"]:
        print("---")
        print("Score:", t["eligibilityScore"])
        print("Why matched:", " | ".join(
            f"{k}:{v}" for k, v in t["drivers"].items()
        ))
        print("Risk Flags:", t["riskFlags"])

asyncio.run(main())
