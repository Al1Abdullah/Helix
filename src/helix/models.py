"""Helix canonical domain models — Pydantic v2."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class Trial(BaseModel):
    id: str = ""
    title: str = ""
    status: str = ""
    phase: list[str] = Field(default_factory=list)
    summary: str = ""
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    min_age_raw: str = ""
    max_age_raw: str = ""
    sex: str = "ALL"
    contact_name: str = ""
    contact_email: str = ""
    url: str = ""
    model_config = {"extra": "ignore"}


class Paper(BaseModel):
    id: str = ""
    title: str = ""
    abstract: str = ""
    authors: list[str] = Field(default_factory=list)
    journal: str = ""
    year: int = 0
    url: str = ""
    model_config = {"extra": "ignore"}


class Drug(BaseModel):
    brand_name: str = ""
    generic_name: str = ""
    manufacturer: str = ""
    route: list[str] = Field(default_factory=list)
    indications: str = ""
    warnings: str = ""
    model_config = {"extra": "ignore"}


class ScoreVector(BaseModel):
    condition_match: float = 0.0
    eligibility_fit: float = 0.0
    evidence_support: float = 0.0
    trial_phase_maturity: float = 0.0


class ExplainabilityVector(BaseModel):
    condition_overlap_raw: int = 0
    evidence_hits_raw: int = 0
    age_penalty: float = 0.0
    phase_penalty: float = 0.0


class TrialProfile(BaseModel):
    id: str = ""
    title: str = ""
    url: str = ""
    phase: list[str] = Field(default_factory=list)
    final_score: float = 0.0
    score_vector: ScoreVector = Field(default_factory=ScoreVector)
    explainability_vector: ExplainabilityVector = Field(default_factory=ExplainabilityVector)
    risk_flags: list[str] = Field(default_factory=list)


class ClinicalInsight(BaseModel):
    total_trials: int = 0
    top_score: float = 0.0
    average_score: float = 0.0
    condition: str = ""
    expanded_from: Optional[str] = None  # v1.3.0: set when input was an abbreviation


class ExcludedTrial(BaseModel):
    id: str = ""
    title: str = ""
    exclusion_reason: str = ""


class SynthesisResult(BaseModel):
    clinicalInsight: ClinicalInsight = Field(default_factory=ClinicalInsight)
    trialProfiles: list[TrialProfile] = Field(default_factory=list)
    excludedTrials: list[ExcludedTrial] = Field(default_factory=list)


class ServiceHealth(BaseModel):
    status: str
    latency_ms: float = 0.0
    error: Optional[str] = None


class HealthReport(BaseModel):
    status: str
    version: str = ""
    services: dict[str, ServiceHealth] = Field(default_factory=dict)
    timestamp: str = ""
