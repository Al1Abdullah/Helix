"""
Helix synthesis pipeline smoke test.
Tests against live APIs. Run from repo root:
    python tests/tools/testSynthesis.py
"""

import asyncio
import json
from helix.tools.synthesis import synthesizeEvidence


def _safe_get(d: dict, *keys, default="N/A"):
    """Safely traverse nested dict keys without raising."""
    cur = d
    for key in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key, default)
        if cur is default:
            return default
    return cur


def print_divider(label: str = ""):
    width = 60
    if label:
        pad = (width - len(label) - 2) // 2
        print(f"\n{'─' * pad} {label} {'─' * pad}")
    else:
        print("─" * width)


async def main():
    condition = "Type 2 Diabetes"
    age = 45

    print_divider("HELIX SYNTHESIS REPORT")
    print(f"  Condition : {condition}")
    print(f"  Patient Age: {age}")
    print_divider()

    result = await synthesizeEvidence(condition, age=age)

    # ── Clinical Insight ──────────────────────────────────────
    print_divider("CLINICAL INSIGHT")
    insight = result.get("clinicalInsight") or {}
    print(f"  Condition     : {_safe_get(insight, 'condition')}")
    print(f"  Total Trials  : {_safe_get(insight, 'total_trials')}")
    print(f"  Top Score     : {_safe_get(insight, 'top_score')}")
    print(f"  Average Score : {_safe_get(insight, 'average_score')}")

    # ── Trial Profiles ────────────────────────────────────────
    profiles = result.get("trialProfiles") or []
    print_divider(f"TRIAL PROFILES ({len(profiles)} scored)")

    for i, profile in enumerate(profiles, start=1):
        if not isinstance(profile, dict):
            print(f"  [profile {i}] malformed entry — skipping")
            continue

        print(f"\n  ── Trial {i} ──")
        print(f"  ID          : {profile.get('id', 'N/A')}")
        print(f"  Title       : {(profile.get('title') or 'N/A')[:80]}")
        print(f"  Phase       : {profile.get('phase', [])}")
        print(f"  Final Score : {profile.get('final_score', 'N/A')}")

        sv = profile.get("score_vector") or {}
        print("  Score Vector:")
        for k, v in sv.items():
            print(f"    {k:<25} {v}")

        ev = profile.get("explainability_vector") or {}
        print("  Explainability Vector:")
        for k, v in ev.items():
            print(f"    {k:<25} {v}")

        flags = profile.get("risk_flags") or []
        print(f"  Risk Flags  : {flags if flags else 'none'}")
        print(f"  URL         : {profile.get('url', '')}")

    # ── Excluded Trials ───────────────────────────────────────
    excluded = result.get("excludedTrials") or []
    print_divider(f"EXCLUDED TRIALS ({len(excluded)} rejected)")
    if excluded:
        for ex in excluded:
            if not isinstance(ex, dict):
                continue
            print(f"  [{ex.get('id', '?')}] {(ex.get('title') or '')[:60]} — {ex.get('exclusion_reason', '')}")
    else:
        print("  (none excluded)")

    print_divider("END OF REPORT")
    print()


if __name__ == "__main__":
    asyncio.run(main())
