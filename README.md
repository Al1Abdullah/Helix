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
[![Version](https://img.shields.io/badge/version-1.4.0-111111?style=flat-square)](CHANGELOG.md)

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
helix-api
# → http://localhost:8000/docs
```

### Docker

```bash
docker compose up
# → http://localhost:8000/docs
```

---

## REST API

```bash
helix-api    # starts on :8000
```

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Ping all 3 APIs, get per-service latency |
| `GET` | `/synonyms` | All 70+ recognized medical abbreviations and their expansions |
| `GET` | `/score-weights` | Scoring formula, weight vector, and component descriptions |
| `POST` | `/synthesize` | Full synthesis: scored + ranked trials, excluded trials with reasons |
| `POST` | `/eligibility` | Match patient profile to trials by condition, age, and sex |
| `GET` | `/trials` | Search ClinicalTrials.gov (supports `sex` filter) |
| `GET` | `/papers` | Search PubMed with full abstracts |
| `GET` | `/drugs` | Search openFDA drug labels |
| `GET` | `/cache/stats` | Inspect cache state |
| `DELETE` | `/cache` | Flush all caches |

**Input validation:** `age` is restricted to `[0, 130]`. `condition` must be `1–300` characters. Invalid requests return a 422 with a clear error message.

```bash
# Abbreviations are auto-expanded: T2D → Type 2 Diabetes
curl -X POST http://localhost:8000/synthesize \
  -H "Content-Type: application/json" \
  -d '{"condition": "T2D", "age": 45, "sex": "MALE"}'

# Sex filter on direct trial search
curl "http://localhost:8000/trials?condition=NSCLC&sex=FEMALE&limit=5"
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
| `synthesize_evidence` | Full cross-database synthesis — scored profiles + excluded trial reasons |
| `find_trials` | Search ClinicalTrials.gov (supports `sex` filter) |
| `search_papers` | PubMed search by topic + year range, full abstracts |
| `lookup_drug` | FDA drug label lookup by brand or generic name |
| `match_eligibility` | Pre-filter trials by condition, age, and sex |
| `health_check` | Live API connectivity + per-service latency |

All tools that accept a `condition` support medical abbreviations (`T2D`, `NSCLC`, `COPD`, `afib`, etc.) — they are automatically expanded before any API call.

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

All sub-scores normalized to `[0, 1]`. Every response includes a full `score_vector` and `explainability_vector` — every score is auditable.

A patient at the **center** of a trial's age window scores `1.0` for `eligibility_fit`. At the **edge** they score `0.5`. Open enrollment (no age constraints) scores `0.75`.

Trials that fail hard eligibility checks (age out of range, sex mismatch, missing ID/title) are not silently dropped — they appear in `excludedTrials` with the specific rejection reason.

---

## Data Sources

| Source | Records | Access |
|--------|---------|--------|
| [ClinicalTrials.gov](https://clinicaltrials.gov/api/v2) | 400,000+ trials | Free, no key |
| [PubMed / NCBI](https://www.ncbi.nlm.nih.gov/home/develop/api/) | 35M+ papers | Free, optional key |
| [openFDA](https://open.fda.gov/apis/) | Drug labels | Free, no key |

A free PubMed API key raises the rate limit from 3 to 10 requests/second. See `.env.example`.

---

## Architecture

```
src/helix/
├── api.py              FastAPI REST server
├── server.py           MCP server
├── models.py           Pydantic v2 domain schemas
├── cache.py            Async TTL cache (per-tool TTLs)
├── logger.py           Structured JSON logging → stderr
├── config/             Configuration (URLs, weights, TTLs)
├── clients/            Raw API clients (retry + WAF bypass)
│   ├── trialsClient.py     curl_cffi Chrome TLS impersonation
│   ├── pubmedClient.py     httpx + retry + efetch abstracts
│   └── fdaClient.py        httpx + retry + 4xx short-circuit
├── tools/              Business logic layer (all cached)
│   ├── synthesis.py        Vector scoring pipeline
│   ├── eligibility.py      Age + sex pre-filter
│   ├── trials.py / pubmed.py / fda.py / health.py
└── utils/
    ├── formatter.py        API response normalizer
    └── synonyms.py         70+ medical abbreviation mappings
tests/
├── unit/               Fast unit tests (no network, CI-safe) — 79 assertions
│   ├── test_scoring.py     Scoring functions, hard gate, sex filtering
│   ├── test_formatter.py   Response shaping, field hygiene
│   ├── test_synonyms.py    Abbreviation expansion
│   └── test_cache.py       TTL cache behaviour
└── tools/              Live smoke tests (require network)
```

---

## License

MIT — see [LICENSE](LICENSE).
