"""Health smoke test. Run: python tests/tools/testHealth.py"""
import asyncio
from helix.tools.health import checkHealth


async def main():
    print("Pinging all 3 external APIs...\n")
    r = await checkHealth()
    print(f"Overall : {r.get('status','?').upper()}")
    print(f"Version : {r.get('version','?')}")
    print(f"Time    : {r.get('timestamp','?')}\n")
    for svc, info in (r.get("services") or {}).items():
        if not isinstance(info, dict):
            continue
        s = info.get("status","?")
        icon = "✓" if s == "ok" else ("⚠" if s == "degraded" else "✗")
        line = f"  {icon}  {svc:<28} {s:<10} {info.get('latency_ms','?')} ms"
        if info.get("error"):
            line += f"  [{info['error']}]"
        print(line)
    print()

asyncio.run(main())
