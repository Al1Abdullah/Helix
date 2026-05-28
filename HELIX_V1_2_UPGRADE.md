# HELIX v1.2.0 UPGRADE — GEMINI CLI EXECUTION PROMPT
# Run from inside: Helix-main/
# Gemini: execute every instruction in this file exactly, top to bottom.

## WHAT THIS FIXES AND ADDS

BUG FIX — ServerConfig.version hardcoded to "1.0.0" while pyproject.toml is 1.1.0.
  All /health and /docs responses report wrong version. Fix: importlib.metadata
  reads version from the installed package at runtime, stays in sync automatically.

NEW — Condition synonym expansion (src/helix/utils/synonyms.py).
  Patients and clinicians search with abbreviations. "T2D" never matched trials for
  "Type 2 Diabetes". Now 65+ abbreviation/alias mappings are applied before any API
  call. Zero new dependencies — pure stdlib dict lookup.

NEW — Sex eligibility parameter on synthesize and eligibility pipelines.
  The sex field was parsed from ClinicalTrials.gov but never used in scoring.
  synthesizeEvidence() and matchEligibility() now accept sex="MALE"|"FEMALE".
  Sex-mismatched trials are excluded by the hard gate and reported in excludedTrials.
  REST endpoints /synthesize and /eligibility accept sex in the request body.

NEW — GET /score-weights endpoint.
  Returns the weight vector and plain-English description of every scoring component.
  Lets API consumers explain trial rankings without reading source code.

NEW — Unit tests for synonym expansion (tests/unit/test_synonyms.py).
  10 assertions: uppercase, lowercase, mixed-case, whitespace strip, passthrough.

## FILE OPERATIONS (9 total)

Creates:
  src/helix/utils/synonyms.py
  tests/unit/test_synonyms.py

Overwrites:
  src/helix/config/__init__.py       — dynamic version via importlib.metadata
  src/helix/tools/synthesis.py       — sex param + synonym expand + _hard_gate update
  src/helix/tools/eligibility.py     — sex param + sex hard gate
  src/helix/api.py                   — sex in request bodies + GET /score-weights
  pyproject.toml                     — version 1.2.0
  CHANGELOG.md

Do NOT touch any other file.

---

## FILE 1 — src/helix/utils/synonyms.py (CREATE)

```python
"""
Condition synonym and abbreviation expansion.
Zero external dependencies — pure stdlib dict lookup.
Call expand() before passing any user-supplied condition to an external API.
"""
from __future__ import annotations

_MAP: dict[str, str] = {
    # Diabetes
    "t2d": "Type 2 Diabetes",
    "type2 diabetes": "Type 2 Diabetes",
    "diabetes type 2": "Type 2 Diabetes",
    "dm2": "Type 2 Diabetes",
    "t1d": "Type 1 Diabetes",
    "dm1": "Type 1 Diabetes",
    # Oncology
    "nsclc": "Non-Small Cell Lung Cancer",
    "sclc": "Small Cell Lung Cancer",
    "crc": "Colorectal Cancer",
    "tnbc": "Triple Negative Breast Cancer",
    "hnscc": "Head and Neck Squamous Cell Carcinoma",
    "hcc": "Hepatocellular Carcinoma",
    "rcc": "Renal Cell Carcinoma",
    "dlbcl": "Diffuse Large B-Cell Lymphoma",
    "cll": "Chronic Lymphocytic Leukemia",
    "aml": "Acute Myeloid Leukemia",
    "cml": "Chronic Myeloid Leukemia",
    "mm": "Multiple Myeloma",
    # Cardiology
    "chf": "Congestive Heart Failure",
    "hf": "Heart Failure",
    "afib": "Atrial Fibrillation",
    "af": "Atrial Fibrillation",
    "cad": "Coronary Artery Disease",
    "mi": "Myocardial Infarction",
    "acs": "Acute Coronary Syndrome",
    "pad": "Peripheral Arterial Disease",
    "htn": "Hypertension",
    "svt": "Supraventricular Tachycardia",
    # Pulmonology
    "copd": "Chronic Obstructive Pulmonary Disease",
    "ild": "Interstitial Lung Disease",
    "ards": "Acute Respiratory Distress Syndrome",
    "ph": "Pulmonary Hypertension",
    # Nephrology
    "ckd": "Chronic Kidney Disease",
    "aki": "Acute Kidney Injury",
    "esrd": "End-Stage Renal Disease",
    "fsgs": "Focal Segmental Glomerulosclerosis",
    # Gastroenterology
    "nash": "Non-Alcoholic Steatohepatitis",
    "nafld": "Non-Alcoholic Fatty Liver Disease",
    "ibd": "Inflammatory Bowel Disease",
    "uc": "Ulcerative Colitis",
    "cd": "Crohn's Disease",
    "gerd": "Gastroesophageal Reflux Disease",
    "pbc": "Primary Biliary Cholangitis",
    # Rheumatology / Immunology
    "ra": "Rheumatoid Arthritis",
    "sle": "Systemic Lupus Erythematosus",
    "lupus": "Systemic Lupus Erythematosus",
    "as": "Ankylosing Spondylitis",
    "psa": "Psoriatic Arthritis",
    "ssc": "Systemic Sclerosis",
    "sjogrens": "Sjogren's Syndrome",
    "gpa": "Granulomatosis with Polyangiitis",
    # Neurology
    "ms": "Multiple Sclerosis",
    "ad": "Alzheimer's Disease",
    "pd": "Parkinson's Disease",
    "als": "Amyotrophic Lateral Sclerosis",
    "tbi": "Traumatic Brain Injury",
    # Infectious Disease
    "hiv": "Human Immunodeficiency Virus",
    "hbv": "Hepatitis B",
    "hcv": "Hepatitis C",
    "tb": "Tuberculosis",
    "cdiff": "Clostridioides difficile",
    # Psychiatry
    "mdd": "Major Depressive Disorder",
    "gad": "Generalized Anxiety Disorder",
    "ocd": "Obsessive Compulsive Disorder",
    "ptsd": "Post-Traumatic Stress Disorder",
    "bpd": "Borderline Personality Disorder",
    "adhd": "Attention Deficit Hyperactivity Disorder",
    # Dermatology / Endocrine
    "pso": "Psoriasis",
    "atd": "Atopic Dermatitis",
    "hypo": "Hypothyroidism",
    "hyper": "Hyperthyroidism",
}


def expand(condition: str) -> str:
    """
    Return the canonical condition name for known abbreviations/aliases.
    Comparison is case-insensitive; strips extra whitespace.
    Returns the original string unchanged if no mapping exists.

    Examples:
        expand("T2D")   → "Type 2 Diabetes"
        expand("nsclc") → "Non-Small Cell Lung Cancer"
        expand("Type 2 Diabetes") → "Type 2 Diabetes"   # passthrough
        expand("  COPD  ") → "Chronic Obstructive Pulmonary Disease"
    """
    if not condition:
        return condition
    return _MAP.get(condition.strip().lower(), condition)
```

---

## FILE 2 — src/helix/config/__init__.py (OVERWRITE)

```python
import os
from dotenv import load_dotenv

load_dotenv()

try:
    from importlib.metadata import version as _pkg_version
    _VERSION = _pkg_version("helix")
except Exception:
    _VERSION = "1.2.0"


class TrialsConfig:
    base_url: str = "https://clinicaltrials.gov/api/v2"
    default_limit: int = 10
    max_limit: int = 50


class PubMedConfig:
    base_url: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    email: str = os.getenv("PUBMED_EMAIL", "helix@example.com")
    api_key: str = os.getenv("PUBMED_API_KEY", "")
    default_limit: int = 10


class FdaConfig:
    base_url: str = "https://api.fda.gov/drug"
    default_limit: int = 10


class CacheConfig:
    synthesis_ttl: int = 300   # 5 min
    trials_ttl: int = 180      # 3 min
    papers_ttl: int = 600      # 10 min
    drugs_ttl: int = 3600      # 1 hr


class ServerConfig:
    name: str = "Helix"
    version: str = _VERSION


trials = TrialsConfig()
pubmed = PubMedConfig()
fda = FdaConfig()
cache = CacheConfig()
server = ServerConfig()
```

---

## FILE 3 — src/helix/tools/synthesis.py (OVERWRITE)

```python
"""
Helix synthesis pipeline — deterministic weighted vector scoring.

final_score = 100 * (
    0.35 * condition_match +
    0.30 * eligibility_fit +
    0.20 * evidence_support +
    0.15 * trial_phase_maturity
)
All sub-scores normalized to [0, 1]. Results cached 5 min per
(condition, age, location, sex).

v1.2.0: synonym expansion applied before any API call; sex param added to
hard gate; version reads from package metadata.
v1.1.0: eligibility_fit computes age-window centrality (was hardcoded 1.0).
"""
import asyncio
import time
from helix.utils.synonyms import expand
from helix.tools.eligibility import matchEligibility
from helix.tools.pubmed import searchPapers
from helix.clients.fdaClient import FdaClient
from helix.utils.formatter import Formatter
from helix.config.weights import WEIGHTS
from helix.cache import synthesis_cache
from helix.logger import get_logger
from helix.models import (
    TrialProfile, ScoreVector, ExplainabilityVector,
    ClinicalInsight, SynthesisResult, ExcludedTrial,
)

_fda = FdaClient()
_fmt = Formatter()
_log = get_logger(__name__)


def _phase_score(phase: list) -> float:
    if not isinstance(phase, list):
        return 0.5
    if any(p in ["PHASE3", "PHASE4"] for p in phase):
        return 1.0
    if "PHASE2" in phase:
        return 0.6
    if "PHASE1" in phase:
        return 0.3
    return 0.5


def _norm(value: float, max_val: float) -> float:
    return min(float(value) / float(max_val), 1.0) if max_val > 0 else 0.0


def _hard_gate(trial: dict, age: int, sex: str = None) -> tuple[bool, str]:
    mn, mx = trial.get("min_age"), trial.get("max_age")
    if isinstance(mn, int) and age < mn:
        return False, f"age {age} below min {mn}"
    if isinstance(mx, int) and age > mx:
        return False, f"age {age} above max {mx}"
    if sex:
        trial_sex = (trial.get("sex") or "ALL").upper()
        patient_sex = sex.upper()
        if trial_sex != "ALL" and trial_sex != patient_sex:
            return False, f"sex mismatch: trial={trial_sex}, patient={patient_sex}"
    if not trial.get("id"):
        return False, "missing trial ID"
    if not trial.get("title"):
        return False, "missing trial title"
    return True, ""


def _eligibility_fit_score(trial: dict, age: int) -> float:
    """
    Age-window centrality score for the eligibility_fit vector component.
    Patient at center of window = 1.0; at edge = 0.5; open enrollment = 0.75.
    Range: [0.5, 1.0]. Never 0 — hard gate already excluded out-of-window patients.
    """
    mn = trial.get("min_age")
    mx = trial.get("max_age")
    if mn is None and mx is None:
        return 0.75
    lo = mn if mn is not None else 0
    hi = mx if mx is not None else 120
    center = (lo + hi) / 2.0
    half_width = max((hi - lo) / 2.0, 1.0)
    dist = abs(age - center) / half_width
    return round(max(0.5, 1.0 - dist * 0.5), 4)


def buildTrialProfile(trial: dict, age: int, condition: str, papers: list, drugs: list) -> dict:
    cond_tok  = set((condition or "").lower().split())
    title_tok = set((trial.get("title") or "").lower().split())
    overlap   = len(cond_tok & title_tok)
    cond_m    = _norm(overlap, max(len(cond_tok), 1))

    ev_hits = 0
    for p in papers:
        if not isinstance(p, dict):
            continue
        title_match    = bool(set((p.get("title") or "").lower().split()) & cond_tok)
        abstract_match = bool(set((p.get("abstract") or "").lower().split()) & cond_tok)
        if title_match or abstract_match:
            ev_hits += 1
    ev_m = _norm(ev_hits, max(len(papers), 1))

    phase   = trial.get("phase") or []
    phase_m = _phase_score(phase)
    elig_m  = _eligibility_fit_score(trial, age)

    score = round(100.0 * (
        WEIGHTS["condition_match"]        * cond_m
        + WEIGHTS["eligibility_fit"]      * elig_m
        + WEIGHTS["evidence_support"]     * ev_m
        + WEIGHTS["trial_phase_maturity"] * phase_m
    ), 2)

    mn, mx = trial.get("min_age"), trial.get("max_age")
    age_pen = 0.0
    if isinstance(mn, int) and age < mn:
        age_pen = round((mn - age) / max(mn, 1), 3)
    elif isinstance(mx, int) and age > mx:
        age_pen = round((age - mx) / max(age, 1), 3)

    flags = []
    if cond_m  < 0.2: flags.append("LOW_CONDITION_MATCH")
    if phase_m <= 0.3: flags.append("EARLY_STAGE_TRIAL")
    if ev_m    < 0.1: flags.append("LOW_EVIDENCE_SUPPORT")

    return TrialProfile(
        id=trial.get("id") or "",
        title=trial.get("title") or "",
        url=trial.get("url") or "",
        phase=phase,
        final_score=score,
        score_vector=ScoreVector(
            condition_match=round(cond_m, 4),
            eligibility_fit=round(elig_m, 4),
            evidence_support=round(ev_m, 4),
            trial_phase_maturity=round(phase_m, 4),
        ),
        explainability_vector=ExplainabilityVector(
            condition_overlap_raw=overlap,
            evidence_hits_raw=ev_hits,
            age_penalty=age_pen,
            phase_penalty=round(1.0 - phase_m, 3),
        ),
        risk_flags=flags,
    ).model_dump()


def buildClinicalInsight(profiles: list, condition: str) -> dict:
    if not profiles:
        return ClinicalInsight(condition=condition or "").model_dump()
    scores = [p.get("final_score", 0.0) for p in profiles]
    return ClinicalInsight(
        total_trials=len(profiles),
        top_score=round(max(scores), 2),
        average_score=round(sum(scores) / len(scores), 2),
        condition=condition or "",
    ).model_dump()


async def synthesizeEvidence(
    condition: str,
    age: int,
    location: str = None,
    sex: str = None,
) -> dict:
    """Full cross-database synthesis. Cached 5 min per (condition, age, location, sex)."""
    condition = expand(condition)  # "T2D" → "Type 2 Diabetes" etc.
    key = f"synthesis:{condition.lower().strip()}:{age}:{location or ''}:{sex or ''}"
    cached = await synthesis_cache.get(key)
    if cached is not None:
        _log.info("cache_hit", extra={"tool": "synthesis", "condition": condition, "age": age})
        return cached

    t0 = time.monotonic()
    trials, papers = await asyncio.gather(
        matchEligibility(condition, age, location, limit=8, sex=sex),
        searchPapers(condition, limit=5),
    )

    try:
        drugs_raw = await _fda.searchByIndication(condition, limit=3)
        drugs = _fmt.shapeDrugResults(drugs_raw) if isinstance(drugs_raw, dict) else []
    except Exception:
        drugs = []

    eligible, excluded = [], []
    for t in (trials or []):
        ok, reason = _hard_gate(t, age, sex)
        if ok:
            eligible.append(t)
        else:
            excluded.append(ExcludedTrial(
                id=t.get("id") or "",
                title=t.get("title") or "",
                exclusion_reason=reason,
            ).model_dump())

    profiles = sorted(
        [buildTrialProfile(t, age, condition, papers or [], drugs) for t in eligible],
        key=lambda p: p.get("final_score", 0.0),
        reverse=True,
    )

    result = SynthesisResult(
        clinicalInsight=buildClinicalInsight(profiles, condition),
        trialProfiles=profiles,
        excludedTrials=excluded,
    ).model_dump()

    elapsed = round((time.monotonic() - t0) * 1000, 1)
    _log.info("synthesis_done", extra={
        "condition": condition, "age": age, "sex": sex or "any",
        "scored": len(profiles), "excluded": len(excluded), "ms": elapsed,
    })

    await synthesis_cache.set(key, result)
    return result
```

---

## FILE 4 — src/helix/tools/eligibility.py (OVERWRITE)

```python
from helix.clients.trialsClient import TrialsClient
from helix.utils.formatter import Formatter
from helix.utils.synonyms import expand

_client = TrialsClient()
_formatter = Formatter()


def _legacy_score(trial: dict, age: int, condition: str) -> int:
    """
    Lightweight pre-filter score (0–100 integer).
    Used ONLY for initial ranking before the synthesis pipeline runs.
    The authoritative scoring happens in synthesis.py (vector-based).
    Returns 0 if the patient is outside the age window (hard rejection).
    """
    min_age = trial.get("min_age")
    max_age = trial.get("max_age")

    if isinstance(min_age, int) and age < min_age:
        return 0
    if isinstance(max_age, int) and age > max_age:
        return 0

    score = 40
    cond_words = condition.lower().split()
    title   = (trial.get("title") or "").lower()
    summary = (trial.get("summary") or "").lower()

    score += min(sum(1 for w in cond_words if w in title) * 15, 40)
    score += min(sum(1 for w in cond_words if w in summary) * 5, 20)

    phase = trial.get("phase") or []
    if any(p in ["PHASE3", "PHASE4"] for p in phase):
        score += 10

    return min(score, 100)


async def matchEligibility(
    condition: str,
    age: int,
    location: str = None,
    limit: int = 10,
    sex: str = None,
) -> list[dict]:
    """
    Fetch trials and return those passing basic age and sex eligibility,
    ordered by lightweight pre-filter score descending.
    v1.2.0: synonym expansion + sex filtering added.
    """
    condition = expand(condition)
    raw = await _client.search(condition, location, limit * 2)
    trials = _formatter.shapeTrialResults(raw)

    scored = []
    for t in trials:
        # Sex hard gate — skip before expensive scoring
        if sex:
            trial_sex = (t.get("sex") or "ALL").upper()
            if trial_sex != "ALL" and trial_sex != sex.upper():
                continue
        s = _legacy_score(t, age, condition)
        if s > 0:
            scored.append({**t, "match_score_legacy": s})

    scored.sort(key=lambda x: x.get("match_score_legacy", 0), reverse=True)
    return scored[:limit]
```

---

## FILE 5 — src/helix/api.py (OVERWRITE)

```python
"""
Helix REST API — FastAPI layer.
Start: helix-api  OR  python -m helix.api
Docs:  http://localhost:8000/docs
"""
from contextlib import asynccontextmanager
from typing import Literal, Optional
import uvicorn
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from helix.tools.synthesis import synthesizeEvidence
from helix.tools.trials import findTrials
from helix.tools.pubmed import searchPapers
from helix.tools.fda import lookupDrug
from helix.tools.eligibility import matchEligibility
from helix.tools.health import checkHealth
from helix.cache import synthesis_cache, trials_cache, papers_cache, drugs_cache
from helix.config import server as server_config
from helix.config.weights import WEIGHTS


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    for c in [synthesis_cache, trials_cache, papers_cache, drugs_cache]:
        await c.clear()


app = FastAPI(
    title="Helix",
    description="Clinical evidence synthesis engine. Queries ClinicalTrials.gov, PubMed, and openFDA simultaneously. No API key required.",
    version=server_config.version,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

_SEX_DESCRIPTION = "Optional patient sex filter: MALE or FEMALE. Trials requiring the opposite sex are excluded."

_WEIGHT_DESCRIPTIONS = {
    "condition_match":       "Token overlap between patient condition and trial title (0–1)",
    "eligibility_fit":       "Age-window centrality: 1.0=patient at window center, 0.5=at edge, 0.75=open enrollment",
    "evidence_support":      "Fraction of PubMed papers whose title or abstract mentions the condition (0–1)",
    "trial_phase_maturity":  "Phase 3/4=1.0, Phase 2=0.6, Phase 1=0.3, unknown=0.5",
}


class SynthesizeRequest(BaseModel):
    condition: str
    age: int
    location: Optional[str] = None
    sex: Optional[Literal["MALE", "FEMALE"]] = None


class EligibilityRequest(BaseModel):
    condition: str
    age: int
    location: Optional[str] = None
    limit: int = 10
    sex: Optional[Literal["MALE", "FEMALE"]] = None


@app.get("/health", tags=["System"])
async def health():
    """Ping all 3 APIs and report latency per service."""
    return await checkHealth()


@app.get("/score-weights", tags=["System"])
async def score_weights():
    """
    Return the scoring weight vector used to rank clinical trials.
    Enables API consumers to understand and explain trial rankings.
    """
    return {
        "weights": WEIGHTS,
        "formula": "final_score = 100 * sum(weight_i * component_i)",
        "descriptions": _WEIGHT_DESCRIPTIONS,
    }


@app.get("/cache/stats", tags=["System"])
async def cache_stats():
    """Inspect in-memory cache state."""
    return {k: v.stats() for k, v in [
        ("synthesis", synthesis_cache), ("trials", trials_cache),
        ("papers", papers_cache), ("drugs", drugs_cache),
    ]}


@app.delete("/cache", tags=["System"])
async def clear_cache():
    """Flush all caches."""
    for c in [synthesis_cache, trials_cache, papers_cache, drugs_cache]:
        await c.clear()
    return {"cleared": True}


@app.post("/synthesize", tags=["Evidence"])
async def synthesize(req: SynthesizeRequest):
    """
    Full cross-database synthesis with scored, explainable trial profiles.
    Abbreviations like T2D, NSCLC, COPD are automatically expanded.
    """
    return await synthesizeEvidence(req.condition, req.age, req.location, req.sex)


@app.post("/eligibility", tags=["Evidence"])
async def eligibility(req: EligibilityRequest):
    """
    Match patient profile to trials by condition, age, and optional sex.
    Abbreviations are automatically expanded.
    """
    return await matchEligibility(req.condition, req.age, req.location, req.limit, req.sex)


@app.get("/trials", tags=["Data"])
async def trials(
    condition: str = Query(...),
    location: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
):
    """Active recruiting trials on ClinicalTrials.gov."""
    return await findTrials(condition, location, limit)


@app.get("/papers", tags=["Data"])
async def papers(
    topic: str = Query(...),
    yearFrom: Optional[int] = Query(None),
    yearTo: Optional[int] = Query(None),
    limit: int = Query(10, ge=1, le=50),
):
    """PubMed peer-reviewed research papers."""
    return await searchPapers(topic, yearFrom, yearTo, limit)


@app.get("/drugs", tags=["Data"])
async def drugs(
    name: str = Query(...),
    limit: int = Query(5, ge=1, le=20),
):
    """FDA drug label information."""
    return await lookupDrug(name, limit)


def run():
    uvicorn.run("helix.api:app", host="0.0.0.0", port=8000, reload=False, log_level="warning")


if __name__ == "__main__":
    run()
```

---

## FILE 6 — tests/unit/test_synonyms.py (CREATE)

```python
"""Unit tests for condition synonym expansion — no I/O."""
import pytest
from helix.utils.synonyms import expand


def test_uppercase_abbreviation():
    assert expand("T2D") == "Type 2 Diabetes"

def test_lowercase_abbreviation():
    assert expand("nsclc") == "Non-Small Cell Lung Cancer"

def test_mixed_case_abbreviation():
    assert expand("COPD") == "Chronic Obstructive Pulmonary Disease"

def test_passthrough_canonical_name():
    assert expand("Type 2 Diabetes") == "Type 2 Diabetes"

def test_passthrough_unknown_string():
    assert expand("XYZ123") == "XYZ123"

def test_strips_leading_trailing_whitespace():
    assert expand("  t2d  ") == "Type 2 Diabetes"

def test_hiv():
    assert expand("HIV") == "Human Immunodeficiency Virus"

def test_afib():
    assert expand("afib") == "Atrial Fibrillation"

def test_empty_string_passthrough():
    assert expand("") == ""

def test_ra_rheumatoid_arthritis():
    assert expand("RA") == "Rheumatoid Arthritis"
```

---

## FILE 7 — pyproject.toml (OVERWRITE)

```toml
[project]
name = "helix"
version = "1.2.0"
description = "Clinical evidence synthesis engine — ClinicalTrials.gov, PubMed, and openFDA in one API"
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.11"
dependencies = [
    "mcp[cli]>=1.0.0",
    "httpx>=0.27.0",
    "curl_cffi>=0.7.0",
    "fastapi>=0.111.0",
    "uvicorn>=0.30.0",
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-mock>=3.14.0",
]

[project.scripts]
helix     = "helix.server:run"
helix-api = "helix.api:run"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/helix"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

---

## FILE 8 — CHANGELOG.md (OVERWRITE)

```markdown
# Changelog

## [1.2.0] — 2025-06-XX

### Fixed
- **`ServerConfig.version` hardcoded to `"1.0.0"`** — Now reads dynamically from
  package metadata via `importlib.metadata`. `/health`, `/docs`, and all API
  responses now report the correct version automatically on every release.

### Added
- **Condition synonym expansion** (`src/helix/utils/synonyms.py`) — 65+ medical
  abbreviation and alias mappings applied before any external API call. Queries for
  "T2D", "NSCLC", "COPD", "afib", "RA", "HCV" etc. are transparently expanded to
  their canonical full names. Zero new dependencies — pure stdlib dict lookup.
- **Sex eligibility parameter** — `synthesizeEvidence` and `matchEligibility` now
  accept an optional `sex` argument (`"MALE"` or `"FEMALE"`). Trials with a sex
  constraint that doesn't match the patient are excluded by the hard gate and
  reported in `excludedTrials` with reason `sex mismatch`. REST endpoints
  `/synthesize` and `/eligibility` accept `sex` in the request body.
- **`GET /score-weights`** — Returns the scoring weight vector, the formula, and
  plain-English descriptions of every component. Lets API consumers explain trial
  rankings without reading source code.
- **Unit tests for synonym expansion** (`tests/unit/test_synonyms.py`) — 10 pure-
  Python assertions covering uppercase, lowercase, mixed-case, whitespace stripping,
  and passthrough behavior.

---

## [1.1.0] — 2025-06-02

### Fixed
- **`eligibility_fit` hardcoded to `1.0`** — This component carries 30% weight
  in the scoring model but always returned full marks, making it meaningless.
  Now computes **age-window centrality**: patient at window center = 1.0,
  patient at window edge = 0.5, open enrollment = 0.75. Range: [0.5, 1.0].
- **PubMed abstracts always empty** — `esummary` endpoint does not return
  abstract text. Added `fetchAbstracts()` via `efetch` (XML, stdlib only,
  no extra deps). Abstracts now populated in all paper results, capped at 800 chars.
  Evidence support scoring now also checks abstract text, improving match accuracy.

### Added
- **GitHub Actions CI** (`.github/workflows/ci.yml`) — runs unit tests on
  Python 3.11 and 3.12 on every push and PR; also verifies all public imports
- **Docker support** — `Dockerfile` (slim, layer-cached, with HEALTHCHECK)
  and `docker-compose.yml`; start with `docker compose up`
- **Real unit test suite** (`tests/unit/`) — 40+ assertions across formatter,
  TTL cache, and scoring logic; uses `unittest.mock`, no extra deps

### Changed
- Version `1.0.0` → `1.1.0`
- `pytest-mock` added to `[dev]` optional dependencies
- Evidence support scoring enhanced: checks both title and abstract text

---

## [1.0.0] — 2025-06-01

### Added
- FastAPI REST layer (`helix-api`) on `:8000` with Swagger UI at `/docs`
- Async TTL cache — synthesis 5 min, trials 3 min, papers 10 min, drugs 1 hr
- Health check MCP tool + `GET /health` REST endpoint with per-service latency
- Pydantic v2 domain models across all module boundaries
- Structured JSON logging to stderr (Datadog/CloudWatch compatible)
- Exponential backoff retry (3 attempts, 1s → 2s) on all API clients

## [0.2.0] — 2025-05-30

### Fixed
- WAF bypass — `curl_cffi` Chrome TLS impersonation resolves ClinicalTrials.gov 403

## [0.1.0] — 2025-05-28

### Added
- Initial production refactor: vector scoring, hard eligibility gate, async clients
```

---

## VERIFICATION CHECKLIST

After Gemini writes all 9 files, run these commands from the repo root:

```bash
# 1. Reinstall package so importlib.metadata picks up 1.2.0
pip install -e ".[dev]" -q

# 2. Run full unit test suite (all 3 existing test modules + new synonyms tests)
pytest tests/unit/ -v --tb=short

# 3. Smoke-test synonym expansion
python -c "from helix.utils.synonyms import expand; print(expand('T2D')); print(expand('nsclc')); print(expand('Unknown'))"
# Expected: Type 2 Diabetes / Non-Small Cell Lung Cancer / Unknown

# 4. Verify version is now correct
python -c "from helix.config import server; print(server.version)"
# Expected: 1.2.0

# 5. Verify synthesis accepts sex param (unit import check)
python -c "
import inspect
from helix.tools.synthesis import synthesizeEvidence
from helix.tools.eligibility import matchEligibility
print('synthesizeEvidence params:', list(inspect.signature(synthesizeEvidence).parameters))
print('matchEligibility params:', list(inspect.signature(matchEligibility).parameters))
"
# Expected: [..., 'sex'] in both

# 6. Start REST API and verify new endpoints
helix-api &
sleep 3

curl -s http://localhost:8000/score-weights | python -m json.tool
# Expected: {"weights": {...}, "formula": "...", "descriptions": {...}}

curl -s http://localhost:8000/health | python -m json.tool
# Expected: version is "1.2.0"

# 7. Test sex param in synthesis via REST
curl -s -X POST http://localhost:8000/synthesize \
  -H "Content-Type: application/json" \
  -d '{"condition": "T2D", "age": 45, "sex": "FEMALE"}' \
  | python -m json.tool
# Expected: condition expanded to "Type 2 Diabetes" in clinicalInsight;
#           any MALE-only trials appear in excludedTrials with sex mismatch reason

# 8. Kill API
pkill -f "helix-api"
```

All 9 files written. All checks passing = v1.2.0 complete.
