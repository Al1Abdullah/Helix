"""
Helix REST API — FastAPI layer.
Start: helix-api  OR  python -m helix.api
Docs:  http://localhost:8000/docs
"""
from contextlib import asynccontextmanager
from typing import Literal, Optional
import uvicorn
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from helix.tools.synthesis import synthesizeEvidence
from helix.tools.trials import findTrials
from helix.tools.pubmed import searchPapers
from helix.tools.fda import lookupDrug
from helix.tools.eligibility import matchEligibility
from helix.tools.health import checkHealth
from helix.cache import synthesis_cache, trials_cache, papers_cache, drugs_cache
from helix.config import server as server_config
from helix.config.weights import WEIGHTS


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    for c in [synthesis_cache, trials_cache, papers_cache, drugs_cache]:
        await c.clear()


app = FastAPI(
    title="Helix",
    description="Clinical evidence synthesis engine. Queries ClinicalTrials.gov, PubMed, and openFDA simultaneously. No API key required.",
    version=server_config.version,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

_SEX_DESCRIPTION = "Optional patient sex filter: MALE or FEMALE. Trials requiring the opposite sex are excluded."

_WEIGHT_DESCRIPTIONS = {
    "condition_match":       "Token overlap between patient condition and trial title (0–1)",
    "eligibility_fit":       "Age-window centrality: 1.0=patient at window center, 0.5=at edge, 0.75=open enrollment",
    "evidence_support":      "Fraction of PubMed papers whose title or abstract mentions the condition (0–1)",
    "trial_phase_maturity":  "Phase 3/4=1.0, Phase 2=0.6, Phase 1=0.3, unknown=0.5",
}


class SynthesizeRequest(BaseModel):
    condition: str
    age: int
    location: Optional[str] = None
    sex: Optional[Literal["MALE", "FEMALE"]] = None


class EligibilityRequest(BaseModel):
    condition: str
    age: int
    location: Optional[str] = None
    limit: int = 10
    sex: Optional[Literal["MALE", "FEMALE"]] = None


@app.get("/health", tags=["System"])
async def health():
    """Ping all 3 APIs and report latency per service."""
    return await checkHealth()


@app.get("/score-weights", tags=["System"])
async def score_weights():
    """
    Return the scoring weight vector used to rank clinical trials.
    Enables API consumers to understand and explain trial rankings.
    """
    return {
        "weights": WEIGHTS,
        "formula": "final_score = 100 * sum(weight_i * component_i)",
        "descriptions": _WEIGHT_DESCRIPTIONS,
    }


@app.get("/cache/stats", tags=["System"])
async def cache_stats():
    """Inspect in-memory cache state."""
    return {k: v.stats() for k, v in [
        ("synthesis", synthesis_cache), ("trials", trials_cache),
        ("papers", papers_cache), ("drugs", drugs_cache),
    ]}


@app.delete("/cache", tags=["System"])
async def clear_cache():
    """Flush all caches."""
    for c in [synthesis_cache, trials_cache, papers_cache, drugs_cache]:
        await c.clear()
    return {"cleared": True}


@app.post("/synthesize", tags=["Evidence"])
async def synthesize(req: SynthesizeRequest):
    """
    Full cross-database synthesis with scored, explainable trial profiles.
    Abbreviations like T2D, NSCLC, COPD are automatically expanded.
    """
    return await synthesizeEvidence(req.condition, req.age, req.location, req.sex)


@app.post("/eligibility", tags=["Evidence"])
async def eligibility(req: EligibilityRequest):
    """
    Match patient profile to trials by condition, age, and optional sex.
    Abbreviations are automatically expanded.
    """
    return await matchEligibility(req.condition, req.age, req.location, req.limit, req.sex)


@app.get("/trials", tags=["Data"])
async def trials(
    condition: str = Query(...),
    location: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
):
    """Active recruiting trials on ClinicalTrials.gov."""
    return await findTrials(condition, location, limit)


@app.get("/papers", tags=["Data"])
async def papers(
    topic: str = Query(...),
    yearFrom: Optional[int] = Query(None),
    yearTo: Optional[int] = Query(None),
    limit: int = Query(10, ge=1, le=50),
):
    """PubMed peer-reviewed research papers."""
    return await searchPapers(topic, yearFrom, yearTo, limit)


@app.get("/drugs", tags=["Data"])
async def drugs(
    name: str = Query(...),
    limit: int = Query(5, ge=1, le=20),
):
    """FDA drug label information."""
    return await lookupDrug(name, limit)


def run():
    uvicorn.run("helix.api:app", host="0.0.0.0", port=8000, reload=False, log_level="warning")


if __name__ == "__main__":
    run()
