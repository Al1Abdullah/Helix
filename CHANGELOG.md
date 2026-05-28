# Changelog

## [1.3.0] — 2026-05-28

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

## [1.2.0] — 2026-05-28

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
