# ============================================================
# MRD Agent - Models Package
# ============================================================
# All Pydantic models for type-safe data structures.
# Task 4 Requirement: "Pydantic models define interface between agent steps"
# ============================================================

from src.models.companies import (
    VerifiedCompany, 
    TRIUMPH, 
    SKILLZ, 
    get_company,
    get_all_companies,
    get_focus_companies,
    register_company,
    create_company_from_url,
    create_company_pair,
)
from src.models.mrd import (
    MRDOutput,
    StrategicAnalysis,
    CompetitorProfile,
    SWOTAnalysis,
    FeatureRecommendation,
    RegulatoryAssessment,
)
from src.models.state import MRDState, ResearchTask, ResearchResult

__all__ = [
    # Company database
    "VerifiedCompany",
    "TRIUMPH",
    "SKILLZ",
    "get_company",
    # MRD output models
    "MRDOutput",
    "StrategicAnalysis",
    "CompetitorProfile",
    "SWOTAnalysis",
    "FeatureRecommendation",
    "RegulatoryAssessment",
    # State models
    "MRDState",
    "ResearchTask",
    "ResearchResult",
]
