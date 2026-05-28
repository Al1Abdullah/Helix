import asyncio
from helix.tools.synthesis import synthesizeEvidence

async def main():
    result = await synthesizeEvidence("Type 2 Diabetes", age=45)

    print("\nCLINICAL INSIGHT")
    print(result["clinicalInsight"])

    print("\nTRIAL PROFILES")

    for t in result["trialProfiles"]:
        print("\n---")
        print("Score:", t["score"])
        print("Risk Flags:", t["riskFlags"])
        print("Drivers:")
        for k, v in t["drivers"].items():
            print(f"  - {k}: {v}")
        print("Signals:", t["signals"])

asyncio.run(main())
