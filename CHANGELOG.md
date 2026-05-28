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
