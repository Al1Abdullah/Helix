<div align="center">

<br>

# Helix

**MCP server connecting any AI model to the world's largest free healthcare databases.**

<br>

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-111111?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-111111?style=flat-square)](LICENSE)
[![MCP Compatible](https://img.shields.io/badge/MCP-compatible-111111?style=flat-square)](https://modelcontextprotocol.io)
[![No API Key](https://img.shields.io/badge/no_API_key-required-111111?style=flat-square)](#data-sources)

<br>

```
 Claude · GPT · Gemini · Copilot · any MCP client
                      │
               ┌──────┴──────┐
               │    Helix    │
               └──────┬──────┘
         ┌────────────┼────────────┐
         ▼            ▼            ▼
  ClinicalTrials    PubMed      openFDA
   400k+ trials   35M papers   Drug labels
```

<br>

</div>

---

Helix is a [Model Context Protocol](https://modelcontextprotocol.io) server. Install it once and every MCP-compatible AI model gains structured, queryable access to three of the largest public healthcare databases on earth — without managing credentials, rate limits, or data wrangling.

---

## Quick Start

```bash
git clone https://github.com/Al1Abdullah/Helix.git
cd Helix
pip install -e .
```

**Claude Desktop** — add to `claude_desktop_config.json` and restart:

```json
{
  "mcpServers": {
    "helix": {
      "command": "helix"
    }
  }
}
```

**Any MCP client** — Helix runs over stdio, compatible with any client that implements the MCP spec:

```bash
helix
```

---

## Tools

| Tool | Database | What it does |
|---|---|---|
| `find_trials` | ClinicalTrials.gov | Find recruiting trials by condition and location |
| `search_papers` | PubMed | Search peer-reviewed research with optional year range |
| `lookup_drug` | openFDA | Get drug approvals, indications, warnings, manufacturer |
| `match_eligibility` | ClinicalTrials.gov | Score and rank trials against a patient profile |

---

## Example Queries

Once connected, prompt your AI model naturally:

```
Find recruiting clinical trials for Type 2 Diabetes in London
```
```
Search Alzheimer's disease research published after 2023
```
```
What does the FDA say about metformin?
```
```
Match a 45-year-old patient with Type 2 Diabetes to eligible trials
```

---

## Output Format

Each tool returns clean, structured objects ready for any model to reason about.

**`find_trials` — one result:**

```json
{
  "id": "NCT04800835",
  "title": "Semaglutide vs Placebo in Patients With Type 2 Diabetes and CKD",
  "status": "RECRUITING",
  "phase": ["PHASE3"],
  "minimumAge": "18 Years",
  "maximumAge": "75 Years",
  "contactName": "Study Coordinator",
  "contactEmail": "trials@site.org",
  "url": "https://clinicaltrials.gov/study/NCT04800835"
}
```

**`match_eligibility` — one result:**

```json
{
  "id": "NCT04800835",
  "title": "Semaglutide vs Placebo in Patients With Type 2 Diabetes and CKD",
  "matchScore": 85,
  "minimumAge": "18 Years",
  "maximumAge": "75 Years",
  "url": "https://clinicaltrials.gov/study/NCT04800835"
}
```

---

## Reference

### `find_trials`

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `condition` | `string` | — | Required. Medical condition to search |
| `location` | `string` | `null` | City or country filter |
| `limit` | `int` | `10` | Max 50 |

### `search_papers`

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `topic` | `string` | — | Required. Research topic |
| `yearFrom` | `int` | `null` | Start year filter |
| `yearTo` | `int` | `null` | End year filter |
| `limit` | `int` | `10` | Max 50 |

### `lookup_drug`

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `name` | `string` | — | Required. Brand or generic drug name |
| `limit` | `int` | `5` | Max 50 |

### `match_eligibility`

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `condition` | `string` | — | Required. Medical condition |
| `age` | `int` | — | Required. Patient age in years |
| `location` | `string` | `null` | City or country filter |
| `limit` | `int` | `10` | Max 50 |

---

## Data Sources

All sources are free, public, and require no authentication.

| Source | Scale | Maintained by |
|---|---|---|
| [ClinicalTrials.gov](https://clinicaltrials.gov) | 400,000+ trials | US National Library of Medicine |
| [PubMed](https://pubmed.ncbi.nlm.nih.gov) | 35M+ papers | National Center for Biotechnology Information |
| [openFDA](https://open.fda.gov) | Full drug label database | US Food and Drug Administration |

---

## Project Structure

```
src/helix/
├── server.py            MCP server entry point, tool registration
├── config.py            All configuration, one place
├── tools/
│   ├── trials.py        find_trials
│   ├── pubmed.py        search_papers
│   ├── fda.py           lookup_drug
│   └── eligibility.py   match_eligibility
├── clients/
│   ├── trialsClient.py  ClinicalTrials.gov API v2
│   ├── pubmedClient.py  NCBI Entrez API
│   └── fdaClient.py     openFDA label API
└── utils/
    ├── formatter.py     Shapes raw API responses into clean objects
    └── validator.py     Input validation via Pydantic
```

---

## License

MIT — see [LICENSE](LICENSE)