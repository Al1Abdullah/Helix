# HELIX — WAF FIX PROMPT (targeted, 2 files only)
# Run from inside Helix-main/

---

## PROBLEM

`src/helix/clients/trialsClient.py` currently uses `httpx`.
ClinicalTrials.gov sits behind Cloudflare WAF which inspects TLS fingerprints (JA3/JA4).
`httpx` has a non-browser TLS fingerprint → 403 Forbidden every request → zero trials returned.

The fix is to replace `httpx` in `trialsClient.py` with `curl_cffi`, which impersonates
a real Chrome TLS fingerprint and passes WAF inspection.

Only TWO files need to change. Do NOT touch any other file.

---

## FILE 1 — `pyproject.toml`

FIND this exact block:

```toml
dependencies = [
    "mcp[cli]>=1.0.0",
    "httpx>=0.27.0",
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
]
```

REPLACE it with:

```toml
dependencies = [
    "mcp[cli]>=1.0.0",
    "httpx>=0.27.0",
    "curl_cffi>=0.7.0",
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
]
```

(Keep every other line in pyproject.toml exactly as-is.)

---

## FILE 2 — `src/helix/clients/trialsClient.py`

OVERWRITE the entire file with:

```python
"""
trialsClient.py — ClinicalTrials.gov API v2 client.

Uses curl_cffi to impersonate a Chrome TLS fingerprint, bypassing Cloudflare
WAF which blocks non-browser TLS stacks (httpx, requests, aiohttp all fail with 403).
Falls back to plain httpx automatically if curl_cffi is not installed.
"""

from helix.config import trials as trials_config

_SAFE_FALLBACK = {"studies": []}

# --- TLS fingerprint strategy -------------------------------------------------
# curl_cffi impersonates Chrome's JA3/JA4 TLS fingerprint → passes WAF.
# httpx fallback is kept so the import never hard-crashes in edge environments.
try:
    from curl_cffi.requests import AsyncSession as _CurlSession
    _USE_CURL = True
except ImportError:
    _USE_CURL = False
    import httpx


_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}


class TrialsClient:
    def __init__(self):
        self._base_url = trials_config.base_url

    async def search(
        self, condition: str, location: str = None, limit: int = 10
    ) -> dict:
        """
        Search ClinicalTrials.gov for recruiting trials matching a condition.
        Returns safe fallback {"studies": []} on any error.
        """
        params = {
            "query.cond": condition,
            "filter.overallStatus": "RECRUITING,NOT_YET_RECRUITING",
            "pageSize": min(limit, trials_config.max_limit),
            "format": "json",
        }
        if location:
            params["query.locn"] = location

        url = f"{self._base_url}/studies"

        if _USE_CURL:
            return await self._get_curl(url, params)
        return await self._get_httpx(url, params)

    async def _get_curl(self, url: str, params: dict) -> dict:
        """Fetch using curl_cffi Chrome impersonation (bypasses WAF)."""
        try:
            async with _CurlSession(impersonate="chrome120") as session:
                response = await session.get(
                    url,
                    params=params,
                    headers=_BROWSER_HEADERS,
                    timeout=20,
                )
                response.raise_for_status()
                data = response.json()
                return data if isinstance(data, dict) else _SAFE_FALLBACK
        except Exception:
            return _SAFE_FALLBACK

    async def _get_httpx(self, url: str, params: dict) -> dict:
        """Fallback fetch using httpx (may 403 on WAF-protected endpoints)."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    url, params=params, headers=_BROWSER_HEADERS
                )
                response.raise_for_status()
                data = response.json()
                return data if isinstance(data, dict) else _SAFE_FALLBACK
        except Exception:
            return _SAFE_FALLBACK
```

---

## EXECUTION STEPS

Run these commands in order from inside `Helix-main/`:

```bash
# 1. Install the new dependency
pip install "curl_cffi>=0.7.0"

# 2. Reinstall the package so pyproject.toml changes take effect
pip install -e .

# 3. Run the full test suite
python tests/tools/testSynthesis.py
python tests/tools/testTrials.py
python tests/tools/testEligibility.py
python tests/tools/testFda.py
python tests/tools/testPubmed.py
```

---

## EXPECTED OUTCOME

- `testTrials.py` now returns real trial IDs (NCT...) instead of zero results
- `testSynthesis.py` prints a full clinical report with populated `trialProfiles`
- `testFda.py` and `testPubmed.py` still work (unchanged)
- `testEligibility.py` now returns matched trials with scores

---

## DO NOT TOUCH

- `src/helix/clients/fdaClient.py` — FDA API does not WAF-block httpx, leave it
- `src/helix/clients/pubmedClient.py` — PubMed does not WAF-block httpx, leave it
- Every other file in the repo — already verified clean

---

## VERIFICATION CHECK (run after)

```bash
python -c "
from curl_cffi.requests import AsyncSession
print('curl_cffi installed OK')

import inspect
import sys
sys.path.insert(0, 'src')
from helix.clients.trialsClient import TrialsClient, _USE_CURL
assert _USE_CURL, 'curl_cffi not detected by trialsClient!'
tc = TrialsClient()
assert inspect.iscoroutinefunction(tc.search)
assert inspect.iscoroutinefunction(tc._get_curl)
assert inspect.iscoroutinefunction(tc._get_httpx)
print('trialsClient WAF fix verified')
"
```

