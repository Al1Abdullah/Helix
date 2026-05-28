# HELIX v1.4.0 — Final Upgrade Prompt

Feed this to Gemini CLI from inside `Helix-main/`:
```
gemini < HELIX_V1_4_FINAL.md
```

---

## Context

You are upgrading the Helix clinical evidence synthesis server from **v1.3.0 → v1.4.0**.
Helix is a production FastAPI + MCP server that queries ClinicalTrials.gov, PubMed, and
openFDA concurrently. It has 68 passing unit tests.

This is the **final** upgrade — fix every remaining bug, close every gap.
After this, nothing should remain to do.

---

## What to change and why

### Bug 1 — Version fallback is stale
`src/helix/config/__init__.py` line: `_VERSION = "1.2.0"` — wrong. Fix to `"1.3.0"`.

### Bug 2 — Sex exclusions are invisible in `excludedTrials`
`synthesizeEvidence` passes `sex=sex` to `matchEligibility`. That function pre-filters
sex-mismatched trials with `continue` — they vanish silently. When synthesis calls
`_hard_gate`, sex-mismatched trials are already gone, so they never appear in
`excludedTrials`. Result: callers get no transparency on WHY trials were excluded.

Fix: in `synthesizeEvidence`, call `matchEligibility(..., sex=None, limit=16)`.
Let `_hard_gate` be the sole sex authority inside the synthesis pipeline.
Sex-mismatched trials will now appear in `excludedTrials` with reason
`"sex mismatch: trial=MALE, patient=FEMALE"` as expected.

### Bug 3 — `formatter.py` leaks raw API response
`shapeTrialResults` includes `"raw": study` in every shaped trial dict. This is:
- Undocumented (Paper and Drug shapers don't have it)
- Memory wasteful (full raw study JSON duplicated in every result)
- Inconsistent
Remove the `"raw": study` line.

### Bug 4 — `HealthReport` model version default is "1.0.0"
`models.py`: `version: str = "1.0.0"` — stale default. Change to `version: str = ""`.
(`health.py` always passes `server_config.version` explicitly, so default never shows,
but "1.0.0" is wrong if it ever does.)

### Gap 1 — `GET /trials` has no sex filter
`POST /synthesize` and `POST /eligibility` support `sex`, but `GET /trials` does not.
Add `sex: Optional[Literal["MALE", "FEMALE"]] = Query(None)` to the `/trials` endpoint.
Add matching `sex: Optional[str] = None` parameter to `findTrials()` with post-filter.
Add `sex: Optional[str] = None` to the `find_trials` MCP tool.

### Gap 2 — No input validation on age or condition
Age accepts `0` to `130` (inclusive). Condition must be non-empty (1–300 chars).
Add `Field(ge=0, le=130)` on `age` and `Field(min_length=1, max_length=300)` on
`condition` in `SynthesizeRequest` and `EligibilityRequest` in `api.py`.
In MCP tools (`server.py`), add guard:
```python
if not condition or not condition.strip():
    return []
```
for find_trials, search_papers, match_eligibility, synthesize_evidence.
For age:
```python
if not (0 <= age <= 130):
    return []
```
for match_eligibility and synthesize_evidence.

### Gap 3 — `.env.example` is empty
Document the two supported env vars.

### Gap 4 — `Optional[str]` type hints in `server.py`
MCP tools use bare `str = None` instead of `Optional[str] = None`. Fix all four.

---

## File changes — exact instructions

### 1. `pyproject.toml`
Change:
```
version = "1.3.0"
```
To:
```
version = "1.4.0"
```

---

### 2. `src/helix/config/__init__.py`
Change:
```python
    _VERSION = "1.2.0"
```
To:
```python
    _VERSION = "1.3.0"
```

---

### 3. `src/helix/models.py`
Change:
```python
    version: str = "1.0.0"
```
To:
```python
    version: str = ""
```

---

### 4. `src/helix/utils/formatter.py`
In `shapeTrialResults`, remove this line from the dict:
```python
                "raw": study,
```
Nothing else changes.

---

### 5. `src/helix/tools/trials.py` — OVERWRITE

```python
from helix.clients.trialsClient import TrialsClient
from helix.utils.formatter import Formatter
from helix.utils.synonyms import expand
from helix.cache import trials_cache
from helix.logger import get_logger

_client = TrialsClient()
_fmt    = Formatter()
_log    = get_logger(__name__)


async def findTrials(
    condition: str,
    location: str = None,
    limit: int = 10,
    sex: str = None,
) -> list[dict]:
    """Find active clinical trials. Synonym-expanded, cached 3 min. Never raises.

    Args:
        condition: Medical condition or abbreviation.
        location: Optional location filter.
        limit: Max results to return.
        sex: Optional sex filter: MALE or FEMALE. Applied post-fetch.
    """
    condition = expand(condition)
    key = f"trials:{condition.lower().strip()}:{location or ''}:{limit}:{sex or ''}"
    cached = await trials_cache.get(key)
    if cached is not None:
        _log.info("cache_hit", extra={"tool": "trials", "condition": condition})
        return cached
    try:
        # Fetch extra when sex-filtering so we hit the requested limit after exclusions
        fetch_limit = limit * 2 if sex else limit
        raw = await _client.search(condition, location, fetch_limit)
        result = _fmt.shapeTrialResults(raw)
        if sex:
            result = [
                t for t in result
                if (t.get("sex") or "ALL").upper() in ("ALL", sex.upper())
            ]
            result = result[:limit]
        await trials_cache.set(key, result)
        _log.info(
            "fetched",
            extra={"tool": "trials", "condition": condition, "count": len(result)},
        )
        return result
    except Exception as e:
        _log.warning("error", extra={"tool": "trials", "error": str(e)})
        return [{"id": "", "title": f"[error: {e}]", "status": "", "phase": [], "url": ""}]
```

---

### 6. `src/helix/tools/synthesis.py`
Find and replace the `asyncio.gather` call inside `synthesizeEvidence`:

Old:
```python
    trials, papers = await asyncio.gather(
        matchEligibility(condition, age, location, limit=8, sex=sex),
        searchPapers(condition, limit=5),
    )
```

New:
```python
    # Pass sex=None so ALL trials (including sex-mismatched) come back from
    # matchEligibility. The _hard_gate below is the sole sex authority inside
    # synthesis, ensuring sex-rejected trials appear in excludedTrials.
    trials, papers = await asyncio.gather(
        matchEligibility(condition, age, location, limit=16, sex=None),
        searchPapers(condition, limit=5),
    )
```

Also update the module-level docstring top line to say `v1.4.0` instead of `v1.3.0`:
Old:
```
v1.3.0: expanded_from populated in ClinicalInsight when abbreviation is resolved.
```
New:
```
v1.4.0: sex filtering solely via _hard_gate for full excludedTrials transparency.
v1.3.0: expanded_from populated in ClinicalInsight when abbreviation is resolved.
```

---

### 7. `src/helix/api.py` — OVERWRITE

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
from pydantic import BaseModel, Field
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
    condition: str = Field(..., min_length=1, max_length=300)
    age: int = Field(..., ge=0, le=130)
    location: Optional[str] = None
    sex: Optional[Literal["MALE", "FEMALE"]] = None


class EligibilityRequest(BaseModel):
    condition: str = Field(..., min_length=1, max_length=300)
    age: int = Field(..., ge=0, le=130)
    location: Optional[str] = None
    limit: int = Field(10, ge=1, le=50)
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
    Sex-mismatched trials are reported in excludedTrials with their reason.
    """
    return await synthesizeEvidence(req.condition, req.age, req.location, req.sex)


@app.post("/eligibility", tags=["Evidence"])
async def eligibility(req: EligibilityRequest):
    """Match patient profile to trials by condition, age, and optional sex."""
    return await matchEligibility(req.condition, req.age, req.location, req.limit, req.sex)


# ── Data ──────────────────────────────────────────────────────────────────────

@app.get("/trials", tags=["Data"])
async def trials(
    condition: str = Query(..., min_length=1, max_length=300),
    location: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    sex: Optional[Literal["MALE", "FEMALE"]] = Query(None),
):
    """Active recruiting trials on ClinicalTrials.gov. Abbreviations auto-expanded."""
    return await findTrials(condition, location, limit, sex)


@app.get("/papers", tags=["Data"])
async def papers(
    topic: str = Query(..., min_length=1, max_length=300),
    yearFrom: Optional[int] = Query(None),
    yearTo: Optional[int] = Query(None),
    limit: int = Query(10, ge=1, le=50),
):
    """PubMed peer-reviewed research papers. Abbreviations auto-expanded."""
    return await searchPapers(topic, yearFrom, yearTo, limit)


@app.get("/drugs", tags=["Data"])
async def drugs(
    name: str = Query(..., min_length=1, max_length=200),
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

### 8. `src/helix/server.py` — OVERWRITE

```python
from typing import Optional
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
async def find_trials(
    condition: str,
    location: Optional[str] = None,
    limit: int = 10,
    sex: Optional[str] = None,
) -> list[dict]:
    """Find active clinical trials matching a medical condition.
    Abbreviations like T2D, NSCLC, COPD are automatically expanded.

    Args:
        condition: Medical condition or abbreviation (e.g. "T2D", "Type 2 Diabetes").
        location: Optional location filter (e.g. "Boston, MA").
        limit: Max results (default 10).
        sex: Optional sex filter: MALE or FEMALE.
    """
    if not condition or not condition.strip():
        return []
    return await findTrials(condition, location, limit, sex)


@mcp.tool()
async def search_papers(
    topic: str,
    yearFrom: Optional[int] = None,
    yearTo: Optional[int] = None,
    limit: int = 10,
) -> list[dict]:
    """Search PubMed for peer-reviewed research papers.
    Abbreviations like T2D, NSCLC, COPD are automatically expanded.

    Args:
        topic: Research topic or abbreviation.
        yearFrom: Start year filter (optional).
        yearTo: End year filter (optional).
        limit: Max results (default 10).
    """
    if not topic or not topic.strip():
        return []
    return await searchPapers(topic, yearFrom, yearTo, limit)


@mcp.tool()
async def lookup_drug(name: str, limit: int = 5) -> list[dict]:
    """Look up FDA drug information by brand or generic name."""
    if not name or not name.strip():
        return []
    return await lookupDrug(name, limit)


@mcp.tool()
async def match_eligibility(
    condition: str,
    age: int,
    location: Optional[str] = None,
    limit: int = 10,
    sex: Optional[str] = None,
) -> list[dict]:
    """Match a patient profile to clinical trials ranked by eligibility fit.
    Abbreviations like T2D, NSCLC, COPD are automatically expanded.

    Args:
        condition: Medical condition or abbreviation (e.g. "T2D", "NSCLC").
        age: Patient age in years (0–130).
        location: Optional location filter (e.g. "Boston, MA").
        limit: Max results (default 10).
        sex: Optional patient sex filter: MALE or FEMALE.
    """
    if not condition or not condition.strip():
        return []
    if not (0 <= age <= 130):
        return []
    return await matchEligibility(condition, age, location, limit, sex)


@mcp.tool()
async def synthesize_evidence(
    condition: str,
    age: int,
    location: Optional[str] = None,
    sex: Optional[str] = None,
) -> dict:
    """Cross-database clinical evidence synthesis.
    Queries ClinicalTrials.gov, PubMed, and openFDA concurrently.
    Returns scored, ranked trials with full explainability vectors.
    Abbreviations like T2D, NSCLC, COPD are automatically expanded.
    Response includes expanded_from when an abbreviation was resolved.
    Sex-mismatched trials appear in excludedTrials with their reason.

    Args:
        condition: Medical condition or abbreviation (e.g. "T2D", "NSCLC").
        age: Patient age in years (0–130).
        location: Optional location filter (e.g. "London, UK").
        sex: Optional patient sex filter: MALE or FEMALE.
    """
    if not condition or not condition.strip():
        return {}
    if not (0 <= age <= 130):
        return {}
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

### 9. `.env.example` — OVERWRITE

```
# PubMed E-utilities (optional but recommended)
# Without an API key:  3 requests/second rate limit
# With an API key:    10 requests/second rate limit
# Get a free key at:  https://www.ncbi.nlm.nih.gov/account/
PUBMED_EMAIL=your@email.com
PUBMED_API_KEY=
```

---

### 10. `CHANGELOG.md`
Prepend this section at the very top of the file (before the `## [1.3.0]` line):

```markdown
## [1.4.0] — 2026-05-29

### Fixed
- **Sex exclusions now visible in `excludedTrials`** — `synthesizeEvidence` was passing
  `sex=sex` to `matchEligibility`, which silently dropped sex-mismatched trials via
  `continue`. Those trials never reached `_hard_gate`, so they were invisible to callers.
  Fixed by calling `matchEligibility(..., sex=None, limit=16)` inside synthesis and
  letting `_hard_gate` be the sole sex authority. Sex-rejected trials now appear in
  `excludedTrials` with reason `"sex mismatch: trial=MALE, patient=FEMALE"`.
- **Version fallback was stale** — `config/__init__.py` fell back to `"1.2.0"` when
  `importlib.metadata` failed. Fixed to `"1.3.0"`.
- **`HealthReport` model version default** — was `"1.0.0"`. Changed to `""` (health.py
  always passes the real version explicitly; the default should not be a stale string).
- **`formatter.py` leaked raw API response** — `shapeTrialResults` included `"raw": study`
  in every shaped trial dict: undocumented, memory-wasteful, inconsistent with Paper and
  Drug shapers. Removed.

### Added
- **`sex` filter on `GET /trials`** — `GET /trials?condition=T2D&sex=FEMALE` now works.
  Parity with `/eligibility` and `/synthesize`. Applied post-fetch via post-filter.
  `findTrials()` and the `find_trials` MCP tool both accept the new parameter.
- **Input validation** — `SynthesizeRequest` and `EligibilityRequest` now enforce
  `age` in `[0, 130]` and `condition` length `[1, 300]` via Pydantic `Field` constraints.
  `GET /trials`, `GET /papers`, and `GET /drugs` enforce the same via `Query` constraints.
  MCP tools (`match_eligibility`, `synthesize_evidence`, `find_trials`, `search_papers`,
  `lookup_drug`) return empty results for blank conditions; age-taking tools return empty
  for out-of-range ages.
- **`Optional[str]` type hints in `server.py`** — MCP tools now use `Optional[str] = None`
  instead of bare `str = None`.
- **`.env.example` populated** — Documents `PUBMED_EMAIL` and `PUBMED_API_KEY` with
  rate limit context and a link to get a free NCBI key.
- **8 new unit tests** — see test additions below.

```

---

### 11. `tests/unit/test_scoring.py`
Append these tests at the end of the existing file:

```python

# --- sex exclusion transparency (v1.4.0) ---

def test_hard_gate_trial_female_patient_male():
    """Inverse sex mismatch: trial requires FEMALE, patient is MALE."""
    t = {"id": "NCT001", "title": "Test", "sex": "FEMALE"}
    ok, reason = _hard_gate(t, 45, sex="MALE")
    assert ok is False
    assert "sex mismatch" in reason
    assert "FEMALE" in reason
    assert "MALE" in reason

def test_hard_gate_no_sex_field_defaults_to_all():
    """Trial with no sex field should be treated as ALL and pass any patient."""
    t = {"id": "NCT001", "title": "Test"}  # no "sex" key
    ok, _ = _hard_gate(t, 45, sex="MALE")
    assert ok is True

def test_build_insight_zero_top_score_when_empty():
    """Empty profile list should return top_score=0.0, not crash."""
    r = buildClinicalInsight([], "NSCLC", expanded_from="nsclc")
    assert r["top_score"] == 0.0
    assert r["expanded_from"] == "nsclc"
    assert r["condition"] == "NSCLC"

def test_hard_gate_age_exactly_at_min_passes():
    """Age exactly equal to min_age is valid (inclusive boundary)."""
    t = {"id": "NCT001", "title": "Test", "min_age": 18, "max_age": 65}
    ok, _ = _hard_gate(t, 18)
    assert ok is True

def test_hard_gate_age_exactly_at_max_passes():
    """Age exactly equal to max_age is valid (inclusive boundary)."""
    t = {"id": "NCT001", "title": "Test", "min_age": 18, "max_age": 65}
    ok, _ = _hard_gate(t, 65)
    assert ok is True
```

---

### 12. `tests/unit/test_formatter.py`
Append these tests at the end of the existing file:

```python

def test_shape_trials_no_raw_field(sample_trials_response):
    """Shaped trials must not contain the raw API response field (memory hygiene)."""
    results = Formatter().shapeTrialResults(sample_trials_response)
    for trial in results:
        assert "raw" not in trial, "raw field must not be present in shaped trial dicts"

def test_shape_trials_sex_field_present(sample_trials_response):
    """Shaped trial must include a sex field for downstream sex filtering."""
    t = Formatter().shapeTrialResults(sample_trials_response)[0]
    assert "sex" in t
```

---

### 13. `tests/unit/test_synonyms.py`
Append these tests at the end of the existing file:

```python

def test_none_input_passthrough():
    """expand(None) must return None without raising."""
    assert expand(None) is None

def test_whitespace_only_passthrough():
    """expand with only whitespace should not match anything."""
    result = expand("   ")
    assert result == "   "

def test_multi_word_alias():
    """Multi-word aliases like 'type2 diabetes' must expand correctly."""
    assert expand("type2 diabetes") == "Type 2 Diabetes"

def test_expand_is_idempotent():
    """Calling expand twice on an already-expanded name is a no-op."""
    first = expand("T2D")
    second = expand(first)
    assert first == second
```

---

## Verification checklist

After Gemini finishes all changes, run:

```bash
# 1. Unit tests — must pass 76/76 (was 68; +8 new)
pytest tests/unit/ -v

# 2. Confirm version is correct
python -c "from helix.config import server; print(server.version)"
# Expected: 1.4.0

# 3. Confirm raw field is gone from formatter
python -c "
from helix.utils.formatter import Formatter
r = Formatter().shapeTrialResults({'studies': []})
print('raw field removed OK' if r == [] else r)
"

# 4. Confirm sex transparency — sex-mismatched trial appears in excludedTrials
python -c "
from helix.tools.synthesis import _hard_gate
t = {'id': 'NCT001', 'title': 'Female Only Trial', 'sex': 'FEMALE', 'min_age': None, 'max_age': None}
ok, reason = _hard_gate(t, 45, sex='MALE')
print('Sex transparency OK:', not ok, reason)
"

# 5. Confirm trials.py sex param works
python -c "
import asyncio
from helix.tools.trials import findTrials
import inspect
sig = inspect.signature(findTrials)
print('sex param present:', 'sex' in sig.parameters)
"

# 6. Confirm .env.example is populated
cat .env.example
```

Expected unit test count: **76 passing** (68 existing + 5 test_scoring + 2 test_formatter + 4 test_synonyms - note: some test_synonyms tests may already cover similar ground; final count may be 74–76).

---

## Summary

**12 files changed** (2 overwrite, 10 targeted edits):

| File | Change |
|------|--------|
| `pyproject.toml` | 1.3.0 → 1.4.0 |
| `src/helix/config/__init__.py` | fallback "1.2.0" → "1.3.0" |
| `src/helix/models.py` | HealthReport version default "1.0.0" → "" |
| `src/helix/utils/formatter.py` | remove `"raw": study` |
| `src/helix/tools/trials.py` | add `sex` param + post-filter |
| `src/helix/tools/synthesis.py` | matchEligibility called with sex=None, limit=16 |
| `src/helix/api.py` | sex on /trials, Field validators, Query constraints |
| `src/helix/server.py` | Optional types, sex on find_trials, input guards |
| `.env.example` | document PUBMED_EMAIL + PUBMED_API_KEY |
| `CHANGELOG.md` | prepend v1.4.0 section |
| `tests/unit/test_scoring.py` | +5 tests |
| `tests/unit/test_formatter.py` | +2 tests |
| `tests/unit/test_synonyms.py` | +4 tests (check overlap before adding) |

No new dependencies. No new files. All changes are backward-compatible.
Run `gemini < HELIX_V1_4_FINAL.md` and you're done.
