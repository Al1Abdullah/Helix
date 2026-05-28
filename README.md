# Helix

An MCP server that gives any AI model instant access to the world's largest free healthcare databases.

Connect Claude, GPT, Gemini, or any MCP-compatible model to ClinicalTrials.gov, PubMed, and the FDA drug database — with a single installation.

---

## What It Does

| Tool | Database | What You Ask |
|---|---|---|
| `find_trials` | ClinicalTrials.gov — 400k+ trials | Find active trials for a condition |
| `search_papers` | PubMed — 35M+ papers | Search peer-reviewed research |
| `lookup_drug` | FDA Drug Database | Get approvals, indications, warnings |
| `match_eligibility` | ClinicalTrials.gov | Match a patient profile to ranked trials |

---

## Installation

```bash
pip install helix-mcp
```

Or clone and install locally:

```bash
git clone https://github.com/Al1Abdullah/Helix.git
cd Helix
pip install -e .
```

---

## Add to Claude Desktop

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "helix": {
      "command": "helix"
    }
  }
}
```

Then ask Claude anything like:

- *"Find recruiting trials for Type 2 Diabetes in London"*
- *"Search for recent Alzheimer's research from 2024"*
- *"Look up FDA information for metformin"*
- *"Match a 45-year-old diabetic patient to eligible trials"*

---

## Tools

### find_trials

condition  : Medical condition to search (required)  
location   : Location filter — city, country (optional)  
limit      : Number of results, default 10  

### search_papers

topic      : Research topic (required)  
yearFrom   : Start year filter (optional)  
yearTo     : End year filter (optional)  
limit      : Number of results, default 10  

### lookup_drug

name       : Brand or generic drug name (required)  
limit      : Number of results, default 5  

### match_eligibility

condition  : Medical condition (required)  
age        : Patient age in years (required)  
location   : Location filter (optional)  
limit      : Number of results, default 10  

---

## Data Sources

All sources are free and public. No API keys required.

- ClinicalTrials.gov — US National Library of Medicine
- PubMed — National Center for Biotechnology Information
- openFDA — US Food and Drug Administration

---

## License

MIT
