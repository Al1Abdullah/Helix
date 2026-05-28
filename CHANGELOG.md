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
