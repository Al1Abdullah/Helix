<div align="center">

# Helix

### Clinical evidence synthesis engine — free, no API key, production-grade.

[![CI](https://github.com/Al1Abdullah/Helix/actions/workflows/ci.yml/badge.svg)](https://github.com/Al1Abdullah/Helix/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)
[![MCP Compatible](https://img.shields.io/badge/MCP-compatible-purple?style=flat-square)](https://modelcontextprotocol.io)
[![Version](https://img.shields.io/badge/version-1.4.0-orange?style=flat-square)](CHANGELOG.md)
[![Tests](https://img.shields.io/badge/tests-79%20passing-brightgreen?style=flat-square)](#)
[![No API Key](https://img.shields.io/badge/no_API_key-required-red?style=flat-square)](#data-sources)

<br/>

**Give any AI model — or any HTTP client — structured access to the world's three largest free health databases. In one call.**

<br/>

| | |
|:---:|:---:|
|  **400,000+ Clinical Trials** |  **35M+ PubMed Papers** |
| ClinicalTrials.gov live data | Full abstracts via efetch |
|  **FDA Drug Labels** |  **< 4 Second Response** |
| openFDA drug information | All 3 databases in parallel |

</div>

---

## What makes it different

 **Abbreviation expansion** — type `T2D`, get `Type 2 Diabetes`. 70+ medical abbreviations recognized automatically before any API call.

 **Explainable scoring** — every trial gets a score vector: condition match, age-window centrality, evidence support, trial phase maturity. You know exactly why trial #1 ranked above trial #2.

 **Transparent exclusions** — trials that don't qualify don't silently disappear. They appear in `excludedTrials` with the exact rejection reason (`age 72 above max 65`, `sex mismatch: trial=MALE, patient=FEMALE`).

 **Dual interface** — REST API for any language, MCP server for AI models (Claude Desktop, Copilot, Cursor).

 **Zero credentials** — no API keys, no sign-ups, no rate-limit management. Just run it.

---

## Quick Start

```bash
git clone https://github.com/Al1Abdullah/Helix.git
cd Helix
pip install -e .
helix-api
```

Open **[http://localhost:8000/docs](http://localhost:8000/docs)** — full interactive Swagger UI.

```bash
# Docker
docker compose up   # → http://localhost:8000/docs
```

---

## Sample Output

```bash
curl -X POST http://localhost:8000/synthesize \
  -H "Content-Type: application/json" \
  -d '{"condition": "T2D", "age": 45, "sex": "MALE"}'
```

```json
{
  "clinicalInsight": {
    "condition": "Type 2 Diabetes",
    "expanded_from": "T2D",
    "total_trials": 16,
    "top_score": 94.0,
    "average_score": 77.66
  },
  "trialProfiles": [
    {
      "id": "NCT05099770",
      "title": "Proact: A Study of REACT in Subjects With Type 2 Diabetes...",
      "phase": ["PHASE3"],
      "final_score": 94.0,
      "score_vector": {
        "condition_match": 1.0,
        "eligibility_fit": 0.8,
        "evidence_support": 1.0,
        "trial_phase_maturity": 1.0
      },
      "risk_flags": []
    }
  ],
  "excludedTrials": [
    {
      "id": "NCT00000042",
      "title": "Women-Only Cardiovascular Study",
      "exclusion_reason": "sex mismatch: trial=FEMALE, patient=MALE"
    }
  ]
}
```

---

## REST API

```bash
helix-api    # starts on :8000
```

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Live ping of all 3 APIs with per-service latency |
| `GET` | `/synonyms` | All 70+ recognized abbreviations and their expansions |
| `GET` | `/score-weights` | Scoring formula, weight vector, component descriptions |
| `POST` | `/synthesize` | **Full synthesis** — scored + ranked trials, excluded trials with reasons |
| `POST` | `/eligibility` | Match patient profile to trials by condition, age, sex |
| `GET` | `/trials` | Search ClinicalTrials.gov (supports `?sex=MALE\|FEMALE`) |
| `GET` | `/papers` | Search PubMed with full abstracts |
| `GET` | `/drugs` | Search openFDA drug labels |
| `GET` | `/cache/stats` | Inspect TTL cache state |
| `DELETE` | `/cache` | Flush all caches |

> **Validation:** `age` is restricted to `[0, 130]`. `condition` must be `1–300` characters. Invalid inputs return `422` with a clear error.

---

## MCP — Use inside Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "helix": { "command": "helix" }
  }
}
```

Then ask Claude: *"Find clinical trials for a 52-year-old female with NSCLC"* — Helix handles the rest.

| Tool | Description |
|------|-------------|
| `synthesize_evidence` | Full cross-database synthesis with scored, explainable profiles |
| `find_trials` | Search ClinicalTrials.gov (supports sex filter) |
| `search_papers` | PubMed search by topic + year range, full abstracts |
| `lookup_drug` | FDA drug label lookup by brand or generic name |
| `match_eligibility` | Pre-filter trials by condition, age, and sex |
| `health_check` | Live API connectivity + latency report |

---

## Scoring Model

```
final_score = 100 × (
    0.35 × condition_match       +  # token overlap: condition ↔ trial title
    0.30 × eligibility_fit       +  # age-window centrality (1.0=center, 0.5=edge)
    0.20 × evidence_support      +  # PubMed papers matching condition keywords
    0.15 × trial_phase_maturity     # Phase 3/4=1.0  Phase 2=0.6  Phase 1=0.3
)
```

A patient at the **center** of a trial's age window scores `1.0`. At the **edge**: `0.5`. Open enrollment: `0.75`. Every score is fully auditable via `score_vector` and `explainability_vector` in the response.

---

## Data Sources

| Source | Records | Access |
|--------|---------|--------|
| [ClinicalTrials.gov](https://clinicaltrials.gov/api/v2) | 400,000+ trials | Free, no key |
| [PubMed / NCBI](https://www.ncbi.nlm.nih.gov/home/develop/api/) | 35M+ papers | Free, optional key |
| [openFDA](https://open.fda.gov/apis/) | Drug labels | Free, no key |

> A free PubMed API key raises the rate limit from 3 → 10 requests/second. See `.env.example`.

---

## Architecture

```
src/helix/
├── api.py              FastAPI REST server (:8000)
├── server.py           MCP server (stdio)
├── models.py           Pydantic v2 domain schemas
├── cache.py            Async TTL cache (per-tool TTLs)
├── logger.py           Structured JSON logging → stderr
├── config/             URLs, scoring weights, TTL values
├── clients/            Raw API clients
│   ├── trialsClient.py     curl_cffi Chrome TLS impersonation (WAF bypass)
│   ├── pubmedClient.py     httpx + retry + efetch full abstracts
│   └── fdaClient.py        httpx + retry + 4xx short-circuit
├── tools/              Business logic (all responses cached)
│   ├── synthesis.py        Vector scoring pipeline
│   ├── eligibility.py      Age + sex pre-filter
│   └── trials / pubmed / fda / health
└── utils/
    ├── formatter.py        API response normalizer
    └── synonyms.py         70+ medical abbreviation mappings
tests/
├── unit/               79 assertions — no network, CI-safe
└── tools/              Live smoke tests against real APIs
```

---

## License

MIT — see [LICENSE](LICENSE).
