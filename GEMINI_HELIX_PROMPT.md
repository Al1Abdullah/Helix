# HELIX REFACTOR — COMPLETE ONE-SHOT EXECUTION PROMPT
# Feed this entire file to Gemini CLI. It will rewrite every broken file.
# Run from the repo root: Helix-main/

---

## CONTEXT

You are refactoring a Python MCP server called Helix. It connects AI models to ClinicalTrials.gov, PubMed, and openFDA. The repo root is the current directory. All file paths below are relative to it.

You must rewrite the files listed. Do NOT delete any file not listed. Do NOT change pyproject.toml or README.md. Do NOT add new dependencies beyond what is already in pyproject.toml (mcp, httpx, pydantic, python-dotenv).

---

## COMPLETE BUG AUDIT (every issue you must fix)

### BUG 1 — FATAL: Dual config conflict (ImportError on every import)
- `src/helix/config.py` (a file) AND `src/helix/config/` (a package directory) both exist.
- Python resolves the package directory, so `config.py` is shadowed but not removed, causing undefined behavior.
- `src/helix/server.py` does `from helix.config import server` → fails because `config/__init__.py` is empty.
- `src/helix/clients/pubmedClient.py` does `from helix.config import pubmed` → fails, same reason.
- FIX: Delete `src/helix/config.py`. Rewrite `src/helix/config/__init__.py` to export all config objects.

### BUG 2 — FATAL: FdaClient method name mismatch (AttributeError)
- `src/helix/clients/fdaClient.py` only defines `searchByIndication()`.
- `src/helix/tools/fda.py` calls `client.search(name, limit)` → AttributeError at runtime.
- FIX: Rename the method to `search()` in fdaClient, and keep `searchByIndication()` as an alias for synthesis.py which calls it directly.

### BUG 3 — FATAL: fdaClient and trialsClient use subprocess+curl (not async, crashes on bad JSON)
- Both clients use `subprocess.run(["curl", ...])` then `json.loads(result.stdout)`.
- `json.loads("")` raises JSONDecodeError when the API is down or rate-limited.
- Neither is truly async despite being called from async context.
- FIX: Rewrite both clients using `httpx.AsyncClient` (async/await). Wrap in try/except and return safe fallbacks.

### BUG 4 — FATAL: PubMed client uses synchronous httpx in async pipeline
- `pubmedClient.py` uses `httpx.Client` (sync) inside methods called from async code.
- FIX: Rewrite using `httpx.AsyncClient` with `async def` methods.

### BUG 5 — Schema mismatch: synthesis output keys don't match spec
- Current `buildTrialProfile` returns: `score`, `drivers`, `signals`, `riskFlags`
- Required schema is: `final_score`, `score_vector`, `explainability_vector`, `risk_flags`
- FIX: Rename all keys to match spec exactly.

### BUG 6 — Missing `excludedTrials` in synthesizeEvidence output
- Spec requires the output dict to have `"excludedTrials": [...]` listing trials rejected by hard eligibility filter.
- Currently all ineligible trials still get scored and included in trialProfiles.
- FIX: Split trials into eligible/ineligible BEFORE scoring. Include excludedTrials in output.

### BUG 7 — Missing `age_penalty` and `phase_penalty` in explainability_vector
- Spec requires explainability_vector with: `condition_overlap_raw`, `evidence_hits_raw`, `age_penalty`, `phase_penalty`
- Current `signals` dict only has `condition_overlap_raw` and `evidence_hits_raw`.
- FIX: Calculate and include age_penalty (float 0.0 or 1.0) and phase_penalty (float).

### BUG 8 — Age fields are strings in formatter but synthesis expects ints
- `formatter.shapeTrialResults()` stores `minimumAge: "18 Years"` (string from API).
- `synthesis.py`'s `buildTrialProfile` does `isinstance(min_age, int)` → always False → age filter never works.
- `eligibility.py` has `parseAge()` to fix this but formatter never calls it.
- FIX: Apply parseAge() inside `formatter.shapeTrialResults()` to store `min_age: int|None` and `max_age: int|None`.

### BUG 9 — Abstract field missing from paper schema
- Spec requires `Paper.abstract: str`.
- `formatter.shapePaperResults()` never populates `abstract`.
- PubMed esummary does not return full abstract text; use empty string `""` as safe default.
- FIX: Add `"abstract": ""` to each paper dict in shapePaperResults.

### BUG 10 — Double scoring: legacy scoreMatch() in eligibility conflicts with synthesis scoring
- `eligibility.py` scores trials with a legacy 0–100 integer formula and stores `matchScore`.
- `synthesis.py` does its own weighted vector scoring but stores `matchScore` in the trial dict first.
- The legacy score is never actually used in the final output.
- FIX: Keep `eligibility.py`'s `matchEligibility()` for basic age-based pre-filtering and initial ordering, but make clear it only does pre-filtering. The authoritative scoring happens in synthesis.py only.

### BUG 11 — testSynthesis.py uses wrong key names
- Accesses `t["score"]`, `t["riskFlags"]`, `t["drivers"]`, `t["signals"]`
- After fix, keys will be `final_score`, `risk_flags`, `score_vector`, `explainability_vector`
- FIX: Update test to use new key names and add safe `.get()` access everywhere.

### BUG 12 — server.py config import fails
- `from helix.config import server` → fails because config/__init__.py is empty.
- FIX: After fixing config/__init__.py, this import will work.

### BUG 13 — tools/fda.py is async wrapper but fdaClient was sync
- After converting fdaClient to async, tools/fda.py must await client.search().
- FIX: Update tools/fda.py to await the async client methods.

### BUG 14 — tools/trials.py is async but trialsClient.search() must now be awaited correctly
- After converting trialsClient to async, ensure await is used.
- FIX: Already async in tools/trials.py, just ensure client is now properly awaited.

### BUG 15 — synthesis.py calls fdaClient.searchByIndication directly (not through tools/fda.py)
- This bypasses error handling and schema normalization.
- FIX: Replace direct fdaClient call in synthesis.py with await on the async client, wrapped in try/except returning safe fallback.

---

## EXACT FILES TO CREATE/OVERWRITE

Overwrite or create each file below with EXACTLY the content shown. Use the file path as-is relative to the repo root.

---

### FILE 1: `src/helix/config/__init__.py`
OVERWRITE with:

```python
import os
from dotenv import load_dotenv

load_dotenv()


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


class ServerConfig:
    name: str = "Helix"
    version: str = "0.1.0"


trials = TrialsConfig()
pubmed = PubMedConfig()
fda = FdaConfig()
server = ServerConfig()
```

---

### FILE 2: `src/helix/config/fda.py`
OVERWRITE with:

```python
from helix.config import fda

baseUrl = fda.base_url
```

---

### FILE 3: `src/helix/config/pubmed.py`
OVERWRITE with:

```python
from helix.config import pubmed

baseUrl = pubmed.base_url
```

---

### FILE 4: `src/helix/config/trials.py`
OVERWRITE with:

```python
from helix.config import trials

baseUrl = trials.base_url
```

---

### FILE 5: `src/helix/config/weights.py`
OVERWRITE with:

```python
WEIGHTS = {
    "condition_match": 0.35,
    "eligibility_fit": 0.30,
    "evidence_support": 0.20,
    "trial_phase_maturity": 0.15,
}

# Sanity check — weights must sum to 1.0
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, "WEIGHTS must sum to 1.0"
```

---

### FILE 6: `src/helix/clients/fdaClient.py`
OVERWRITE with:

```python
import httpx
from helix.config import fda as fda_config

_SAFE_FALLBACK = {"results": [], "error": "no_data"}


class FdaClient:
    def __init__(self):
        self._base_url = fda_config.base_url
        self._headers = {"User-Agent": "Helix/1.0 (clinical trial research tool)"}

    async def search(self, name: str, limit: int = 5) -> dict:
        """Search FDA drug labels by brand or generic name."""
        query = name.replace(" ", "+")
        url = (
            f"{self._base_url}/label.json"
            f"?search=openfda.brand_name:{query}+openfda.generic_name:{query}"
            f"&limit={limit}"
        )
        return await self._get(url)

    async def searchByIndication(self, condition: str, limit: int = 5) -> dict:
        """Search FDA drug labels by indication (used in synthesis pipeline)."""
        query = f'"{condition}"'.replace(" ", "+")
        url = (
            f"{self._base_url}/label.json"
            f"?search=indications_and_usage:{query}"
            f"&limit={limit}"
        )
        return await self._get(url)

    async def _get(self, url: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, headers=self._headers)
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict):
                    return _SAFE_FALLBACK
                return data
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"results": [], "error": "not_found"}
            return {"results": [], "error": f"http_{e.response.status_code}"}
        except Exception:
            return _SAFE_FALLBACK
```

---

### FILE 7: `src/helix/clients/pubmedClient.py`
OVERWRITE with:

```python
import httpx
from helix.config import pubmed as pubmed_config


class PubMedClient:
    def __init__(self):
        self._base_url = pubmed_config.base_url
        self._headers = {"User-Agent": "Helix/1.0 (clinical trial research tool)"}

    async def search(
        self,
        topic: str,
        year_from: int = None,
        year_to: int = None,
        limit: int = 10,
    ) -> list[str]:
        """Search PubMed and return a list of article IDs."""
        query = topic
        if year_from and year_to:
            query += f" AND {year_from}:{year_to}[pdat]"
        elif year_from:
            query += f" AND {year_from}:3000[pdat]"

        params = {
            "db": "pubmed",
            "term": query,
            "retmax": limit,
            "retmode": "json",
            "email": pubmed_config.email,
        }
        if pubmed_config.api_key:
            params["api_key"] = pubmed_config.api_key

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    f"{self._base_url}/esearch.fcgi",
                    params=params,
                    headers=self._headers,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("esearchresult", {}).get("idlist", [])
        except Exception:
            return []

    async def fetchSummaries(self, ids: list[str]) -> dict:
        """Fetch metadata summaries for a list of PubMed IDs."""
        if not ids:
            return {}

        params = {
            "db": "pubmed",
            "id": ",".join(ids),
            "retmode": "json",
            "email": pubmed_config.email,
        }
        if pubmed_config.api_key:
            params["api_key"] = pubmed_config.api_key

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    f"{self._base_url}/esummary.fcgi",
                    params=params,
                    headers=self._headers,
                )
                response.raise_for_status()
                return response.json()
        except Exception:
            return {}
```

---

### FILE 8: `src/helix/clients/trialsClient.py`
OVERWRITE with:

```python
import httpx
from helix.config import trials as trials_config

_SAFE_FALLBACK = {"studies": []}


class TrialsClient:
    def __init__(self):
        self._base_url = trials_config.base_url
        self._headers = {"User-Agent": "Helix/1.0 (clinical trial research tool)"}

    async def search(
        self, condition: str, location: str = None, limit: int = 10
    ) -> dict:
        """Search ClinicalTrials.gov for recruiting trials matching a condition."""
        params = {
            "query.cond": condition,
            "filter.overallStatus": "RECRUITING,NOT_YET_RECRUITING",
            "pageSize": min(limit, trials_config.max_limit),
            "format": "json",
        }
        if location:
            params["query.locn"] = location

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    f"{self._base_url}/studies",
                    params=params,
                    headers=self._headers,
                )
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict):
                    return _SAFE_FALLBACK
                return data
        except Exception:
            return _SAFE_FALLBACK
```

---

### FILE 9: `src/helix/utils/formatter.py`
OVERWRITE with:

```python
def _parse_age(age_string: str) -> int | None:
    """Convert age strings like '18 Years' or '6 Months' to integer years."""
    if not age_string or not isinstance(age_string, str):
        return None
    lower = age_string.lower().strip()
    try:
        value = int(lower.split()[0])
        if "month" in lower:
            return max(value // 12, 0)
        return value
    except (ValueError, IndexError):
        return None


class Formatter:
    def shapeTrialResults(self, raw_response: dict) -> list[dict]:
        """Normalize raw ClinicalTrials.gov API response into canonical Trial dicts."""
        if not isinstance(raw_response, dict):
            return []

        studies = raw_response.get("studies", [])
        if not isinstance(studies, list):
            return []

        results = []
        for study in studies:
            if not isinstance(study, dict):
                continue

            protocol = study.get("protocolSection") or {}
            identification = protocol.get("identificationModule") or {}
            status = protocol.get("statusModule") or {}
            description = protocol.get("descriptionModule") or {}
            eligibility = protocol.get("eligibilityModule") or {}
            design = protocol.get("designModule") or {}
            contacts = protocol.get("contactsLocationsModule") or {}
            central_contacts = contacts.get("centralContacts") or []
            contact_info = central_contacts[0] if central_contacts else {}

            nct_id = identification.get("nctId") or ""
            min_age_raw = eligibility.get("minimumAge") or ""
            max_age_raw = eligibility.get("maximumAge") or ""

            results.append({
                # Canonical identifiers
                "id": nct_id,
                "title": identification.get("briefTitle") or "",
                # Status
                "status": status.get("overallStatus") or "",
                # Phase: list of strings e.g. ["PHASE3"]
                "phase": design.get("phases") or [],
                # Summary text (capped for token efficiency)
                "summary": (description.get("briefSummary") or "")[:500],
                # Age eligibility — parsed to int|None (canonical schema)
                "min_age": _parse_age(min_age_raw),
                "max_age": _parse_age(max_age_raw),
                # Keep raw string for display
                "min_age_raw": min_age_raw,
                "max_age_raw": max_age_raw,
                # Demographics
                "sex": eligibility.get("sex") or "ALL",
                # Contact
                "contact_name": contact_info.get("name") or "",
                "contact_email": contact_info.get("email") or "",
                # URL
                "url": f"https://clinicaltrials.gov/study/{nct_id}" if nct_id else "",
                # Raw for debug access (never crash on missing keys)
                "raw": study,
            })

        return results

    def shapePaperResults(self, ids: list, summaries: dict) -> list[dict]:
        """Normalize raw PubMed esummary response into canonical Paper dicts."""
        if not isinstance(summaries, dict) or not isinstance(ids, list):
            return []

        result_block = summaries.get("result") or {}
        uids = result_block.get("uids") or []

        papers = []
        for uid in uids:
            if not isinstance(uid, str):
                continue
            paper = result_block.get(uid) or {}
            if not isinstance(paper, dict):
                continue

            authors_raw = paper.get("authors") or []
            author_names = [
                a.get("name") or ""
                for a in authors_raw[:3]
                if isinstance(a, dict)
            ]

            pub_date = paper.get("pubdate") or ""
            year_str = pub_date[:4] if pub_date else ""
            try:
                year = int(year_str)
            except (ValueError, TypeError):
                year = 0

            papers.append({
                "id": uid,
                "title": paper.get("title") or "",
                # abstract: esummary does not return full text; empty string is safe default
                "abstract": "",
                "authors": author_names,
                "journal": paper.get("source") or "",
                "year": year,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
            })

        return papers

    def shapeDrugResults(self, raw_response: dict) -> list[dict]:
        """Normalize raw openFDA drug label response into canonical Drug dicts."""
        if not isinstance(raw_response, dict):
            return []

        results = raw_response.get("results") or []
        if not isinstance(results, list):
            return []

        shaped = []
        for drug in results:
            if not isinstance(drug, dict):
                continue

            openfda = drug.get("openfda") or {}
            brand_names = openfda.get("brand_name") or []
            generic_names = openfda.get("generic_name") or []
            manufacturers = openfda.get("manufacturer_name") or []
            indications_list = drug.get("indications_and_usage") or []
            warnings_list = drug.get("warnings") or []

            shaped.append({
                "brand_name": brand_names[0] if brand_names else "",
                "generic_name": generic_names[0] if generic_names else "",
                "manufacturer": manufacturers[0] if manufacturers else "",
                "route": openfda.get("route") or [],
                "indications": (indications_list[0][:300]) if indications_list else "",
                "warnings": (warnings_list[0][:300]) if warnings_list else "",
            })

        return shaped
```

---

### FILE 10: `src/helix/tools/eligibility.py`
OVERWRITE with:

```python
from helix.clients.trialsClient import TrialsClient
from helix.utils.formatter import Formatter

_client = TrialsClient()
_formatter = Formatter()


def _legacy_score(trial: dict, age: int, condition: str) -> int:
    """
    Lightweight pre-filter score (0–100 integer).
    Used ONLY for initial ranking before the synthesis pipeline runs.
    The authoritative scoring happens in synthesis.py (vector-based).
    Returns 0 if the patient is outside the age window (hard rejection).
    """
    min_age = trial.get("min_age")  # already int|None from formatter
    max_age = trial.get("max_age")  # already int|None from formatter

    if isinstance(min_age, int) and age < min_age:
        return 0
    if isinstance(max_age, int) and age > max_age:
        return 0

    score = 40
    cond_words = condition.lower().split()
    title = (trial.get("title") or "").lower()
    summary = (trial.get("summary") or "").lower()

    score += min(sum(1 for w in cond_words if w in title) * 15, 40)
    score += min(sum(1 for w in cond_words if w in summary) * 5, 20)

    phase = trial.get("phase") or []
    if any(p in ["PHASE3", "PHASE4"] for p in phase):
        score += 10

    return min(score, 100)


async def matchEligibility(
    condition: str, age: int, location: str = None, limit: int = 10
) -> list[dict]:
    """
    Fetch trials and return those passing basic age eligibility,
    ordered by lightweight pre-filter score descending.
    """
    raw = await _client.search(condition, location, limit * 2)
    trials = _formatter.shapeTrialResults(raw)

    scored = []
    for t in trials:
        s = _legacy_score(t, age, condition)
        if s > 0:
            scored.append({**t, "match_score_legacy": s})

    scored.sort(key=lambda x: x.get("match_score_legacy", 0), reverse=True)
    return scored[:limit]
```

---

### FILE 11: `src/helix/tools/pubmed.py`
OVERWRITE with:

```python
from helix.clients.pubmedClient import PubMedClient
from helix.utils.formatter import Formatter

_client = PubMedClient()
_formatter = Formatter()


async def searchPapers(
    topic: str,
    yearFrom: int = None,
    yearTo: int = None,
    limit: int = 10,
) -> list[dict]:
    """
    Search PubMed for research papers on a topic.
    Returns a list of canonical Paper dicts (never raises).
    """
    try:
        ids = await _client.search(topic, year_from=yearFrom, year_to=yearTo, limit=limit)
        if not ids:
            return []
        summaries = await _client.fetchSummaries(ids)
        return _formatter.shapePaperResults(ids, summaries)
    except Exception as err:
        return [{"id": "", "title": f"[search error: {err}]", "abstract": "", "authors": [], "journal": "", "year": 0, "url": ""}]
```

---

### FILE 12: `src/helix/tools/trials.py`
OVERWRITE with:

```python
from helix.clients.trialsClient import TrialsClient
from helix.utils.formatter import Formatter

_client = TrialsClient()
_formatter = Formatter()


async def findTrials(
    condition: str, location: str = None, limit: int = 10
) -> list[dict]:
    """
    Find active clinical trials for a condition.
    Returns a list of canonical Trial dicts (never raises).
    """
    try:
        raw = await _client.search(condition, location, limit)
        return _formatter.shapeTrialResults(raw)
    except Exception as err:
        return [{"id": "", "title": f"[search error: {err}]", "status": "", "phase": [], "url": ""}]
```

---

### FILE 13: `src/helix/tools/fda.py`
OVERWRITE with:

```python
from helix.clients.fdaClient import FdaClient
from helix.utils.formatter import Formatter

_client = FdaClient()
_formatter = Formatter()


async def lookupDrug(name: str, limit: int = 5) -> list[dict]:
    """
    Look up FDA drug information by brand or generic name.
    Returns a list of canonical Drug dicts (never raises).
    """
    try:
        raw = await _client.search(name, limit)
        if raw.get("error") or not raw.get("results"):
            return []
        return _formatter.shapeDrugResults(raw)
    except Exception as err:
        return [{"brand_name": "", "generic_name": f"[error: {err}]", "manufacturer": "", "route": [], "indications": "", "warnings": ""}]
```

---

### FILE 14: `src/helix/tools/synthesis.py`
OVERWRITE with:

```python
"""
Helix synthesis pipeline — deterministic, vector-based clinical evidence scoring.

Score formula (weighted sum → [0, 100]):
  final_score = 100 * (
      0.35 * condition_match +
      0.30 * eligibility_fit +
      0.20 * evidence_support +
      0.15 * trial_phase_maturity
  )

All sub-scores are normalized to [0, 1] before weighting.
"""

import asyncio
from helix.tools.eligibility import matchEligibility
from helix.tools.pubmed import searchPapers
from helix.clients.fdaClient import FdaClient
from helix.utils.formatter import Formatter
from helix.config.weights import WEIGHTS

_fda_client = FdaClient()
_formatter = Formatter()


# ---------------------------------------------------------------------------
# Sub-score helpers
# ---------------------------------------------------------------------------

def _phase_maturity_score(phase: list) -> float:
    """Map trial phase list to a [0, 1] maturity score."""
    if not isinstance(phase, list):
        return 0.5
    if any(p in ["PHASE3", "PHASE4"] for p in phase):
        return 1.0
    if any(p == "PHASE2" for p in phase):
        return 0.6
    if any(p == "PHASE1" for p in phase):
        return 0.3
    return 0.5  # unknown phase gets neutral score


def _normalize(value: float, max_val: float) -> float:
    """Clamp value/max_val to [0, 1]. Returns 0.0 if max_val is 0."""
    if not max_val or max_val <= 0:
        return 0.0
    return min(float(value) / float(max_val), 1.0)


# ---------------------------------------------------------------------------
# Hard eligibility check (MUST run before scoring)
# ---------------------------------------------------------------------------

def _passes_hard_eligibility(trial: dict, age: int) -> tuple[bool, str]:
    """
    Returns (True, "") if patient passes hard eligibility.
    Returns (False, reason_string) if trial must be excluded.
    """
    min_age = trial.get("min_age")
    max_age = trial.get("max_age")

    if isinstance(min_age, int) and age < min_age:
        return False, f"age {age} below minimum {min_age}"
    if isinstance(max_age, int) and age > max_age:
        return False, f"age {age} above maximum {max_age}"
    if not trial.get("id"):
        return False, "missing trial ID"
    if not trial.get("title"):
        return False, "missing trial title"

    return True, ""


# ---------------------------------------------------------------------------
# Core profile builder
# ---------------------------------------------------------------------------

def buildTrialProfile(
    trial: dict,
    age: int,
    condition: str,
    papers: list,
    drugs: list,
) -> dict:
    """
    Build a fully-scored trial profile with explainability vectors.
    Assumes the trial has already PASSED hard eligibility.
    """
    # --- Condition match ---
    cond_tokens = set((condition or "").lower().split())
    title_tokens = set((trial.get("title") or "").lower().split())
    condition_overlap = len(cond_tokens & title_tokens)
    condition_match = _normalize(condition_overlap, max(len(cond_tokens), 1))

    # --- Evidence support ---
    evidence_hits = 0
    for paper in papers:
        if not isinstance(paper, dict):
            continue
        paper_tokens = set((paper.get("title") or "").lower().split())
        if paper_tokens & cond_tokens:
            evidence_hits += 1
    evidence_support = _normalize(evidence_hits, max(len(papers), 1))

    # --- Eligibility fit (1.0 = passed hard filter, which is always True here) ---
    eligibility_fit = 1.0

    # --- Phase maturity ---
    phase = trial.get("phase") or []
    phase_maturity = _phase_maturity_score(phase)

    # --- Weighted final score (0–100) ---
    final_score = round(
        100.0 * (
            WEIGHTS["condition_match"] * condition_match
            + WEIGHTS["eligibility_fit"] * eligibility_fit
            + WEIGHTS["evidence_support"] * evidence_support
            + WEIGHTS["trial_phase_maturity"] * phase_maturity
        ),
        2,
    )

    # --- Explainability penalties ---
    min_age = trial.get("min_age")
    max_age = trial.get("max_age")
    age_penalty = 0.0
    if isinstance(min_age, int) and age < min_age:
        age_penalty = round((min_age - age) / max(min_age, 1), 3)
    elif isinstance(max_age, int) and age > max_age:
        age_penalty = round((age - max_age) / max(age, 1), 3)

    phase_penalty = round(1.0 - phase_maturity, 3)

    # --- Risk flags ---
    risk_flags = []
    if condition_match < 0.2:
        risk_flags.append("LOW_CONDITION_MATCH")
    if phase_maturity <= 0.3:
        risk_flags.append("EARLY_STAGE_TRIAL")
    if evidence_support < 0.1:
        risk_flags.append("LOW_EVIDENCE_SUPPORT")

    return {
        "id": trial.get("id") or "",
        "title": trial.get("title") or "",
        "url": trial.get("url") or "",
        "phase": phase,
        "final_score": final_score,
        "score_vector": {
            "condition_match": round(condition_match, 4),
            "eligibility_fit": round(eligibility_fit, 4),
            "evidence_support": round(evidence_support, 4),
            "trial_phase_maturity": round(phase_maturity, 4),
        },
        "explainability_vector": {
            "condition_overlap_raw": condition_overlap,
            "evidence_hits_raw": evidence_hits,
            "age_penalty": age_penalty,
            "phase_penalty": phase_penalty,
        },
        "risk_flags": risk_flags,
    }


# ---------------------------------------------------------------------------
# Clinical insight summary
# ---------------------------------------------------------------------------

def buildClinicalInsight(profiles: list, condition: str) -> dict:
    """Aggregate summary statistics over all scored profiles."""
    if not profiles:
        return {
            "total_trials": 0,
            "top_score": 0.0,
            "average_score": 0.0,
            "condition": condition or "",
        }

    scores = [p.get("final_score", 0.0) for p in profiles]
    return {
        "total_trials": len(profiles),
        "top_score": round(max(scores), 2),
        "average_score": round(sum(scores) / len(scores), 2),
        "condition": condition or "",
    }


# ---------------------------------------------------------------------------
# Main synthesis entry point
# ---------------------------------------------------------------------------

async def synthesizeEvidence(
    condition: str, age: int, location: str = None
) -> dict:
    """
    Cross-database clinical evidence synthesis.

    Steps:
      1. Fetch candidate trials + PubMed papers concurrently.
      2. Fetch FDA drug context for the condition.
      3. Hard eligibility filter — split into eligible/excluded.
      4. Score eligible trials with deterministic vector model.
      5. Return structured report with explainability.

    Returns:
      {
        "clinicalInsight": { total_trials, top_score, average_score, condition },
        "trialProfiles":   [ ... scored trial profiles ... ],
        "excludedTrials":  [ ... debug list of rejected trials ... ]
      }
    """
    # Step 1: concurrent fetch
    trials, papers = await asyncio.gather(
        matchEligibility(condition, age, location, limit=8),
        searchPapers(condition, limit=5),
    )

    # Step 2: FDA drug context (fire-and-forget safe)
    try:
        drugs_raw = await _fda_client.searchByIndication(condition, limit=3)
        drugs = _formatter.shapeDrugResults(drugs_raw) if isinstance(drugs_raw, dict) else []
    except Exception:
        drugs = []

    # Step 3: hard eligibility split
    eligible_trials = []
    excluded_trials = []

    for trial in (trials or []):
        passed, reason = _passes_hard_eligibility(trial, age)
        if passed:
            eligible_trials.append(trial)
        else:
            excluded_trials.append({
                "id": trial.get("id") or "",
                "title": trial.get("title") or "",
                "exclusion_reason": reason,
            })

    # Step 4: score eligible trials
    profiles = [
        buildTrialProfile(t, age, condition, papers or [], drugs)
        for t in eligible_trials
    ]

    # Sort by score descending for easy reading
    profiles.sort(key=lambda p: p.get("final_score", 0.0), reverse=True)

    # Step 5: assemble report
    return {
        "clinicalInsight": buildClinicalInsight(profiles, condition),
        "trialProfiles": profiles,
        "excludedTrials": excluded_trials,
    }
```

---

### FILE 15: `src/helix/server.py`
OVERWRITE with:

```python
from mcp.server.fastmcp import FastMCP
from helix.tools.trials import findTrials
from helix.tools.pubmed import searchPapers
from helix.tools.fda import lookupDrug
from helix.tools.eligibility import matchEligibility
from helix.tools.synthesis import synthesizeEvidence
from helix.config import server as server_config

mcp = FastMCP(server_config.name)


@mcp.tool()
async def find_trials(
    condition: str, location: str = None, limit: int = 10
) -> list[dict]:
    """Find active clinical trials matching a medical condition."""
    return await findTrials(condition, location, limit)


@mcp.tool()
async def search_papers(
    topic: str, yearFrom: int = None, yearTo: int = None, limit: int = 10
) -> list[dict]:
    """Search PubMed for peer-reviewed research papers."""
    return await searchPapers(topic, yearFrom, yearTo, limit)


@mcp.tool()
async def lookup_drug(name: str, limit: int = 5) -> list[dict]:
    """Look up FDA drug information by brand or generic name."""
    return await lookupDrug(name, limit)


@mcp.tool()
async def match_eligibility(
    condition: str, age: int, location: str = None, limit: int = 10
) -> list[dict]:
    """Match a patient profile to clinical trials ranked by eligibility fit."""
    return await matchEligibility(condition, age, location, limit)


@mcp.tool()
async def synthesize_evidence(
    condition: str, age: int, location: str = None
) -> dict:
    """
    Cross-database clinical evidence synthesis.

    Runs trial matching, PubMed research, and FDA drug lookup simultaneously
    and returns a single fused report with per-trial explainability vectors.

    Args:
        condition: Medical condition (e.g. "Type 2 Diabetes")
        age: Patient age in years
        location: Optional location filter (e.g. "London, UK")
    """
    return await synthesizeEvidence(condition, age, location)


def run():
    mcp.run()


if __name__ == "__main__":
    run()
```

---

### FILE 16: `tests/tools/testSynthesis.py`
OVERWRITE with:

```python
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
```

---

### FILE 17: `tests/tools/testEligibility.py`
OVERWRITE with:

```python
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
```

---

### FILE 18: `tests/tools/testFda.py`
OVERWRITE with:

```python
import asyncio
from helix.tools.fda import lookupDrug


async def main():
    print("Looking up Metformin in FDA database...\n")
    results = await lookupDrug("metformin", limit=2)

    for drug in (results or []):
        print(f"Brand      : {drug.get('brand_name', 'N/A')}")
        print(f"Generic    : {drug.get('generic_name', 'N/A')}")
        print(f"Maker      : {drug.get('manufacturer', 'N/A')}")
        print(f"Route      : {drug.get('route', [])}")
        print(f"Indications: {(drug.get('indications') or '')[:150]}")
        print("---")


asyncio.run(main())
```

---

### FILE 19: `tests/tools/testPubmed.py`
OVERWRITE with:

```python
import asyncio
from helix.tools.pubmed import searchPapers


async def main():
    print("Searching PubMed for Alzheimer's research...\n")
    results = await searchPapers("Alzheimer's disease", yearFrom=2023, limit=3)

    for paper in (results or []):
        print(f"ID      : {paper.get('id', 'N/A')}")
        print(f"Title   : {paper.get('title', 'N/A')}")
        print(f"Authors : {', '.join(paper.get('authors', []))}")
        print(f"Journal : {paper.get('journal', 'N/A')}")
        print(f"Year    : {paper.get('year', 'N/A')}")
        print(f"URL     : {paper.get('url', '')}")
        print("---")


asyncio.run(main())
```

---

### FILE 20: `tests/tools/testTrials.py`
OVERWRITE with:

```python
import asyncio
from helix.tools.trials import findTrials


async def main():
    print("Searching for diabetes trials...\n")
    results = await findTrials("Type 2 Diabetes", limit=3)

    for trial in (results or []):
        print(f"ID     : {trial.get('id', 'N/A')}")
        print(f"Title  : {trial.get('title', 'N/A')}")
        print(f"Status : {trial.get('status', 'N/A')}")
        print(f"Phase  : {trial.get('phase', [])}")
        print(f"URL    : {trial.get('url', '')}")
        print("---")


asyncio.run(main())
```

---

## DELETION REQUIRED

Delete this file. It conflicts with the config package directory:

```
src/helix/config.py
```

To delete it, run:
```bash
rm src/helix/config.py
```

---

## EXECUTION INSTRUCTIONS FOR GEMINI CLI

Do all of the following in order:

1. Run `rm src/helix/config.py` to remove the conflicting config file.

2. For each FILE listed above (FILE 1 through FILE 20), overwrite the file at the given path with exactly the content shown in its code block. Create any directories that don't exist.

3. After writing all files, run:
   ```bash
   cd /path/to/Helix-main
   python tests/tools/testSynthesis.py
   ```
   and confirm it completes without errors and prints a structured clinical report.

4. Also verify individually:
   ```bash
   python tests/tools/testFda.py
   python tests/tools/testPubmed.py
   python tests/tools/testTrials.py
   python tests/tools/testEligibility.py
   ```

5. Do NOT modify `pyproject.toml`, `README.md`, `.gitignore`, or `LICENSE`.

6. Do NOT add any new Python packages. Only use: `httpx`, `asyncio` (stdlib), `json` (stdlib), `os` (stdlib), `mcp`, `pydantic`, `python-dotenv`.

7. Do NOT use `subprocess` anywhere in the final code.

8. Confirm all `__pycache__` directories can be safely deleted after the rewrite:
   ```bash
   find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
   ```

---

## VERIFICATION CHECKLIST

After all files are written, the following must be true:

- [ ] `from helix.config import server, pubmed, fda, trials` all work without error
- [ ] `from helix.clients.fdaClient import FdaClient` and `FdaClient().search(...)` exists
- [ ] `from helix.clients.trialsClient import TrialsClient` and `TrialsClient().search(...)` is async
- [ ] `from helix.clients.pubmedClient import PubMedClient` and `.search(...)` is async
- [ ] `synthesizeEvidence("Type 2 Diabetes", 45)` returns dict with keys: `clinicalInsight`, `trialProfiles`, `excludedTrials`
- [ ] Each item in `trialProfiles` has keys: `id`, `title`, `final_score`, `score_vector`, `explainability_vector`, `risk_flags`
- [ ] `score_vector` has exactly: `condition_match`, `eligibility_fit`, `evidence_support`, `trial_phase_maturity`
- [ ] `explainability_vector` has exactly: `condition_overlap_raw`, `evidence_hits_raw`, `age_penalty`, `phase_penalty`
- [ ] No `subprocess` calls remain in any Python file
- [ ] `testSynthesis.py` prints structured output without KeyError, AttributeError, or TypeError

---
END OF PROMPT
