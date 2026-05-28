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
[![Version](https://img.shields.io/badge/version-1.1.0-111111?style=flat-square)](CHANGELOG.md)

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

### Docker

```bash
docker compose up          # REST API on :8000
# → http://localhost:8000/docs
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
| `GET` | `/papers` | Search PubMed (with full abstracts) |
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

| Tool | Description |
|------|-------------|
| `synthesize_evidence` | Full cross-database synthesis with scored, explainable profiles |
| `find_trials` | Search ClinicalTrials.gov for recruiting trials |
| `search_papers` | Search PubMed by topic + year range (full abstracts) |
| `lookup_drug` | FDA drug label lookup |
| `match_eligibility` | Pre-filter trials by patient age + condition |
| `health_check` | Live API connectivity + latency report |

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

All sub-scores normalized to [0, 1]. Full `score_vector` and `explainability_vector`
returned with every profile — every score is fully auditable.

### eligibility_fit (v1.1.0)

A patient at the **center** of a trial's age window scores **1.0**. A patient at the
**edge** scores **0.5**. Open enrollment (no age constraints) scores **0.75**.
Trials that passed the hard gate but are less tailored to this specific patient
age profile are naturally ranked lower.

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
│   ├── pubmedClient.py     httpx + retry + efetch abstracts
│   └── fdaClient.py        httpx + retry
├── tools/              Business logic layer (cached)
│   ├── synthesis.py        Vector scoring pipeline
│   ├── eligibility.py      Age-based pre-filter
│   ├── trials.py / pubmed.py / fda.py / health.py
└── utils/
    └── formatter.py        API response normalizer
tests/
├── unit/               Fast unit tests (no network, CI-safe)
│   ├── test_formatter.py
│   ├── test_cache.py
│   └── test_scoring.py
└── tools/              Live smoke tests (require network)
```

---

## License

MIT — see [LICENSE](LICENSE).
