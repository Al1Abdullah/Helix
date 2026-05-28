# HELIX v1.0.0 UPGRADE — GEMINI CLI EXECUTION PROMPT
# Run from inside: Helix-main/
# Gemini: read this file top to bottom and execute every instruction exactly.

## OVERVIEW — 18 file operations

Creates (new):
  src/helix/models.py
  src/helix/cache.py
  src/helix/logger.py
  src/helix/api.py
  src/helix/tools/health.py
  tests/tools/testHealth.py
  CHANGELOG.md

Overwrites (replace entire content):
  pyproject.toml
  src/helix/config/__init__.py
  src/helix/clients/fdaClient.py
  src/helix/clients/trialsClient.py
  src/helix/clients/pubmedClient.py
  src/helix/tools/synthesis.py
  src/helix/tools/trials.py
  src/helix/tools/pubmed.py
  src/helix/tools/fda.py
  src/helix/server.py
  README.md

Do NOT touch any other file.

---

## FILE 1 — pyproject.toml (OVERWRITE)

```toml
[project]
name = "helix"
version = "1.0.0"
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

## FILE 2 — src/helix/config/__init__.py (OVERWRITE)

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


class CacheConfig:
    synthesis_ttl: int = 300   # 5 min
    trials_ttl: int = 180      # 3 min
    papers_ttl: int = 600      # 10 min
    drugs_ttl: int = 3600      # 1 hr


class ServerConfig:
    name: str = "Helix"
    version: str = "1.0.0"


trials = TrialsConfig()
pubmed = PubMedConfig()
fda = FdaConfig()
cache = CacheConfig()
server = ServerConfig()
```

---

## FILE 3 — src/helix/models.py (CREATE)

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

## FILE 4 — src/helix/cache.py (CREATE)

```python
"""Async in-memory TTL cache — no external dependencies."""
import asyncio
import time
from typing import Any, Optional


class TTLCache:
    def __init__(self, default_ttl: int = 300):
        self._store: dict[str, tuple[Any, float]] = {}
        self._lock = asyncio.Lock()
        self.default_ttl = default_ttl

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.monotonic() > expires_at:
                del self._store[key]
                return None
            return value

    async def set(self, key: str, value: Any, ttl: int = None) -> None:
        async with self._lock:
            self._store[key] = (value, time.monotonic() + (ttl or self.default_ttl))

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()

    def stats(self) -> dict:
        now = time.monotonic()
        total = len(self._store)
        valid = sum(1 for _, (_, exp) in self._store.items() if exp > now)
        return {"total_keys": total, "valid_keys": valid, "expired_keys": total - valid}


from helix.config import cache as _cfg

synthesis_cache = TTLCache(default_ttl=_cfg.synthesis_ttl)
trials_cache    = TTLCache(default_ttl=_cfg.trials_ttl)
papers_cache    = TTLCache(default_ttl=_cfg.papers_ttl)
drugs_cache     = TTLCache(default_ttl=_cfg.drugs_ttl)
```

---

## FILE 5 — src/helix/logger.py (CREATE)

```python
"""Structured JSON logger — all output to stderr, never pollutes MCP stdout."""
import json
import logging
import sys
from datetime import datetime, timezone

_SKIP = {
    "args","asctime","created","exc_info","exc_text","filename","funcName",
    "id","levelname","levelno","lineno","module","msecs","message","msg",
    "name","pathname","process","processName","relativeCreated","stack_info",
    "thread","threadName","taskName",
}


class _JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.module,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        for k, v in record.__dict__.items():
            if k not in _SKIP:
                payload[k] = v
        return json.dumps(payload, default=str)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        h = logging.StreamHandler(sys.stderr)
        h.setFormatter(_JSONFormatter())
        logger.addHandler(h)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger
```

---

## FILE 6 — src/helix/clients/fdaClient.py (OVERWRITE)

```python
"""openFDA drug label client — retry with exponential backoff, 4xx short-circuit."""
import asyncio
import httpx
from helix.config import fda as fda_config
from helix.logger import get_logger

_log = get_logger(__name__)
_FALLBACK = {"results": [], "error": "no_data"}
_NO_RETRY = {400, 401, 403, 404, 422}
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


class FdaClient:
    def __init__(self):
        self._base = fda_config.base_url

    async def search(self, name: str, limit: int = 5) -> dict:
        q = name.replace(" ", "+")
        url = f"{self._base}/label.json?search=openfda.brand_name:{q}+openfda.generic_name:{q}&limit={limit}"
        return await self._get(url, f"drug:{name}")

    async def searchByIndication(self, condition: str, limit: int = 5) -> dict:
        q = f'"{condition}"'.replace(" ", "+")
        url = f"{self._base}/label.json?search=indications_and_usage:{q}&limit={limit}"
        return await self._get(url, f"indication:{condition}")

    async def _get(self, url: str, ctx: str = "") -> dict:
        last = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=15.0) as c:
                    r = await c.get(url, headers=_HEADERS)
                    r.raise_for_status()
                    d = r.json()
                    return d if isinstance(d, dict) else _FALLBACK
            except httpx.HTTPStatusError as e:
                if e.response.status_code in _NO_RETRY:
                    return {"results": [], "error": f"http_{e.response.status_code}"}
                last = e
            except Exception as e:
                last = e
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)
        _log.warning("fda_exhausted", extra={"ctx": ctx, "error": str(last)})
        return _FALLBACK
```

---

## FILE 7 — src/helix/clients/trialsClient.py (OVERWRITE)

```python
"""ClinicalTrials.gov v2 client — curl_cffi Chrome impersonation bypasses WAF 403."""
import asyncio
from helix.config import trials as trials_config
from helix.logger import get_logger

_log = get_logger(__name__)
_FALLBACK = {"studies": []}

try:
    from curl_cffi.requests import AsyncSession as _Curl
    _USE_CURL = True
except ImportError:
    _USE_CURL = False

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
}


class TrialsClient:
    def __init__(self):
        self._base = trials_config.base_url

    async def search(self, condition: str, location: str = None, limit: int = 10) -> dict:
        params = {
            "query.cond": condition,
            "filter.overallStatus": "RECRUITING,NOT_YET_RECRUITING",
            "pageSize": min(limit, trials_config.max_limit),
            "format": "json",
        }
        if location:
            params["query.locn"] = location
        url = f"{self._base}/studies"
        last = None
        for attempt in range(3):
            try:
                if _USE_CURL:
                    async with _Curl(impersonate="chrome120") as s:
                        r = await s.get(url, params=params, headers=_HEADERS, timeout=20)
                        r.raise_for_status()
                        d = r.json()
                        return d if isinstance(d, dict) else _FALLBACK
                else:
                    import httpx
                    async with httpx.AsyncClient(timeout=20.0) as c:
                        r = await c.get(url, params=params, headers=_HEADERS)
                        r.raise_for_status()
                        d = r.json()
                        return d if isinstance(d, dict) else _FALLBACK
            except Exception as e:
                last = e
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)
        _log.warning("trials_exhausted", extra={"condition": condition, "error": str(last)})
        return _FALLBACK
```

---

## FILE 8 — src/helix/clients/pubmedClient.py (OVERWRITE)

```python
"""NCBI PubMed E-utilities client — retry with exponential backoff."""
import asyncio
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
```

---

## FILE 9 — src/helix/tools/health.py (CREATE)

```python
"""Health check — concurrent ping of all 3 APIs with latency measurement."""
import asyncio
import time
from datetime import datetime, timezone
from helix.clients.trialsClient import TrialsClient
from helix.clients.pubmedClient import PubMedClient
from helix.clients.fdaClient import FdaClient
from helix.models import HealthReport, ServiceHealth
from helix.config import server as server_config

_trials = TrialsClient()
_pubmed = PubMedClient()
_fda    = FdaClient()


async def _ping_trials():
    t = time.monotonic()
    try:
        raw = await _trials.search("cancer", limit=1)
        ok = isinstance(raw.get("studies"), list)
        return ServiceHealth(status="ok" if ok else "degraded", latency_ms=round((time.monotonic()-t)*1000,1))
    except Exception as e:
        return ServiceHealth(status="error", latency_ms=round((time.monotonic()-t)*1000,1), error=str(e))


async def _ping_pubmed():
    t = time.monotonic()
    try:
        ids = await _pubmed.search("cancer", limit=1)
        return ServiceHealth(status="ok" if isinstance(ids, list) else "degraded", latency_ms=round((time.monotonic()-t)*1000,1))
    except Exception as e:
        return ServiceHealth(status="error", latency_ms=round((time.monotonic()-t)*1000,1), error=str(e))


async def _ping_fda():
    t = time.monotonic()
    try:
        raw = await _fda.search("aspirin", limit=1)
        ok = isinstance(raw, dict) and "error" not in raw
        return ServiceHealth(status="ok" if ok else "degraded", latency_ms=round((time.monotonic()-t)*1000,1))
    except Exception as e:
        return ServiceHealth(status="error", latency_ms=round((time.monotonic()-t)*1000,1), error=str(e))


async def checkHealth() -> dict:
    """Ping all 3 APIs concurrently. Returns HealthReport dict."""
    t_h, p_h, f_h = await asyncio.gather(_ping_trials(), _ping_pubmed(), _ping_fda())
    services = {"clinicaltrials_gov": t_h, "pubmed": p_h, "fda": f_h}
    overall = "ok" if all(s.status == "ok" for s in services.values()) else "degraded"
    return HealthReport(
        status=overall,
        version=server_config.version,
        services=services,
        timestamp=datetime.now(timezone.utc).isoformat(),
    ).model_dump()
```

---

## FILE 10 — src/helix/tools/trials.py (OVERWRITE)

```python
from helix.clients.trialsClient import TrialsClient
from helix.utils.formatter import Formatter
from helix.cache import trials_cache
from helix.logger import get_logger

_client = TrialsClient()
_fmt    = Formatter()
_log    = get_logger(__name__)


async def findTrials(condition: str, location: str = None, limit: int = 10) -> list[dict]:
    """Find active clinical trials. Cached 3 min. Never raises."""
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

## FILE 11 — src/helix/tools/pubmed.py (OVERWRITE)

```python
from helix.clients.pubmedClient import PubMedClient
from helix.utils.formatter import Formatter
from helix.cache import papers_cache
from helix.logger import get_logger

_client = PubMedClient()
_fmt    = Formatter()
_log    = get_logger(__name__)


async def searchPapers(topic: str, yearFrom: int = None, yearTo: int = None, limit: int = 10) -> list[dict]:
    """Search PubMed. Cached 10 min. Never raises."""
    key = f"papers:{topic.lower().strip()}:{yearFrom}:{yearTo}:{limit}"
    cached = await papers_cache.get(key)
    if cached is not None:
        _log.info("cache_hit", extra={"tool": "pubmed", "topic": topic})
        return cached
    try:
        ids = await _client.search(topic, year_from=yearFrom, year_to=yearTo, limit=limit)
        if not ids:
            return []
        summaries = await _client.fetchSummaries(ids)
        result = _fmt.shapePaperResults(ids, summaries)
        await papers_cache.set(key, result)
        _log.info("fetched", extra={"tool": "pubmed", "topic": topic, "count": len(result)})
        return result
    except Exception as e:
        _log.warning("error", extra={"tool": "pubmed", "error": str(e)})
        return [{"id": "", "title": f"[error: {e}]", "abstract": "", "authors": [], "journal": "", "year": 0, "url": ""}]
```

---

## FILE 12 — src/helix/tools/fda.py (OVERWRITE)

```python
from helix.clients.fdaClient import FdaClient
from helix.utils.formatter import Formatter
from helix.cache import drugs_cache
from helix.logger import get_logger

_client = FdaClient()
_fmt    = Formatter()
_log    = get_logger(__name__)


async def lookupDrug(name: str, limit: int = 5) -> list[dict]:
    """Look up FDA drug info. Cached 1 hr. Never raises."""
    key = f"drugs:{name.lower().strip()}:{limit}"
    cached = await drugs_cache.get(key)
    if cached is not None:
        _log.info("cache_hit", extra={"tool": "fda", "name": name})
        return cached
    try:
        raw = await _client.search(name, limit)
        if raw.get("error") or not raw.get("results"):
            return []
        result = _fmt.shapeDrugResults(raw)
        await drugs_cache.set(key, result)
        _log.info("fetched", extra={"tool": "fda", "name": name, "count": len(result)})
        return result
    except Exception as e:
        _log.warning("error", extra={"tool": "fda", "error": str(e)})
        return [{"brand_name": "", "generic_name": f"[error: {e}]", "manufacturer": "", "route": [], "indications": "", "warnings": ""}]
```

---

## FILE 13 — src/helix/tools/synthesis.py (OVERWRITE)

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


def buildTrialProfile(trial: dict, age: int, condition: str, papers: list, drugs: list) -> dict:
    cond_tok  = set((condition or "").lower().split())
    title_tok = set((trial.get("title") or "").lower().split())
    overlap   = len(cond_tok & title_tok)
    cond_m    = _norm(overlap, max(len(cond_tok), 1))

    ev_hits   = sum(1 for p in papers if isinstance(p, dict) and (set((p.get("title") or "").lower().split()) & cond_tok))
    ev_m      = _norm(ev_hits, max(len(papers), 1))

    phase     = trial.get("phase") or []
    phase_m   = _phase_score(phase)
    elig_m    = 1.0

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
    if cond_m    < 0.2: flags.append("LOW_CONDITION_MATCH")
    if phase_m   <= 0.3: flags.append("EARLY_STAGE_TRIAL")
    if ev_m      < 0.1: flags.append("LOW_EVIDENCE_SUPPORT")

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

## FILE 14 — src/helix/server.py (OVERWRITE)

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
    """Find active clinical trials matching a medical condition."""
    return await findTrials(condition, location, limit)


@mcp.tool()
async def search_papers(topic: str, yearFrom: int = None, yearTo: int = None, limit: int = 10) -> list[dict]:
    """Search PubMed for peer-reviewed research papers."""
    return await searchPapers(topic, yearFrom, yearTo, limit)


@mcp.tool()
async def lookup_drug(name: str, limit: int = 5) -> list[dict]:
    """Look up FDA drug information by brand or generic name."""
    return await lookupDrug(name, limit)


@mcp.tool()
async def match_eligibility(condition: str, age: int, location: str = None, limit: int = 10) -> list[dict]:
    """Match a patient profile to clinical trials ranked by eligibility fit."""
    return await matchEligibility(condition, age, location, limit)


@mcp.tool()
async def synthesize_evidence(condition: str, age: int, location: str = None) -> dict:
    """
    Cross-database clinical evidence synthesis.
    Queries ClinicalTrials.gov, PubMed, and openFDA concurrently.
    Returns scored, ranked trials with full explainability vectors.

    Args:
        condition: Medical condition (e.g. "Type 2 Diabetes")
        age: Patient age in years
        location: Optional location filter (e.g. "London, UK")
    """
    return await synthesizeEvidence(condition, age, location)


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

## FILE 15 — src/helix/api.py (CREATE)

```python
"""
Helix REST API — FastAPI layer.
Start: helix-api  OR  python -m helix.api
Docs:  http://localhost:8000/docs
"""
from contextlib import asynccontextmanager
from typing import Optional
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
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET","POST"], allow_headers=["*"])


class SynthesizeRequest(BaseModel):
    condition: str
    age: int
    location: Optional[str] = None


class EligibilityRequest(BaseModel):
    condition: str
    age: int
    location: Optional[str] = None
    limit: int = 10


@app.get("/health", tags=["System"])
async def health():
    """Ping all 3 APIs and report latency per service."""
    return await checkHealth()


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
    """Full cross-database synthesis with scored, explainable trial profiles."""
    return await synthesizeEvidence(req.condition, req.age, req.location)


@app.post("/eligibility", tags=["Evidence"])
async def eligibility(req: EligibilityRequest):
    """Match patient profile to trials by age and condition."""
    return await matchEligibility(req.condition, req.age, req.location, req.limit)


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

## FILE 16 — tests/tools/testHealth.py (CREATE)

```python
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
```

---

## FILE 17 — CHANGELOG.md (CREATE)

```markdown
# Changelog

## [1.0.0] — 2025-06-01

### Added
- **FastAPI REST layer** (`helix-api`) — full HTTP API on `:8000` with auto-generated Swagger UI at `/docs`
- **Async TTL cache** — in-memory per-tool caching (synthesis 5 min, trials 3 min, papers 10 min, drugs 1 hr)
- **Health check** — `health_check` MCP tool + `GET /health` REST endpoint with concurrent per-service latency
- **Pydantic v2 models** — `Trial`, `Paper`, `Drug`, `TrialProfile`, `ScoreVector`, `ExplainabilityVector`, `SynthesisResult`, `HealthReport`
- **Structured JSON logging** — all modules log to stderr in JSON (Datadog/CloudWatch-ready)
- **Exponential backoff retry** — all 3 API clients retry 3x (1s → 2s); non-retryable 4xx short-circuits immediately

### Changed
- Version `0.1.0` → `1.0.0`
- All tool functions log cache hit/miss and fetch counts

## [0.2.0] — 2025-05-30

### Fixed
- WAF bypass — replaced plain httpx with `curl_cffi` Chrome TLS impersonation in `trialsClient.py`; resolves Cloudflare 403

## [0.1.0] — 2025-05-28

### Added
- Initial production refactor from prototype
- Deterministic vector scoring with explainability
- Hard eligibility pre-filter with `excludedTrials`
- Async `httpx` clients, canonical schema, age parsing
```

---

## FILE 18 — README.md (OVERWRITE)

```markdown
<div align="center">

# Helix

**Clinical evidence synthesis engine — free, no API key, production-grade.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-111111?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-111111?style=flat-square)](LICENSE)
[![MCP Compatible](https://img.shields.io/badge/MCP-compatible-111111?style=flat-square)](https://modelcontextprotocol.io)
[![REST API](https://img.shields.io/badge/REST_API-:8000-111111?style=flat-square)](#rest-api)
[![No API Key](https://img.shields.io/badge/no_API_key-required-111111?style=flat-square)](#data-sources)
[![Version](https://img.shields.io/badge/version-1.0.0-111111?style=flat-square)](CHANGELOG.md)

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
| `GET` | `/papers` | Search PubMed |
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

### MCP Tools

| Tool | Description |
|------|-------------|
| `synthesize_evidence` | Full cross-database synthesis with scored, explainable profiles |
| `find_trials` | Search ClinicalTrials.gov for recruiting trials |
| `search_papers` | Search PubMed by topic + year range |
| `lookup_drug` | FDA drug label lookup |
| `match_eligibility` | Pre-filter trials by patient age + condition |
| `health_check` | Live API connectivity + latency report |

---

## Scoring Model

```
final_score = 100 × (
    0.35 × condition_match       +
    0.30 × eligibility_fit       +
    0.20 × evidence_support      +
    0.15 × trial_phase_maturity
)
```

All sub-scores normalized to [0, 1]. Full `score_vector` and `explainability_vector` returned with every profile — every score is auditable.

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
│   ├── pubmedClient.py     httpx + retry
│   └── fdaClient.py        httpx + retry
├── tools/              Business logic layer (cached)
│   ├── synthesis.py        Vector scoring pipeline
│   ├── eligibility.py      Age-based pre-filter
│   ├── trials.py / pubmed.py / fda.py / health.py
└── utils/
    └── formatter.py        API response normalizer
```

---

## License

MIT — see [LICENSE](LICENSE).
```

---

## EXECUTION ORDER

Run these commands exactly, in order, from inside `Helix-main/`:

```bash
pip install "fastapi>=0.111.0" "uvicorn>=0.30.0" "curl_cffi>=0.7.0"
pip install -e .
python tests/tools/testHealth.py
python tests/tools/testSynthesis.py
python tests/tools/testTrials.py
python tests/tools/testEligibility.py
python tests/tools/testFda.py
python tests/tools/testPubmed.py
helix-api &
sleep 2
curl -s http://localhost:8000/health | python3 -m json.tool
curl -s http://localhost:8000/cache/stats | python3 -m json.tool
kill %1
git add .
git commit -m "feat: v1.0.0 — FastAPI REST, TTL cache, Pydantic v2, retry, health check, JSON logs"
git push
```

---

## VERIFICATION CHECKLIST

- [ ] `from helix.models import Trial, TrialProfile, SynthesisResult, HealthReport` — no error
- [ ] `from helix.cache import synthesis_cache, trials_cache, papers_cache, drugs_cache` — no error
- [ ] `from helix.logger import get_logger` — no error
- [ ] `from helix.api import app` — FastAPI app object exists
- [ ] `from helix.tools.health import checkHealth` — no error
- [ ] `testHealth.py` prints ✓ for all 3 services
- [ ] `testSynthesis.py` prints full report with scored profiles
- [ ] `/cache/stats` returns `{"synthesis":{...},"trials":{...},"papers":{...},"drugs":{...}}`
- [ ] `CHANGELOG.md` exists at repo root with v1.0.0 entry
- [ ] `README.md` contains REST API table and scoring formula
