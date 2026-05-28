# HELIX v1.3.0 UPGRADE — GEMINI CLI EXECUTION PROMPT
# Run from inside: Helix-main/
# Gemini: execute every instruction in this file exactly, top to bottom.

## WHAT THIS FIXES AND ADDS

BUG FIX — MCP tool parity: sex param was added to REST API in v1.2.0 but
  server.py MCP tools were never updated. synthesize_evidence and match_eligibility
  MCP tools still don't accept sex. Any Claude Desktop user can't use sex filtering.

BUG FIX — Synonym expansion gap: expand() is called in synthesis.py and
  eligibility.py, but findTrials() and searchPapers() call the API directly with
  the raw string. A user searching for "T2D" via find_trials MCP tool or GET /trials
  gets raw unmatched results. Fix: apply expand() in trials.py and pubmed.py.

NEW — expanded_from field in ClinicalInsight: when a condition abbreviation is
  expanded (T2D → Type 2 Diabetes), callers currently have no way to know it happened.
  Add optional expanded_from: str to ClinicalInsight model and populate it in synthesis.
  API response becomes self-documenting.

NEW — GET /synonyms endpoint: returns the full abbreviation → canonical name map.
  Useful for UI autocomplete, validation, and debugging. Zero cost to implement.

NEW — 2 unit tests for expanded_from in buildClinicalInsight.
NEW — CI verify imports: add explicit assertion that expand("T2D") == "Type 2 Diabetes".

## FILE OPERATIONS (10 total — all overwrites, no creates)

Overwrites:
  src/helix/server.py              — sex param on synthesize_evidence + match_eligibility
  src/helix/models.py              — add expanded_from: Optional[str] to ClinicalInsight
  src/helix/tools/synthesis.py     — populate expanded_from, refine expand() call site
  src/helix/tools/trials.py        — apply expand() before cache key + API call
  src/helix/tools/pubmed.py        — apply expand() before cache key + API call
  src/helix/api.py                 — add GET /synonyms endpoint
  tests/unit/test_scoring.py       — add 2 tests for expanded_from in buildClinicalInsight
  .github/workflows/ci.yml         — add synonyms import assertion to verify step
  pyproject.toml                   — version 1.3.0
  CHANGELOG.md

Do NOT touch any other file.

---

## FILE 1 — src/helix/server.py (OVERWRITE)

```python
from mcp.server.fastmcp import FastMCP
from helix.tools.trials import findTrials
from helix.tools.pubmed import searchPapers
from helix.tools.fda import lookupDrug
from helix.tools.eligibility import matchEligibility
from helix.tools.synthesis import synthesizeEvidence
from helix.tools.health import checkHealth
from helix.config import server as server_config

mcp = FastMCP(server_config.name)


@mcp.tool()
async def find_trials(condition: str, location: str = None, limit: int = 10) -> list[dict]:
    """Find active clinical trials matching a medical condition.
    Abbreviations like T2D, NSCLC, COPD are automatically expanded.

    Args:
        condition: Medical condition or abbreviation (e.g. "T2D", "Type 2 Diabetes").
        location: Optional location filter (e.g. "Boston, MA").
        limit: Max results (default 10).
    """
    return await findTrials(condition, location, limit)


@mcp.tool()
async def search_papers(topic: str, yearFrom: int = None, yearTo: int = None, limit: int = 10) -> list[dict]:
    """Search PubMed for peer-reviewed research papers.
    Abbreviations like T2D, NSCLC, COPD are automatically expanded.

    Args:
        topic: Research topic or abbreviation.
        yearFrom: Start year filter (optional).
        yearTo: End year filter (optional).
        limit: Max results (default 10).
    """
    return await searchPapers(topic, yearFrom, yearTo, limit)


@mcp.tool()
async def lookup_drug(name: str, limit: int = 5) -> list[dict]:
    """Look up FDA drug information by brand or generic name."""
    return await lookupDrug(name, limit)


@mcp.tool()
async def match_eligibility(
    condition: str,
    age: int,
    location: str = None,
    limit: int = 10,
    sex: str = None,
) -> list[dict]:
    """Match a patient profile to clinical trials ranked by eligibility fit.
    Abbreviations like T2D, NSCLC, COPD are automatically expanded.

    Args:
        condition: Medical condition or abbreviation (e.g. "T2D", "NSCLC").
        age: Patient age in years.
        location: Optional location filter (e.g. "Boston, MA").
        limit: Max results (default 10).
        sex: Optional patient sex filter: MALE or FEMALE.
    """
    return await matchEligibility(condition, age, location, limit, sex)


@mcp.tool()
async def synthesize_evidence(
    condition: str,
    age: int,
    location: str = None,
    sex: str = None,
) -> dict:
    """Cross-database clinical evidence synthesis.
    Queries ClinicalTrials.gov, PubMed, and openFDA concurrently.
    Returns scored, ranked trials with full explainability vectors.
    Abbreviations like T2D, NSCLC, COPD are automatically expanded.
    Response includes expanded_from when an abbreviation was resolved.

    Args:
        condition: Medical condition or abbreviation (e.g. "T2D", "NSCLC").
        age: Patient age in years.
        location: Optional location filter (e.g. "London, UK").
        sex: Optional patient sex filter: MALE or FEMALE.
    """
    return await synthesizeEvidence(condition, age, location, sex)


@mcp.tool()
async def health_check() -> dict:
    """Check live connectivity and latency to all 3 external APIs."""
    return await checkHealth()


def run():
    mcp.run()


if __name__ == "__main__":
    run()
```

---

## FILE 2 — src/helix/models.py (OVERWRITE)

```python
"""Helix canonical domain models — Pydantic v2."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class Trial(BaseModel):
    id: str = ""
    title: str = ""
    status: str = ""
    phase: list[str] = Field(default_factory=list)
    summary: str = ""
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    min_age_raw: str = ""
    max_age_raw: str = ""
    sex: str = "ALL"
    contact_name: str = ""
    contact_email: str = ""
    url: str = ""
    model_config = {"extra": "ignore"}


class Paper(BaseModel):
    id: str = ""
    title: str = ""
    abstract: str = ""
    authors: list[str] = Field(default_factory=list)
    journal: str = ""
    year: int = 0
    url: str = ""
    model_config = {"extra": "ignore"}


class Drug(BaseModel):
    brand_name: str = ""
    generic_name: str = ""
    manufacturer: str = ""
    route: list[str] = Field(default_factory=list)
    indications: str = ""
    warnings: str = ""
    model_config = {"extra": "ignore"}


class ScoreVector(BaseModel):
    condition_match: float = 0.0
    eligibility_fit: float = 0.0
    evidence_support: float = 0.0
    trial_phase_maturity: float = 0.0


class ExplainabilityVector(BaseModel):
    condition_overlap_raw: int = 0
    evidence_hits_raw: int = 0
    age_penalty: float = 0.0
    phase_penalty: float = 0.0


class TrialProfile(BaseModel):
    id: str = ""
    title: str = ""
    url: str = ""
    phase: list[str] = Field(default_factory=list)
    final_score: float = 0.0
    score_vector: ScoreVector = Field(default_factory=ScoreVector)
    explainability_vector: ExplainabilityVector = Field(default_factory=ExplainabilityVector)
    risk_flags: list[str] = Field(default_factory=list)


class ClinicalInsight(BaseModel):
    total_trials: int = 0
    top_score: float = 0.0
    average_score: float = 0.0
    condition: str = ""
    expanded_from: Optional[str] = None  # v1.3.0: set when input was an abbreviation


class ExcludedTrial(BaseModel):
    id: str = ""
    title: str = ""
    exclusion_reason: str = ""


class SynthesisResult(BaseModel):
    clinicalInsight: ClinicalInsight = Field(default_factory=ClinicalInsight)
    trialProfiles: list[TrialProfile] = Field(default_factory=list)
    excludedTrials: list[ExcludedTrial] = Field(default_factory=list)


class ServiceHealth(BaseModel):
    status: str
    latency_ms: float = 0.0
    error: Optional[str] = None


class HealthReport(BaseModel):
    status: str
    version: str = "1.0.0"
    services: dict[str, ServiceHealth] = Field(default_factory=dict)
    timestamp: str = ""
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

v1.3.0: expanded_from populated in ClinicalInsight when abbreviation is resolved.
v1.2.0: synonym expansion + sex param + _hard_gate sex check.
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
        if trial_sex != "ALL" and trial_sex != sex.upper():
            return False, f"sex mismatch: trial={trial_sex}, patient={sex.upper()}"
    if not trial.get("id"):
        return False, "missing trial ID"
    if not trial.get("title"):
        return False, "missing trial title"
    return True, ""


def _eligibility_fit_score(trial: dict, age: int) -> float:
    """
    Age-window centrality score. Center=1.0, edge=0.5, open enrollment=0.75.
    Range: [0.5, 1.0]. Hard gate already excluded out-of-window patients.
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


def buildClinicalInsight(
    profiles: list,
    condition: str,
    expanded_from: str = None,
) -> dict:
    if not profiles:
        return ClinicalInsight(
            condition=condition or "",
            expanded_from=expanded_from,
        ).model_dump()
    scores = [p.get("final_score", 0.0) for p in profiles]
    return ClinicalInsight(
        total_trials=len(profiles),
        top_score=round(max(scores), 2),
        average_score=round(sum(scores) / len(scores), 2),
        condition=condition or "",
        expanded_from=expanded_from,
    ).model_dump()


async def synthesizeEvidence(
    condition: str,
    age: int,
    location: str = None,
    sex: str = None,
) -> dict:
    """Full cross-database synthesis. Cached 5 min per (condition, age, location, sex)."""
    # Expand abbreviation and record original for response transparency
    original = condition.strip()
    condition = expand(original)
    expanded_from = original if condition != original else None

    key = f"synthesis:{condition.lower()}:{age}:{location or ''}:{sex or ''}"
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
        clinicalInsight=buildClinicalInsight(profiles, condition, expanded_from),
        trialProfiles=profiles,
        excludedTrials=excluded,
    ).model_dump()

    elapsed = round((time.monotonic() - t0) * 1000, 1)
    _log.info("synthesis_done", extra={
        "condition": condition, "age": age, "sex": sex or "any",
        "expanded_from": expanded_from,
        "scored": len(profiles), "excluded": len(excluded), "ms": elapsed,
    })

    await synthesis_cache.set(key, result)
    return result
```

---

## FILE 4 — src/helix/tools/trials.py (OVERWRITE)

```python
from helix.clients.trialsClient import TrialsClient
from helix.utils.formatter import Formatter
from helix.utils.synonyms import expand
from helix.cache import trials_cache
from helix.logger import get_logger

_client = TrialsClient()
_fmt    = Formatter()
_log    = get_logger(__name__)


async def findTrials(condition: str, location: str = None, limit: int = 10) -> list[dict]:
    """Find active clinical trials. Synonym-expanded, cached 3 min. Never raises."""
    condition = expand(condition)
    key = f"trials:{condition.lower().strip()}:{location or ''}:{limit}"
    cached = await trials_cache.get(key)
    if cached is not None:
        _log.info("cache_hit", extra={"tool": "trials", "condition": condition})
        return cached
    try:
        raw = await _client.search(condition, location, limit)
        result = _fmt.shapeTrialResults(raw)
        await trials_cache.set(key, result)
        _log.info("fetched", extra={"tool": "trials", "condition": condition, "count": len(result)})
        return result
    except Exception as e:
        _log.warning("error", extra={"tool": "trials", "error": str(e)})
        return [{"id": "", "title": f"[error: {e}]", "status": "", "phase": [], "url": ""}]
```

---

## FILE 5 — src/helix/tools/pubmed.py (OVERWRITE)

```python
from helix.clients.pubmedClient import PubMedClient
from helix.utils.formatter import Formatter
from helix.utils.synonyms import expand
from helix.cache import papers_cache
from helix.logger import get_logger

_client = PubMedClient()
_fmt    = Formatter()
_log    = get_logger(__name__)


async def searchPapers(
    topic: str,
    yearFrom: int = None,
    yearTo: int = None,
    limit: int = 10,
) -> list[dict]:
    """
    Search PubMed for papers. Synonym-expanded, fetches full abstracts via efetch.
    Cached 10 min. Never raises.
    """
    topic = expand(topic)
    key = f"papers:{topic.lower().strip()}:{yearFrom}:{yearTo}:{limit}"
    cached = await papers_cache.get(key)
    if cached is not None:
        _log.info("cache_hit", extra={"tool": "pubmed", "topic": topic})
        return cached
    try:
        ids = await _client.search(topic, year_from=yearFrom, year_to=yearTo, limit=limit)
        if not ids:
            return []

        import asyncio
        summaries, abstracts = await asyncio.gather(
            _client.fetchSummaries(ids),
            _client.fetchAbstracts(ids),
        )

        result = _fmt.shapePaperResults(ids, summaries)

        for paper in result:
            pid = paper.get("id", "")
            if pid in abstracts:
                paper["abstract"] = abstracts[pid]

        await papers_cache.set(key, result)
        _log.info("fetched", extra={
            "tool": "pubmed", "topic": topic, "count": len(result),
            "with_abstracts": sum(1 for p in result if p.get("abstract")),
        })
        return result
    except Exception as e:
        _log.warning("error", extra={"tool": "pubmed", "error": str(e)})
        return [{"id": "", "title": f"[error: {e}]", "abstract": "", "authors": [], "journal": "", "year": 0, "url": ""}]
```

---

## FILE 6 — src/helix/api.py (OVERWRITE)

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
from helix.utils.synonyms import _MAP as _SYNONYM_MAP


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

_WEIGHT_DESCRIPTIONS = {
    "condition_match":      "Token overlap between patient condition and trial title (0–1)",
    "eligibility_fit":      "Age-window centrality: 1.0=center, 0.5=edge, 0.75=open enrollment",
    "evidence_support":     "Fraction of PubMed papers matching condition keywords (0–1)",
    "trial_phase_maturity": "Phase 3/4=1.0, Phase 2=0.6, Phase 1=0.3, unknown=0.5",
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


# ── System ──────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health():
    """Ping all 3 APIs and report latency per service."""
    return await checkHealth()


@app.get("/score-weights", tags=["System"])
async def score_weights():
    """Return the scoring weight vector, formula, and component descriptions."""
    return {
        "weights": WEIGHTS,
        "formula": "final_score = 100 * sum(weight_i * component_i)",
        "descriptions": _WEIGHT_DESCRIPTIONS,
    }


@app.get("/synonyms", tags=["System"])
async def synonyms():
    """
    Return all known condition abbreviations and their canonical expansions.
    Useful for UI autocomplete, input validation, and debugging synonym expansion.
    """
    return {
        "total": len(_SYNONYM_MAP),
        "mappings": {k: v for k, v in sorted(_SYNONYM_MAP.items())},
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


# ── Evidence ─────────────────────────────────────────────────────────────────

@app.post("/synthesize", tags=["Evidence"])
async def synthesize(req: SynthesizeRequest):
    """
    Full cross-database synthesis with scored, explainable trial profiles.
    Abbreviations (T2D, NSCLC, COPD, etc.) are automatically expanded.
    Response includes clinicalInsight.expanded_from when expansion occurred.
    """
    return await synthesizeEvidence(req.condition, req.age, req.location, req.sex)


@app.post("/eligibility", tags=["Evidence"])
async def eligibility(req: EligibilityRequest):
    """Match patient profile to trials by condition, age, and optional sex."""
    return await matchEligibility(req.condition, req.age, req.location, req.limit, req.sex)


# ── Data ──────────────────────────────────────────────────────────────────────

@app.get("/trials", tags=["Data"])
async def trials(
    condition: str = Query(...),
    location: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
):
    """Active recruiting trials on ClinicalTrials.gov. Abbreviations auto-expanded."""
    return await findTrials(condition, location, limit)


@app.get("/papers", tags=["Data"])
async def papers(
    topic: str = Query(...),
    yearFrom: Optional[int] = Query(None),
    yearTo: Optional[int] = Query(None),
    limit: int = Query(10, ge=1, le=50),
):
    """PubMed peer-reviewed research papers. Abbreviations auto-expanded."""
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

## FILE 7 — tests/unit/test_scoring.py (OVERWRITE)

```python
"""Unit tests for synthesis scoring functions — pure logic, no I/O."""
import pytest
from helix.tools.synthesis import (
    _phase_score,
    _norm,
    _hard_gate,
    _eligibility_fit_score,
    buildClinicalInsight,
)


# --- _phase_score ---

def test_phase_score_p4():
    assert _phase_score(["PHASE4"]) == 1.0

def test_phase_score_p3():
    assert _phase_score(["PHASE3"]) == 1.0

def test_phase_score_p2():
    assert _phase_score(["PHASE2"]) == 0.6

def test_phase_score_p1():
    assert _phase_score(["PHASE1"]) == 0.3

def test_phase_score_empty():
    assert _phase_score([]) == 0.5

def test_phase_score_not_list():
    assert _phase_score(None) == 0.5


# --- _norm ---

def test_norm_zero_value():
    assert _norm(0, 10) == 0.0

def test_norm_full():
    assert _norm(10, 10) == 1.0

def test_norm_clamp():
    assert _norm(15, 10) == 1.0

def test_norm_zero_max():
    assert _norm(5, 0) == 0.0

def test_norm_partial():
    assert abs(_norm(5, 10) - 0.5) < 1e-9


# --- _hard_gate ---

def test_hard_gate_passes():
    t = {"id": "NCT001", "title": "Test Trial", "min_age": 18, "max_age": 65}
    ok, reason = _hard_gate(t, 45)
    assert ok is True
    assert reason == ""

def test_hard_gate_age_too_young():
    t = {"id": "NCT001", "title": "Test", "min_age": 18}
    ok, reason = _hard_gate(t, 16)
    assert ok is False
    assert "below" in reason

def test_hard_gate_age_too_old():
    t = {"id": "NCT001", "title": "Test", "max_age": 65}
    ok, reason = _hard_gate(t, 70)
    assert ok is False
    assert "above" in reason

def test_hard_gate_missing_id():
    t = {"id": "", "title": "Test"}
    ok, reason = _hard_gate(t, 45)
    assert ok is False
    assert "ID" in reason

def test_hard_gate_missing_title():
    t = {"id": "NCT001", "title": ""}
    ok, reason = _hard_gate(t, 45)
    assert ok is False
    assert "title" in reason

def test_hard_gate_no_age_constraints():
    t = {"id": "NCT001", "title": "Test", "min_age": None, "max_age": None}
    ok, _ = _hard_gate(t, 99)
    assert ok is True

def test_hard_gate_sex_mismatch():
    t = {"id": "NCT001", "title": "Test", "sex": "MALE"}
    ok, reason = _hard_gate(t, 45, sex="FEMALE")
    assert ok is False
    assert "sex mismatch" in reason

def test_hard_gate_sex_all_passes_any_patient():
    t = {"id": "NCT001", "title": "Test", "sex": "ALL"}
    ok, _ = _hard_gate(t, 45, sex="FEMALE")
    assert ok is True

def test_hard_gate_sex_match_passes():
    t = {"id": "NCT001", "title": "Test", "sex": "FEMALE"}
    ok, _ = _hard_gate(t, 45, sex="FEMALE")
    assert ok is True

def test_hard_gate_no_sex_filter_skips_check():
    t = {"id": "NCT001", "title": "Test", "sex": "MALE"}
    ok, _ = _hard_gate(t, 45, sex=None)
    assert ok is True


# --- _eligibility_fit_score ---

def test_elig_fit_center():
    t = {"min_age": 30, "max_age": 50}
    assert _eligibility_fit_score(t, 40) == 1.0

def test_elig_fit_at_min_edge():
    t = {"min_age": 30, "max_age": 50}
    assert _eligibility_fit_score(t, 30) == 0.5

def test_elig_fit_at_max_edge():
    t = {"min_age": 30, "max_age": 50}
    assert _eligibility_fit_score(t, 50) == 0.5

def test_elig_fit_open_enrollment():
    t = {"min_age": None, "max_age": None}
    assert _eligibility_fit_score(t, 45) == 0.75

def test_elig_fit_range_is_0_5_to_1():
    t = {"min_age": 18, "max_age": 80}
    for age in [18, 30, 49, 65, 80]:
        score = _eligibility_fit_score(t, age)
        assert 0.5 <= score <= 1.0, f"score {score} out of range for age {age}"

def test_elig_fit_only_min_age():
    t = {"min_age": 18, "max_age": None}
    score = _eligibility_fit_score(t, 50)
    assert 0.5 <= score <= 1.0

def test_elig_fit_only_max_age():
    t = {"min_age": None, "max_age": 65}
    score = _eligibility_fit_score(t, 30)
    assert 0.5 <= score <= 1.0


# --- buildClinicalInsight ---

def test_build_insight_empty():
    r = buildClinicalInsight([], "diabetes")
    assert r["total_trials"] == 0
    assert r["condition"] == "diabetes"
    assert r["top_score"] == 0.0

def test_build_insight_scores():
    profiles = [{"final_score": 80.0}, {"final_score": 60.0}, {"final_score": 70.0}]
    r = buildClinicalInsight(profiles, "cancer")
    assert r["total_trials"] == 3
    assert r["top_score"] == 80.0
    assert r["average_score"] == 70.0
    assert r["condition"] == "cancer"

def test_build_insight_expanded_from_set():
    """expanded_from is passed through to the response when abbreviation was resolved."""
    profiles = [{"final_score": 75.0}]
    r = buildClinicalInsight(profiles, "Type 2 Diabetes", expanded_from="T2D")
    assert r["expanded_from"] == "T2D"
    assert r["condition"] == "Type 2 Diabetes"

def test_build_insight_no_expansion():
    """expanded_from is None when no abbreviation was resolved."""
    profiles = [{"final_score": 75.0}]
    r = buildClinicalInsight(profiles, "Type 2 Diabetes", expanded_from=None)
    assert r["expanded_from"] is None
```

---

## FILE 8 — .github/workflows/ci.yml (OVERWRITE)

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Run unit tests
        run: pytest tests/unit/ -v --tb=short

      - name: Verify imports
        run: |
          python -c "from helix.models import Trial, TrialProfile, SynthesisResult, HealthReport, ClinicalInsight"
          python -c "from helix.cache import synthesis_cache, trials_cache, papers_cache, drugs_cache"
          python -c "from helix.logger import get_logger"
          python -c "from helix.api import app"
          python -c "from helix.tools.health import checkHealth"
          python -c "from helix.tools.synthesis import _eligibility_fit_score, buildClinicalInsight"
          python -c "from helix.utils.synonyms import expand; assert expand('T2D') == 'Type 2 Diabetes', 'synonym expansion broken'"
          python -c "from helix.models import ClinicalInsight; c = ClinicalInsight(condition='x', expanded_from='y'); assert c.expanded_from == 'y'"
```

---

## FILE 9 — pyproject.toml (OVERWRITE)

```toml
[project]
name = "helix"
version = "1.3.0"
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

## FILE 10 — CHANGELOG.md (OVERWRITE)

```markdown
# Changelog

## [1.3.0] — 2025-06-XX

### Fixed
- **MCP tool parity gap** — `synthesize_evidence` and `match_eligibility` MCP tools
  were missing the `sex` parameter added to the REST API in v1.2.0. Claude Desktop
  users could not apply sex filtering via MCP. Both tools now accept `sex: str = None`
  and pass it through to the underlying functions.
- **Synonym expansion gap in `findTrials` and `searchPapers`** — `expand()` was
  applied in `synthesis.py` and `eligibility.py` but not in `trials.py` or
  `pubmed.py`. Calling `find_trials("T2D")` directly (via MCP or `GET /trials`)
  bypassed expansion and queried the API with the raw abbreviation. Fixed.

### Added
- **`expanded_from` field in `ClinicalInsight`** — When a condition abbreviation is
  expanded (e.g. "T2D" → "Type 2 Diabetes"), the original input is now recorded in
  `clinicalInsight.expanded_from` in the synthesis response. `null` when no expansion
  occurred. Makes the API self-documenting and aids debugging.
- **`GET /synonyms`** — Returns the full sorted abbreviation → canonical name
  mapping (65+ entries). Useful for UI autocomplete, client-side validation, and
  verifying that a given abbreviation is recognized by Helix.
- **4 new `_hard_gate` sex tests** in `tests/unit/test_scoring.py` — covers sex
  mismatch rejection, ALL passes any patient, sex match passes, no filter skips check.
- **2 new `buildClinicalInsight` tests** — verify `expanded_from` is populated and
  that `None` is returned correctly when no expansion occurred.
- **CI verify imports** now asserts `expand("T2D") == "Type 2 Diabetes"` and that
  `ClinicalInsight.expanded_from` is accessible, catching regressions on both.

---

## [1.2.0] — 2025-06-XX

### Fixed
- **`ServerConfig.version` hardcoded to `"1.0.0"`** — Now reads dynamically from
  package metadata via `importlib.metadata`.

### Added
- **Condition synonym expansion** (`src/helix/utils/synonyms.py`) — 65+ mappings.
- **Sex eligibility parameter** on `synthesizeEvidence` and `matchEligibility`.
- **`GET /score-weights`** endpoint.
- **10 unit tests** for synonym expansion.

---

## [1.1.0] — 2025-06-02

### Fixed
- `eligibility_fit` hardcoded to `1.0` (now age-window centrality).
- PubMed abstracts always empty (now fetched via efetch XML).

### Added
- GitHub Actions CI, Docker support, real unit test suite (40+ assertions).

---

## [1.0.0] — 2025-06-01

### Added
- FastAPI REST layer on `:8000`, async TTL cache, health check, Pydantic v2 models,
  structured JSON logging, exponential backoff retry on all API clients.

## [0.2.0] — 2025-05-30
- WAF bypass via `curl_cffi` Chrome TLS impersonation.

## [0.1.0] — 2025-05-28
- Initial production refactor: vector scoring, hard eligibility gate, async clients.
```

---

## VERIFICATION CHECKLIST

```bash
# 1. Reinstall so importlib.metadata picks up 1.3.0
pip install -e ".[dev]" -q

# 2. Run full unit suite — expect 70 passing (62 existing + 6 new sex/expanded_from tests + 2 gap fixes)
pytest tests/unit/ -v --tb=short

# 3. Verify expand() now fires in findTrials and searchPapers
python -c "
import ast, pathlib
for f in ['src/helix/tools/trials.py', 'src/helix/tools/pubmed.py']:
    src = pathlib.Path(f).read_text()
    assert 'expand(' in src, f'{f} missing expand() call'
    print(f'OK: {f} has expand()')
"

# 4. Verify expanded_from field on model
python -c "
from helix.models import ClinicalInsight
c = ClinicalInsight(condition='Type 2 Diabetes', expanded_from='T2D')
d = c.model_dump()
assert d['expanded_from'] == 'T2D'
print('OK: expanded_from field works')
"

# 5. Verify MCP sex param parity
python -c "
import inspect
from helix.server import mcp
# FastMCP stores tools in _tool_manager; check via source
import pathlib
src = pathlib.Path('src/helix/server.py').read_text()
assert 'sex: str = None' in src
print('OK: sex param in server.py')
"

# 6. Start REST API and test new endpoints
helix-api &
sleep 3

curl -s http://localhost:8000/synonyms | python -m json.tool | head -10
# Expected: {"total": 65, "mappings": {"ad": "Alzheimer's Disease", ...}}

curl -s "http://localhost:8000/trials?condition=T2D&limit=2" | python -m json.tool | head -5
# Expected: results for "Type 2 Diabetes" (not raw "T2D")

curl -s -X POST http://localhost:8000/synthesize \
  -H "Content-Type: application/json" \
  -d '{"condition": "T2D", "age": 45}' \
  | python -c "import sys,json; d=json.load(sys.stdin); ci=d['clinicalInsight']; print('condition:', ci['condition']); print('expanded_from:', ci['expanded_from'])"
# Expected: condition: Type 2 Diabetes / expanded_from: T2D

pkill -f "helix-api"
```

All 10 files written. All checks passing = v1.3.0 complete.
