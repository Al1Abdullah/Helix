<div align="center">

<br/>

# 🧬 Helix

**Clinical evidence synthesis engine — free, no API key, production-grade.**

<br/>

[![CI](https://github.com/Al1Abdullah/Helix/actions/workflows/ci.yml/badge.svg)](https://github.com/Al1Abdullah/Helix/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-22c55e?style=flat-square)](LICENSE)
[![MCP Compatible](https://img.shields.io/badge/MCP-compatible-8b5cf6?style=flat-square)](https://modelcontextprotocol.io)
[![PyPI](https://img.shields.io/badge/PyPI-helix--mcp-f97316?style=flat-square)](https://pypi.org/project/helix-mcp/)
[![Version](https://img.shields.io/badge/version-1.5.0-f97316?style=flat-square)](CHANGELOG.md)
[![HuggingFace](https://img.shields.io/badge/demo-live-yellow?style=flat-square)](https://al1abdullah-helix.hf.space)

<br/>

Give **any AI model** — or any HTTP client — structured, scored access to
the world's three largest free health databases. In a single call.

<br/>

| 400,000+ Clinical Trials | 35M+ PubMed Papers | FDA Drug Labels | < 4s Response |
|:---:|:---:|:---:|:---:|
| ClinicalTrials.gov live | Full abstracts via efetch | openFDA drug information | All 3 databases in parallel |

<br/>

</div>

---

## See It

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
      "title": "PROACT: A Study of REACT in Subjects With Type 2 Diabetes",
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
      "title": "Pediatric Glucose Management Study",
      "exclusion_reason": "age 45 above max 18"
    }
  ]
}
```

Every trial gets a **score vector** showing exactly why it ranked where it did.
Ineligible trials appear in `excludedTrials` with a precise rejection reason — they never silently disappear.

---

## Install

```bash
pip install helix-mcp
```

**REST API**
```bash
helix-api
# → http://localhost:8000/docs
```

**MCP Server (Claude Desktop)**

Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "helix": { "command": "helix" }
  }
}
```

Then ask Claude: *"Find clinical trials for a 52-year-old female with NSCLC in London"*

**Docker**
```bash
docker compose up
```

---

## How It Works

When you call `synthesize_evidence`, Helix:

1. Expands medical abbreviations — `T2D` → `Type 2 Diabetes`, `NSCLC` → `Non-Small Cell Lung Cancer` (70+ mappings)
2. Resolves conditions to authoritative **NLM MeSH terms** before querying PubMed — the same vocabulary PubMed uses internally
3. Queries ClinicalTrials.gov, PubMed, and openFDA **concurrently**
4. Scores every trial using a **BM25 relevance index** built across the full trial corpus
5. Returns ranked profiles with a four-component `score_vector` and an `explainability_vector` showing the raw numbers behind each score

```
Condition input
      ↓
synonym expansion → MeSH resolution
      ↓
ClinicalTrials.gov ──┐
PubMed (MeSH query) ─┼── parallel asyncio.gather
openFDA ─────────────┘
      ↓
BM25 corpus scoring across all trials
      ↓
hard eligibility gate (age + sex)
      ↓
ranked profiles + excluded trials + clinical insight
```

---

## Scoring Formula

```
final_score = 100 × (
    0.35 × condition_match        # BM25 relevance: condition vs trial corpus
  + 0.30 × eligibility_fit        # age-window centrality (1.0=center, 0.5=edge)
  + 0.20 × evidence_support       # fraction of PubMed papers supporting condition
  + 0.15 × trial_phase_maturity   # Phase 3/4=1.0, Phase 2=0.6, Phase 1=0.3
)
```

---

## Tools

| Tool | Description |
|---|---|
| `synthesize_evidence` | Full cross-database synthesis — scored, ranked, explained |
| `find_trials` | Search ClinicalTrials.gov with condition, location, sex, phase |
| `search_papers` | Search PubMed with MeSH-resolved queries, full abstracts |
| `lookup_drug` | FDA drug information by brand or generic name |
| `match_eligibility` | Match a patient profile to trials ranked by eligibility fit |
| `health_check` | Live latency check against all three upstream APIs |

All tools accept medical abbreviations. All tools are cached. All tools never raise.

---

## Data Sources

| Source | Access |
|---|---|
| [ClinicalTrials.gov](https://clinicaltrials.gov/data-api/api) | Free, no key |
| [PubMed E-utilities](https://www.ncbi.nlm.nih.gov/books/NBK25501/) | Free, email optional |
| [openFDA](https://open.fda.gov/apis/) | Free, no key |
| [NLM MeSH API](https://id.nlm.nih.gov/mesh/) | Free, no key |

---

## Development

```bash
git clone https://github.com/Al1Abdullah/Helix.git
cd Helix
pip install -e ".[dev]"
pytest
```

---

## License

MIT — see [LICENSE](LICENSE)
