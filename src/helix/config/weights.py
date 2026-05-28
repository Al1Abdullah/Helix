WEIGHTS = {
    "condition_match": 0.35,
    "eligibility_fit": 0.30,
    "evidence_support": 0.20,
    "trial_phase_maturity": 0.15,
}

# Sanity check — weights must sum to 1.0
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, "WEIGHTS must sum to 1.0"
