```markdown
<div align="center">

<h1>Helix</h1>

<p>An MCP server that gives any AI model direct access to ClinicalTrials.gov, PubMed, and the FDA drug database.</p>

[![License: MIT](https://img.shields.io/badge/License-MIT-000000?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-000000?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-Compatible-000000?style=flat-square)](https://modelcontextprotocol.io)

</div>

---

Helix is a [Model Context Protocol](https://modelcontextprotocol.io) server. Install it once and every MCP-compatible AI model — Claude, GPT, Gemini, Copilot — gains structured access to 400,000+ clinical trials, 35 million research papers, and the complete FDA drug label database.

No API keys. No subscriptions. All data is free and public.

---

## Quick Start

```bash
git clone https://github.com/Al1Abdullah/Helix.git
cd Helix
pip install -e .
```

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "helix": {
      "command": "helix"
    }
  }
}
```

Restart Claude Desktop. Then ask naturally:

> *Find recruiting trials for Type 2 Diabetes in London*
> *Search Alzheimer's research from 2023 onward*
> *Look up FDA information for metformin*
> *Match a 45-year-old diabetic patient to eligible trials*

---

## Tools

| Tool | Database | What it does |
|---|---|---|
| `find_trials` | ClinicalTrials.gov | Find recruiting trials by condition and location |
| `search_papers` | PubMed | Search peer-reviewed research with year filters |
| `lookup_drug` | openFDA | Get drug indications, warnings, and manufacturer |
| `match_eligibility` | ClinicalTrials.gov | Score and rank trials by patient eligibility fit |

---

## Reference

### find_trials

| Parameter | Type | Required | Default |
|---|---|---|---|
| `condition` | string | yes | — |
| `location` | string | no | — |
| `limit` | integer | no | 10 |

### search_papers

| Parameter | Type | Required | Default |
|---|---|---|---|
| `topic` | string | yes | — |
| `yearFrom` | integer | no | — |
| `yearTo` | integer | no | — |
| `limit` | integer | no | 10 |

### lookup_drug

| Parameter | Type | Required | Default |
|---|---|---|---|
| `name` | string | yes | — |
| `limit` | integer | no | 5 |

### match_eligibility

| Parameter | Type | Required | Default |
|---|---|---|---|
| `condition` | string | yes | — |
| `age` | integer | yes | — |
| `location` | string | no | — |
| `limit` | integer | no | 10 |

---

## Data Sources

| Source | Scale | Maintained by |
|---|---|---|
| [ClinicalTrials.gov](https://clinicaltrials.gov) | 400,000+ trials | US National Library of Medicine |
| [PubMed](https://pubmed.ncbi.nlm.nih.gov) | 35M+ papers | National Center for Biotechnology Information |
| [openFDA](https://open.fda.gov) | Full drug label database | US Food and Drug Administration |

---

## Project Structure

```
src/helix/
├── server.py            MCP server, tool registration
├── config.py            All configuration
├── tools/
│   ├── trials.py        find_trials
│   ├── pubmed.py        search_papers
│   ├── fda.py           lookup_drug
│   └── eligibility.py   match_eligibility
├── clients/
│   ├── trialsClient.py
│   ├── pubmedClient.py
│   └── fdaClient.py
└── utils/
    ├── formatter.py     Shapes raw API responses
    └── validator.py     Input validation
```

---

## License

MIT — see [LICENSE](LICENSE)
