```markdown
<div align="center">

<br />

```
██╗  ██╗███████╗██╗     ██╗██╗  ██╗
██║  ██║██╔════╝██║     ██║╚██╗██╔╝
███████║█████╗  ██║     ██║ ╚███╔╝ 
██╔══██║██╔══╝  ██║     ██║ ██╔██╗ 
██║  ██║███████╗███████╗██║██╔╝ ██╗
╚═╝  ╚═╝╚══════╝╚══════╝╚═╝╚═╝  ╚═╝
```

**An MCP server that connects any AI model to the world's largest free healthcare databases.**

ClinicalTrials.gov · PubMed · FDA Drug Database

<br />

[![License: MIT](https://img.shields.io/badge/License-MIT-black?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-black?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-Compatible-black?style=flat-square)](https://modelcontextprotocol.io)

</div>

---

## Overview

Helix is a [Model Context Protocol](https://modelcontextprotocol.io) server. Install it once and every MCP-compatible AI model — Claude, GPT, Gemini, Copilot — gains structured access to 400,000+ clinical trials, 35 million research papers, and the complete FDA drug label database.

No API keys. No subscriptions. All data is free and public.

---

## Tools

| Tool | Source | Description |
|---|---|---|
| `find_trials` | ClinicalTrials.gov | Find recruiting trials by condition and location |
| `search_papers` | PubMed | Search peer-reviewed research with year filters |
| `lookup_drug` | openFDA | Get drug indications, warnings, and manufacturer info |
| `match_eligibility` | ClinicalTrials.gov | Rank trials by patient eligibility fit |

---

## Installation

```bash
git clone https://github.com/Al1Abdullah/Helix.git
cd Helix
pip install -e .
```

---

## Usage

### Claude Desktop

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

Restart Claude Desktop. The tools are immediately available.

### Any MCP Client

```bash
helix
```

Helix runs over stdio — compatible with any client that supports the MCP specification.

---

## Example Queries

Once connected, ask your AI model naturally:

```
Find recruiting clinical trials for Type 2 Diabetes in London
```
```
Search for Alzheimer's research published after 2023
```
```
Look up FDA information for metformin
```
```
Match a 45-year-old patient with Type 2 Diabetes to eligible trials
```

---

## Tool Reference

### `find_trials`

```
condition   Medical condition to search              required
location    City or country filter                   optional
limit       Number of results  (default: 10)         optional
```

### `search_papers`

```
topic       Research topic                           required
yearFrom    Start year filter                        optional
yearTo      End year filter                          optional
limit       Number of results  (default: 10)         optional
```

### `lookup_drug`

```
name        Brand or generic drug name               required
limit       Number of results  (default: 5)          optional
```

### `match_eligibility`

```
condition   Medical condition                        required
age         Patient age in years                     required
location    City or country filter                   optional
limit       Number of results  (default: 10)         optional
```

---

## Data Sources

All sources are public and require no authentication.

| Source | Records | Maintained by |
|---|---|---|
| [ClinicalTrials.gov](https://clinicaltrials.gov) | 400,000+ trials | US National Library of Medicine |
| [PubMed](https://pubmed.ncbi.nlm.nih.gov) | 35M+ papers | National Center for Biotechnology Information |
| [openFDA](https://open.fda.gov) | Drug label database | US Food and Drug Administration |

---

## Project Structure

```
src/helix/
├── server.py          — MCP server entry point
├── config.py          — All configuration
├── tools/
│   ├── trials.py      — find_trials
│   ├── pubmed.py      — search_papers
│   ├── fda.py         — lookup_drug
│   └── eligibility.py — match_eligibility
├── clients/
│   ├── trialsClient.py
│   ├── pubmedClient.py
│   └── fdaClient.py
└── utils/
    ├── formatter.py   — Shapes raw API responses
    └── validator.py   — Input validation
```

---

## License

MIT — see [LICENSE](LICENSE)