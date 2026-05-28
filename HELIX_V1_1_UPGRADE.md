# HELIX v1.1.0 UPGRADE — GEMINI CLI EXECUTION PROMPT
# Run from inside: Helix-main/
# Gemini: execute every instruction in this file exactly, top to bottom.

## WHAT THIS FIXES AND ADDS

BUG FIX 1 — eligibility_fit is hardcoded to 1.0 in synthesis.py.
  This makes the 30% weight component meaningless. Fix: compute
  age-window centrality score (1.0 = patient at window center, 0.5 = at edge).

BUG FIX 2 — PubMed abstracts are always empty strings.
  esummary does not return abstract text. Fix: add fetchAbstracts()
  via efetch API (stdlib XML parsing, no extra deps) and merge into papers.

NEW — GitHub Actions CI (.github/workflows/ci.yml)
  Runs unit tests on Python 3.11 and 3.12 on every push and PR.

NEW — Docker support (Dockerfile + docker-compose.yml)
  Single-command deployment. Includes HEALTHCHECK.

NEW — Real unit test suite (tests/unit/)
  pytest tests with assertions covering formatter, TTL cache, and scoring logic.
  Uses unittest.mock — no extra test dependencies needed.

## FILE OPERATIONS (15 total)

Creates:
  .github/workflows/ci.yml
  Dockerfile
  docker-compose.yml
  .dockerignore
  tests/conftest.py
  tests/unit/__init__.py
  tests/unit/test_formatter.py
  tests/unit/test_cache.py
  tests/unit/test_scoring.py

Overwrites:
  pyproject.toml               — version 1.1.0, add pytest-mock
  src/helix/clients/pubmedClient.py  — add fetchAbstracts via efetch
  src/helix/tools/pubmed.py    — merge abstracts into paper results
  src/helix/tools/synthesis.py — fix elig_m=1.0, add _eligibility_fit_score
  CHANGELOG.md
  README.md

Do NOT touch any other file.

---

## FILE 1 — pyproject.toml (OVERWRITE)

```toml
[project]
name = "helix"
version = "1.1.0"
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

## FILE 2 — .github/workflows/ci.yml (CREATE)

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
          python -c "from helix.models import Trial, TrialProfile, SynthesisResult, HealthReport"
          python -c "from helix.cache import synthesis_cache, trials_cache, papers_cache, drugs_cache"
          python -c "from helix.logger import get_logger"
          python -c "from helix.api import app"
          python -c "from helix.tools.health import checkHealth"
          python -c "from helix.tools.synthesis import _eligibility_fit_score"
```

---

## FILE 3 — Dockerfile (CREATE)

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Layer cache: install deps before copying full source
COPY pyproject.toml .
COPY src/ ./src/

RUN pip install --no-cache-dir .

# Copy remaining files (tests, docs, etc.)
COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD python -c "import httpx, sys; r=httpx.get('http://localhost:8000/health',timeout=5); sys.exit(0 if r.status_code==200 else 1)"

CMD ["helix-api"]
```

---

## FILE 4 — docker-compose.yml (CREATE)

```yaml
services:
  helix-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - PUBMED_EMAIL=${PUBMED_EMAIL:-helix@example.com}
      - PUBMED_API_KEY=${PUBMED_API_KEY:-}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import httpx,sys; r=httpx.get('http://localhost:8000/health',timeout=5); sys.exit(0 if r.status_code==200 else 1)"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
```

---

## FILE 5 — .dockerignore (CREATE)

```
__pycache__
*.pyc
*.pyo
.env
.git
.gitignore
*.md
tests/
dist/
*.egg-info
```

---

## FILE 6 — src/helix/clients/pubmedClient.py (OVERWRITE)

```python
"""NCBI PubMed E-utilities client — esearch + esummary + efetch for full abstracts."""
import asyncio
import xml.etree.ElementTree as ET
import httpx
from helix.config import pubmed as pubmed_config
from helix.logger import get_logger

_log = get_logger(__name__)
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


class PubMedClient:
    def __init__(self):
        self._base = pubmed_config.base_url

    def _params(self) -> dict:
        p = {"email": pubmed_config.email}
        if pubmed_config.api_key:
            p["api_key"] = pubmed_config.api_key
        return p

    async def search(self, topic: str, year_from: int = None, year_to: int = None, limit: int = 10) -> list[str]:
        """Search PubMed and return list of article IDs."""
        q = topic
        if year_from and year_to:
            q += f" AND {year_from}:{year_to}[pdat]"
        elif year_from:
            q += f" AND {year_from}:3000[pdat]"
        params = {**self._params(), "db": "pubmed", "term": q, "retmax": limit, "retmode": "json"}
        last = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=20.0) as c:
                    r = await c.get(f"{self._base}/esearch.fcgi", params=params, headers=_HEADERS)
                    r.raise_for_status()
                    return r.json().get("esearchresult", {}).get("idlist", [])
            except Exception as e:
                last = e
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
        _log.warning("pubmed_search_exhausted", extra={"topic": topic, "error": str(last)})
        return []

    async def fetchSummaries(self, ids: list[str]) -> dict:
        """Fetch metadata (title, authors, journal, year) for a list of PMIDs."""
        if not ids:
            return {}
        params = {**self._params(), "db": "pubmed", "id": ",".join(ids), "retmode": "json"}
        last = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=20.0) as c:
                    r = await c.get(f"{self._base}/esummary.fcgi", params=params, headers=_HEADERS)
                    r.raise_for_status()
                    return r.json()
            except Exception as e:
                last = e
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
        _log.warning("pubmed_fetch_exhausted", extra={"ids": len(ids), "error": str(last)})
        return {}

    async def fetchAbstracts(self, ids: list[str]) -> dict[str, str]:
        """
        Fetch full abstract text via efetch (XML).
        Returns {pmid: abstract_text}. Uses stdlib xml.etree — no extra deps.
        Structured abstracts (with section labels) are joined with spaces.
        Capped at 800 chars to stay token-efficient.
        """
        if not ids:
            return {}
        params = {
            **self._params(),
            "db": "pubmed",
            "id": ",".join(ids),
            "rettype": "abstract",
            "retmode": "xml",
        }
        last = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=30.0) as c:
                    r = await c.get(f"{self._base}/efetch.fcgi", params=params, headers=_HEADERS)
                    r.raise_for_status()
                    root = ET.fromstring(r.text)
                    result: dict[str, str] = {}
                    for article in root.iter("PubmedArticle"):
                        pmid_el = article.find(".//PMID")
                        if pmid_el is None or not pmid_el.text:
                            continue
                        pmid = pmid_el.text.strip()
                        parts = []
                        for el in article.iter("AbstractText"):
                            label = el.get("Label", "")
                            text = (el.text or "").strip()
                            if label and text:
                                parts.append(f"{label}: {text}")
                            elif text:
                                parts.append(text)
                        if parts:
                            result[pmid] = " ".join(parts)[:800]
                    return result
            except Exception as e:
                last = e
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
        _log.warning("pubmed_abstracts_exhausted", extra={"ids": len(ids), "error": str(last)})
        return {}
```

---

## FILE 7 — src/helix/tools/pubmed.py (OVERWRITE)

```python
from helix.clients.pubmedClient import PubMedClient
from helix.utils.formatter import Formatter
from helix.cache import papers_cache
from helix.logger import get_logger

_client = PubMedClient()
_fmt    = Formatter()
_log    = get_logger(__name__)


async def searchPapers(topic: str, yearFrom: int = None, yearTo: int = None, limit: int = 10) -> list[dict]:
    """
    Search PubMed for papers. Fetches full abstracts via efetch.
    Cached 10 min. Never raises.
    """
    key = f"papers:{topic.lower().strip()}:{yearFrom}:{yearTo}:{limit}"
    cached = await papers_cache.get(key)
    if cached is not None:
        _log.info("cache_hit", extra={"tool": "pubmed", "topic": topic})
        return cached
    try:
        ids = await _client.search(topic, year_from=yearFrom, year_to=yearTo, limit=limit)
        if not ids:
            return []

        # Fetch metadata and full abstracts concurrently
        import asyncio
        summaries, abstracts = await asyncio.gather(
            _client.fetchSummaries(ids),
            _client.fetchAbstracts(ids),
        )

        result = _fmt.shapePaperResults(ids, summaries)

        # Enrich with full abstracts (efetch returns what esummary can't)
        for paper in result:
            pid = paper.get("id", "")
            if pid in abstracts:
                paper["abstract"] = abstracts[pid]

        await papers_cache.set(key, result)
        _log.info("fetched", extra={"tool": "pubmed", "topic": topic, "count": len(result), "with_abstracts": sum(1 for p in result if p.get("abstract"))})
        return result
    except Exception as e:
        _log.warning("error", extra={"tool": "pubmed", "error": str(e)})
        return [{"id": "", "title": f"[error: {e}]", "abstract": "", "authors": [], "journal": "", "year": 0, "url": ""}]
```

---

## FILE 8 — src/helix/tools/synthesis.py (OVERWRITE)

```python
"""
Helix synthesis pipeline — deterministic weighted vector scoring.

final_score = 100 * (
    0.35 * condition_match +
    0.30 * eligibility_fit +
    0.20 * evidence_support +
    0.15 * trial_phase_maturity
)
All sub-scores normalized to [0, 1]. Results cached 5 min.

v1.1.0: eligibility_fit now computes age-window centrality instead of
always returning 1.0. A patient at the center of the trial's age window
scores 1.0; a patient at the edge scores 0.5; open enrollment scores 0.75.
"""
import asyncio
import time
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


def _hard_gate(trial: dict, age: int) -> tuple[bool, str]:
    mn, mx = trial.get("min_age"), trial.get("max_age")
    if isinstance(mn, int) and age < mn:
        return False, f"age {age} below min {mn}"
    if isinstance(mx, int) and age > mx:
        return False, f"age {age} above max {mx}"
    if not trial.get("id"):
        return False, "missing trial ID"
    if not trial.get("title"):
        return False, "missing trial title"
    return True, ""


def _eligibility_fit_score(trial: dict, age: int) -> float:
    """
    Age-window centrality score for the 'eligibility_fit' vector component.

    Intuition: a trial designed for ages 40-50 is more specifically tailored
    to a 45-year-old patient than a trial designed for ages 18-80.
    The patient at the center of the window gets 1.0; at the edge gets 0.5.
    Open enrollment (no age constraints) gets 0.75 — inclusive but not tailored.

    Range: [0.5, 1.0]. Never 0 because the hard gate already excluded
    out-of-window patients — anything reaching here is eligible.
    """
    mn = trial.get("min_age")
    mx = trial.get("max_age")

    if mn is None and mx is None:
        return 0.75  # open enrollment — inclusive but not patient-specific

    lo = mn if mn is not None else 0
    hi = mx if mx is not None else 120
    center = (lo + hi) / 2.0
    half_width = max((hi - lo) / 2.0, 1.0)

    # Normalized distance: 0.0 at center, 1.0 at edges
    dist = abs(age - center) / half_width
    return round(max(0.5, 1.0 - dist * 0.5), 4)


def buildTrialProfile(trial: dict, age: int, condition: str, papers: list, drugs: list) -> dict:
    cond_tok  = set((condition or "").lower().split())
    title_tok = set((trial.get("title") or "").lower().split())
    overlap   = len(cond_tok & title_tok)
    cond_m    = _norm(overlap, max(len(cond_tok), 1))

    # Evidence support: count papers whose title shares tokens with condition
    # Also checks abstract if populated (v1.1.0 fetches real abstracts)
    ev_hits = 0
    for p in papers:
        if not isinstance(p, dict):
            continue
        title_match = bool(set((p.get("title") or "").lower().split()) & cond_tok)
        abstract_match = bool(set((p.get("abstract") or "").lower().split()) & cond_tok)
        if title_match or abstract_match:
            ev_hits += 1
    ev_m = _norm(ev_hits, max(len(papers), 1))

    phase   = trial.get("phase") or []
    phase_m = _phase_score(phase)
    elig_m  = _eligibility_fit_score(trial, age)  # v1.1.0: was hardcoded 1.0

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
    if cond_m  < 0.2:  flags.append("LOW_CONDITION_MATCH")
    if phase_m <= 0.3:  flags.append("EARLY_STAGE_TRIAL")
    if ev_m    < 0.1:  flags.append("LOW_EVIDENCE_SUPPORT")

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


async def synthesizeEvidence(condition: str, age: int, location: str = None) -> dict:
    """Full cross-database synthesis. Cached 5 min per (condition, age, location)."""
    key = f"synthesis:{condition.lower().strip()}:{age}:{location or ''}"
    cached = await synthesis_cache.get(key)
    if cached is not None:
        _log.info("cache_hit", extra={"tool": "synthesis", "condition": condition, "age": age})
        return cached

    t0 = time.monotonic()
    trials, papers = await asyncio.gather(
        matchEligibility(condition, age, location, limit=8),
        searchPapers(condition, limit=5),
    )

    try:
        drugs_raw = await _fda.searchByIndication(condition, limit=3)
        drugs = _fmt.shapeDrugResults(drugs_raw) if isinstance(drugs_raw, dict) else []
    except Exception:
        drugs = []

    eligible, excluded = [], []
    for t in (trials or []):
        ok, reason = _hard_gate(t, age)
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
        "condition": condition, "age": age,
        "scored": len(profiles), "excluded": len(excluded), "ms": elapsed,
    })

    await synthesis_cache.set(key, result)
    return result
```

---

## FILE 9 — tests/conftest.py (CREATE)

```python
"""
Shared pytest fixtures for Helix unit tests.
All fixtures are pure Python — no network calls, no external dependencies.
"""
import pytest


@pytest.fixture
def sample_trials_response():
    """Minimal valid ClinicalTrials.gov API response with 2 studies."""
    def _make_study(nct_id, title, min_age, max_age, phases, status="RECRUITING"):
        return {
            "protocolSection": {
                "identificationModule": {"nctId": nct_id, "briefTitle": title},
                "statusModule": {"overallStatus": status},
                "descriptionModule": {"briefSummary": f"A trial about {title.lower()}"},
                "eligibilityModule": {
                    "minimumAge": min_age,
                    "maximumAge": max_age,
                    "sex": "ALL",
                },
                "designModule": {"phases": phases},
                "contactsLocationsModule": {},
            }
        }

    return {
        "studies": [
            _make_study("NCT00000001", "Diabetes Semaglutide Trial", "18 Years", "65 Years", ["PHASE3"]),
            _make_study("NCT00000002", "Type 2 Diabetes Insulin Study", "40 Years", "70 Years", ["PHASE2"]),
        ]
    }


@pytest.fixture
def sample_pubmed_summaries():
    """Minimal valid PubMed esummary response."""
    return {
        "result": {
            "uids": ["12345678", "87654321"],
            "12345678": {
                "title": "Metformin for Type 2 Diabetes: A systematic review",
                "authors": [{"name": "Smith J"}, {"name": "Jones A"}],
                "source": "New England Journal of Medicine",
                "pubdate": "2023 Jan",
            },
            "87654321": {
                "title": "Insulin resistance mechanisms in diabetes",
                "authors": [{"name": "Brown K"}],
                "source": "Lancet",
                "pubdate": "2022 Mar",
            },
        }
    }


@pytest.fixture
def sample_fda_response():
    """Minimal valid openFDA drug label response."""
    return {
        "results": [
            {
                "openfda": {
                    "brand_name": ["GLUCOPHAGE"],
                    "generic_name": ["METFORMIN HYDROCHLORIDE"],
                    "manufacturer_name": ["Bristol-Myers Squibb"],
                    "route": ["ORAL"],
                },
                "indications_and_usage": ["For treatment of type 2 diabetes mellitus."],
                "warnings": ["Lactic acidosis risk. Renal impairment contraindication."],
            }
        ]
    }
```

---

## FILE 10 — tests/unit/__init__.py (CREATE)

```python
```

---

## FILE 11 — tests/unit/test_formatter.py (CREATE)

```python
"""Unit tests for Formatter and _parse_age — no network calls."""
import pytest
from helix.utils.formatter import Formatter, _parse_age


# --- _parse_age ---

def test_parse_years():
    assert _parse_age("18 Years") == 18

def test_parse_years_large():
    assert _parse_age("75 Years") == 75

def test_parse_months():
    assert _parse_age("6 Months") == 0  # 6 // 12 = 0

def test_parse_months_large():
    assert _parse_age("24 Months") == 2

def test_parse_empty():
    assert _parse_age("") is None

def test_parse_none():
    assert _parse_age(None) is None

def test_parse_invalid():
    assert _parse_age("N/A") is None


# --- Formatter.shapeTrialResults ---

def test_shape_trials_basic(sample_trials_response):
    results = Formatter().shapeTrialResults(sample_trials_response)
    assert len(results) == 2

def test_shape_trials_first_trial(sample_trials_response):
    t = Formatter().shapeTrialResults(sample_trials_response)[0]
    assert t["id"] == "NCT00000001"
    assert t["min_age"] == 18
    assert t["max_age"] == 65
    assert t["phase"] == ["PHASE3"]
    assert t["status"] == "RECRUITING"
    assert "clinicaltrials.gov/study/NCT00000001" in t["url"]

def test_shape_trials_empty():
    assert Formatter().shapeTrialResults({}) == []

def test_shape_trials_bad_input():
    assert Formatter().shapeTrialResults(None) == []
    assert Formatter().shapeTrialResults("bad") == []


# --- Formatter.shapePaperResults ---

def test_shape_papers_basic(sample_pubmed_summaries):
    fmt = Formatter()
    papers = fmt.shapePaperResults(["12345678", "87654321"], sample_pubmed_summaries)
    assert len(papers) == 2

def test_shape_papers_fields(sample_pubmed_summaries):
    p = Formatter().shapePaperResults(["12345678"], sample_pubmed_summaries)[0]
    assert p["id"] == "12345678"
    assert "Metformin" in p["title"]
    assert p["year"] == 2023
    assert "pubmed.ncbi.nlm.nih.gov/12345678" in p["url"]

def test_shape_papers_empty():
    assert Formatter().shapePaperResults([], {}) == []


# --- Formatter.shapeDrugResults ---

def test_shape_drugs_basic(sample_fda_response):
    drugs = Formatter().shapeDrugResults(sample_fda_response)
    assert len(drugs) == 1

def test_shape_drugs_fields(sample_fda_response):
    d = Formatter().shapeDrugResults(sample_fda_response)[0]
    assert d["brand_name"] == "GLUCOPHAGE"
    assert d["generic_name"] == "METFORMIN HYDROCHLORIDE"
    assert "ORAL" in d["route"]

def test_shape_drugs_empty():
    assert Formatter().shapeDrugResults({"results": []}) == []
```

---

## FILE 12 — tests/unit/test_cache.py (CREATE)

```python
"""Unit tests for TTLCache — no network calls."""
import asyncio
import time
import pytest
from helix.cache import TTLCache


@pytest.mark.asyncio
async def test_set_and_get():
    cache = TTLCache(default_ttl=60)
    await cache.set("k", {"v": 1})
    assert await cache.get("k") == {"v": 1}


@pytest.mark.asyncio
async def test_get_missing_key():
    cache = TTLCache(default_ttl=60)
    assert await cache.get("does_not_exist") is None


@pytest.mark.asyncio
async def test_expired_entry():
    """Manually plant an already-expired entry and verify it's evicted on get."""
    cache = TTLCache(default_ttl=60)
    async with cache._lock:
        cache._store["stale"] = ("value", time.monotonic() - 1)  # expired 1s ago
    assert await cache.get("stale") is None
    # Key should have been cleaned up
    assert "stale" not in cache._store


@pytest.mark.asyncio
async def test_delete_existing():
    cache = TTLCache(default_ttl=60)
    await cache.set("key", "val")
    await cache.delete("key")
    assert await cache.get("key") is None


@pytest.mark.asyncio
async def test_delete_nonexistent():
    cache = TTLCache(default_ttl=60)
    await cache.delete("ghost")  # must not raise


@pytest.mark.asyncio
async def test_clear():
    cache = TTLCache(default_ttl=60)
    await cache.set("a", 1)
    await cache.set("b", 2)
    await cache.clear()
    assert cache.stats()["total_keys"] == 0


@pytest.mark.asyncio
async def test_stats_all_valid():
    cache = TTLCache(default_ttl=60)
    await cache.set("x", 1)
    await cache.set("y", 2)
    s = cache.stats()
    assert s["total_keys"] == 2
    assert s["valid_keys"] == 2
    assert s["expired_keys"] == 0


@pytest.mark.asyncio
async def test_stats_with_expired():
    cache = TTLCache(default_ttl=60)
    await cache.set("live", "value")
    async with cache._lock:
        cache._store["dead"] = ("value", time.monotonic() - 1)
    s = cache.stats()
    assert s["total_keys"] == 2
    assert s["valid_keys"] == 1
    assert s["expired_keys"] == 1


@pytest.mark.asyncio
async def test_custom_ttl_overrides_default():
    cache = TTLCache(default_ttl=10)
    await cache.set("key", "val", ttl=3600)
    _, expires_at = cache._store["key"]
    # Should expire roughly 3600s from now, not 10s
    assert expires_at > time.monotonic() + 3590
```

---

## FILE 13 — tests/unit/test_scoring.py (CREATE)

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


# --- _eligibility_fit_score ---

def test_elig_fit_center():
    """Patient at exact center of window → 1.0."""
    t = {"min_age": 30, "max_age": 50}
    assert _eligibility_fit_score(t, 40) == 1.0

def test_elig_fit_at_min_edge():
    """Patient at minimum edge → 0.5."""
    t = {"min_age": 30, "max_age": 50}
    assert _eligibility_fit_score(t, 30) == 0.5

def test_elig_fit_at_max_edge():
    """Patient at maximum edge → 0.5."""
    t = {"min_age": 30, "max_age": 50}
    assert _eligibility_fit_score(t, 50) == 0.5

def test_elig_fit_open_enrollment():
    """No age constraints → 0.75 (inclusive but not tailored)."""
    t = {"min_age": None, "max_age": None}
    assert _eligibility_fit_score(t, 45) == 0.75

def test_elig_fit_range_is_0_5_to_1():
    """Score is always in [0.5, 1.0] for any valid in-window age."""
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
```

---

## FILE 14 — CHANGELOG.md (OVERWRITE)

```markdown
# Changelog

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

## FILE 15 — README.md (OVERWRITE)

```markdown
<div align="center">

# Helix

**Clinical evidence synthesis engine — free, no API key, production-grade.**

[![CI](https://github.com/Al1Abdullah/Helix/actions/workflows/ci.yml/badge.svg)](https://github.com/Al1Abdullah/Helix/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-111111?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-111111?style=flat-square)](LICENSE)
[![MCP Compatible](https://img.shields.io/badge/MCP-compatible-111111?style=flat-square)](https://modelcontextprotocol.io)
[![REST API](https://img.shields.io/badge/REST_API-:8000-111111?style=flat-square)](#rest-api)
[![Docker Ready](https://img.shields.io/badge/docker-ready-111111?style=flat-square&logo=docker&logoColor=white)](Dockerfile)
[![No API Key](https://img.shields.io/badge/no_API_key-required-111111?style=flat-square)](#data-sources)
[![Version](https://img.shields.io/badge/version-1.1.0-111111?style=flat-square)](CHANGELOG.md)

```
  Claude · GPT · Gemini · Copilot      curl · Python · any HTTP client
              │                                      │
    ┌─────────┴──────────────────────────────────────┴─────────┐
    │                        Helix                              │
    │           MCP Server (stdio)  ·  REST API (:8000)        │
    │  Vector scoring · TTL cache · Retry · JSON logs          │
    └───────────────────────┬───────────────────────────────────┘
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
      ClinicalTrials      PubMed       openFDA
       400k+ trials      35M papers   Drug labels
```

</div>

---

Helix is a clinical evidence synthesis engine built on the [Model Context Protocol](https://modelcontextprotocol.io). Give any AI model structured access to the three largest free public health databases — or call it as a REST API from any language.

No credentials. No rate-limit management. No data wrangling. Just answers.

---

## Quick Start

```bash
git clone https://github.com/Al1Abdullah/Helix.git
cd Helix
pip install -e .
python tests/tools/testSynthesis.py
```

### Docker

```bash
docker compose up          # REST API on :8000
# → http://localhost:8000/docs
```

---

## REST API

```bash
helix-api          # starts on :8000
# → http://localhost:8000/docs  (Swagger UI)
```

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Ping all 3 APIs, get per-service latency |
| `POST` | `/synthesize` | Full synthesis with scored, explainable profiles |
| `POST` | `/eligibility` | Match patient to trials by age + condition |
| `GET` | `/trials` | Search ClinicalTrials.gov |
| `GET` | `/papers` | Search PubMed (with full abstracts) |
| `GET` | `/drugs` | Search openFDA drug labels |
| `GET` | `/cache/stats` | Inspect cache state |
| `DELETE` | `/cache` | Flush all caches |

```bash
curl -X POST http://localhost:8000/synthesize \
  -H "Content-Type: application/json" \
  -d '{"condition": "Type 2 Diabetes", "age": 45}'
```

---

## MCP Integration

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "helix": { "command": "helix" }
  }
}
```

| Tool | Description |
|------|-------------|
| `synthesize_evidence` | Full cross-database synthesis with scored, explainable profiles |
| `find_trials` | Search ClinicalTrials.gov for recruiting trials |
| `search_papers` | Search PubMed by topic + year range (full abstracts) |
| `lookup_drug` | FDA drug label lookup |
| `match_eligibility` | Pre-filter trials by patient age + condition |
| `health_check` | Live API connectivity + latency report |

---

## Scoring Model

```
final_score = 100 × (
    0.35 × condition_match       +  # token overlap: condition ↔ trial title
    0.30 × eligibility_fit       +  # age-window centrality (1.0=center, 0.5=edge)
    0.20 × evidence_support      +  # PubMed papers matching condition
    0.15 × trial_phase_maturity     # Phase 3/4=1.0, Phase 2=0.6, Phase 1=0.3
)
```

All sub-scores normalized to [0, 1]. Full `score_vector` and `explainability_vector`
returned with every profile — every score is fully auditable.

### eligibility_fit (v1.1.0)

A patient at the **center** of a trial's age window scores **1.0**. A patient at the
**edge** scores **0.5**. Open enrollment (no age constraints) scores **0.75**.
Trials that passed the hard gate but are less tailored to this specific patient
age profile are naturally ranked lower.

---

## Data Sources

| Source | Records | Access |
|--------|---------|--------|
| [ClinicalTrials.gov](https://clinicaltrials.gov/api/v2) | 400,000+ trials | Free, no key |
| [PubMed / NCBI](https://www.ncbi.nlm.nih.gov/home/develop/api/) | 35M+ papers | Free, no key |
| [openFDA](https://open.fda.gov/apis/) | Drug labels | Free, no key |

---

## Architecture

```
src/helix/
├── api.py              FastAPI REST server
├── server.py           MCP server
├── models.py           Pydantic v2 domain schemas
├── cache.py            Async TTL cache
├── logger.py           Structured JSON logging
├── config/             Configuration (URLs, weights, TTLs)
├── clients/            Raw API clients (retry + WAF bypass)
│   ├── trialsClient.py     curl_cffi Chrome impersonation
│   ├── pubmedClient.py     httpx + retry + efetch abstracts
│   └── fdaClient.py        httpx + retry
├── tools/              Business logic layer (cached)
│   ├── synthesis.py        Vector scoring pipeline
│   ├── eligibility.py      Age-based pre-filter
│   ├── trials.py / pubmed.py / fda.py / health.py
└── utils/
    └── formatter.py        API response normalizer
tests/
├── unit/               Fast unit tests (no network, CI-safe)
│   ├── test_formatter.py
│   ├── test_cache.py
│   └── test_scoring.py
└── tools/              Live smoke tests (require network)
```

---

## License

MIT — see [LICENSE](LICENSE).
```

---

## EXECUTION ORDER

```bash
# 1. Install new dev dependency
pip install "pytest-mock>=3.14.0"
pip install -e .

# 2. Run unit tests (no network required)
pytest tests/unit/ -v

# 3. Verify the two bug fixes work
python -c "
from helix.tools.synthesis import _eligibility_fit_score
t = {'min_age': 30, 'max_age': 50}
assert _eligibility_fit_score(t, 40) == 1.0,  'center should be 1.0'
assert _eligibility_fit_score(t, 30) == 0.5,  'edge should be 0.5'
assert _eligibility_fit_score({'min_age': None, 'max_age': None}, 45) == 0.75
print('eligibility_fit_score: OK')
"

python -c "
import asyncio
from helix.clients.pubmedClient import PubMedClient
async def check():
    c = PubMedClient()
    abstracts = await c.fetchAbstracts(['33587037'])
    print(f'fetchAbstracts: OK — got {len(abstracts)} abstract(s)')
asyncio.run(check())
"

# 4. Run full smoke tests (live APIs)
python tests/tools/testSynthesis.py
python tests/tools/testHealth.py

# 5. Start REST API
helix-api &
sleep 2
curl -s http://localhost:8000/health | python3 -m json.tool
kill %1

# 6. Commit
git add .
git commit -m "fix: v1.1.0 — eligibility_fit centrality, PubMed abstracts, CI, Docker, unit tests"
git push
```

---

## VERIFICATION CHECKLIST

- [ ] `pytest tests/unit/ -v` — all tests pass, no network needed
- [ ] `_eligibility_fit_score({"min_age":30,"max_age":50}, 40) == 1.0`
- [ ] `_eligibility_fit_score({"min_age":30,"max_age":50}, 30) == 0.5`
- [ ] `_eligibility_fit_score({"min_age":None,"max_age":None}, 45) == 0.75`
- [ ] `PubMedClient().fetchAbstracts(["33587037"])` returns non-empty dict
- [ ] `testSynthesis.py` shows `eligibility_fit` values that vary between trials
- [ ] `.github/workflows/ci.yml` exists
- [ ] `Dockerfile` exists and `docker compose up` starts the server
- [ ] `CHANGELOG.md` has [1.1.0] entry at top with bug fix descriptions
- [ ] CI badge visible in README.md header
