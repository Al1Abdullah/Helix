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
