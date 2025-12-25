"""
============================================================
MRD Agent - FastAPI Backend
============================================================
PURPOSE: Provide HTTP API for MRD generation.

ENDPOINTS:
- GET  /health            Health check
- POST /generate          Start MRD generation
- GET  /jobs/{job_id}     Get job status/result
- GET  /companies         Get verified companies list

This enables the web frontend to interact with the agent.
============================================================
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Any
from uuid import uuid4
import asyncio
import logging

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.companies import TRIUMPH, SKILLZ, get_all_companies
from src.models.mrd import MRDOutput
from src.agents.orchestrator import run_mrd_agent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================
# REQUEST/RESPONSE MODELS
# ============================================================

class GenerateRequest(BaseModel):
    """Request to generate an MRD."""
    prompt: str = Field(
        ...,
        min_length=10,
        description="The product/market query"
    )
    domain: str = Field(
        default="gambling",
        description="Industry vertical"
    )
    skip_human_review: bool = Field(
        default=True,
        description="Skip HITL for API calls"
    )


class JobStatus(BaseModel):
    """Status of an MRD generation job."""
    job_id: str
    status: str  # pending, running, complete, failed
    created_at: datetime
    completed_at: Optional[datetime] = None
    progress: int = 0  # 0-100
    current_phase: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None


class CompanyInfo(BaseModel):
    """Public company information."""
    id: str
    name: str
    website: str
    industry: str
    description: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    timestamp: datetime


# ============================================================
# JOB STORAGE (In-memory for demo, use Redis in production)
# ============================================================

jobs: dict[str, JobStatus] = {}


# ============================================================
# FASTAPI APP
# ============================================================

def create_app() -> FastAPI:
    """Create and configure the FastAPI app."""
    
    app = FastAPI(
        title="MRD Agent API",
        description="Autonomous Product Strategy Agent for Market Requirements Documents",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Configure CORS for frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    return app


app = create_app()


# ============================================================
# ENDPOINTS
# ============================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="2.0.0",
        timestamp=datetime.utcnow()
    )


@app.get("/companies", response_model=list[CompanyInfo])
async def get_companies():
    """Get list of verified companies."""
    companies = get_all_companies()
    return [
        CompanyInfo(
            id=c.id,
            name=c.official_name,
            website=c.website,
            industry=c.industry,
            description=c.description
        )
        for c in companies
    ]


@app.post("/generate", response_model=JobStatus)
async def generate_mrd(
    request: GenerateRequest,
    background_tasks: BackgroundTasks
):
    """
    Start MRD generation.
    
    Returns a job ID that can be polled for status.
    """
    job_id = uuid4().hex
    
    # Create job record
    job = JobStatus(
        job_id=job_id,
        status="pending",
        created_at=datetime.utcnow(),
        progress=0,
        current_phase="initializing"
    )
    jobs[job_id] = job
    
    # Start background task
    background_tasks.add_task(
        run_generation_task,
        job_id,
        request.prompt,
        request.domain
    )
    
    return job


async def run_generation_task(
    job_id: str,
    prompt: str,
    domain: str
):
    """Background task to run MRD generation."""
    job = jobs.get(job_id)
    if not job:
        return
    
    try:
        job.status = "running"
        job.current_phase = "researching"
        job.progress = 10
        
        # Run the agent
        # Note: For API usage, we'd need to modify orchestrator
        # to skip or auto-approve human review steps
        
        # Simulate progress updates
        job.progress = 30
        job.current_phase = "analyzing competitors"
        
        job.progress = 50
        job.current_phase = "checking regulations"
        
        job.progress = 70
        job.current_phase = "synthesizing"
        
        # For demo, create a sample MRD output
        # In production, this would call run_mrd_agent
        
        from src.models.mrd import (
            MRDOutput, MRDMetadata, StrategicAnalysis,
            MarketSize, AudienceInsight, CompetitorProfile,
            MarketPosition, SWOTAnalysis, SWOTItem,
            FeatureRecommendation, RegulatoryAssessment,
            JurisdictionAssessment, RegulatoryStatus
        )
        
        # Create sample output
        mrd = MRDOutput(
            metadata=MRDMetadata(
                prompt=prompt,
                domain=domain,
                version="2.0.0"
            ),
            strategic_analysis=StrategicAnalysis(
                executive_summary=(
                    f"Analysis of the {domain} market focusing on real-money "
                    "skill gaming. Triumph Labs (triumpharcade.com) is emerging "
                    "as a challenger to the declining Skillz platform. "
                    "Market opportunity exists in the European market with "
                    "proper regulatory compliance."
                ),
                market_size=MarketSize(
                    tam=50000000000,
                    sam=5000000000,
                    cagr=12.5,
                    year=2024
                ),
                target_audience=AudienceInsight(
                    demographic="Males 18-35",
                    behaviors=["Mobile gaming", "Competitive play", "Social sharing"],
                    pain_points=["Slow withdrawals", "Unfair matchmaking"],
                    channels=["TikTok", "Instagram", "YouTube"]
                ),
                key_trends=[
                    "Rise of skill-based gaming over pure gambling",
                    "TikTok as primary user acquisition channel",
                    "Demand for instant withdrawals"
                ],
                market_dynamics="Growing market with regulatory complexity"
            ),
            competitors=[
                CompetitorProfile(
                    name="Triumph Labs, Inc.",
                    website="https://triumpharcade.com",
                    description="Growing skill-based gaming platform",
                    position=MarketPosition.CHALLENGER,
                    target_audience="Males 18-35",
                    key_strengths=["User growth", "TikTok marketing", "Game variety"],
                    key_weaknesses=["Limited international presence"],
                    games_offered=["Pool", "Doodle Jump", "Brick Breaker"]
                ),
                CompetitorProfile(
                    name="Skillz Inc.",
                    website="https://www.skillz.com",
                    description="Declining mobile eSports platform",
                    position=MarketPosition.DECLINING,
                    target_audience="Competitive gamers",
                    key_strengths=["Brand recognition", "Developer network"],
                    key_weaknesses=["Revenue decline", "User complaints", "Stock issues"],
                    games_offered=["Blackout Bingo", "Solitaire Cube"]
                )
            ],
            swot=SWOTAnalysis(
                strengths=[
                    SWOTItem(statement="Skill-based games have legal advantages", impact="high"),
                    SWOTItem(statement="Growing mobile gaming market", impact="high")
                ],
                weaknesses=[
                    SWOTItem(statement="Complex regulatory landscape", impact="high"),
                    SWOTItem(statement="High user acquisition costs", impact="medium")
                ],
                opportunities=[
                    SWOTItem(statement="Underserved European market", impact="high"),
                    SWOTItem(statement="TikTok influencer partnerships", impact="medium")
                ],
                threats=[
                    SWOTItem(statement="Regulatory changes", impact="high"),
                    SWOTItem(statement="Established competitor response", impact="medium")
                ]
            ),
            feature_recommendations=[
                FeatureRecommendation(
                    name="Social Tournaments",
                    description="Allow friends to compete in private tournaments",
                    priority="must_have",
                    rationale="Builds viral growth and retention"
                ),
                FeatureRecommendation(
                    name="Instant Withdrawals",
                    description="Sub-24-hour payout processing",
                    priority="must_have",
                    rationale="Key pain point with competitors"
                ),
                FeatureRecommendation(
                    name="TikTok Integration",
                    description="One-tap gameplay sharing to TikTok",
                    priority="should_have",
                    rationale="Primary acquisition channel for target demo"
                )
            ],
            regulatory=RegulatoryAssessment(
                jurisdictions=[
                    JurisdictionAssessment(
                        jurisdiction="uk",
                        status=RegulatoryStatus.LEGAL_WITH_RESTRICTIONS,
                        licensing_required=True,
                        licensing_authority="UK Gambling Commission"
                    ),
                    JurisdictionAssessment(
                        jurisdiction="germany",
                        status=RegulatoryStatus.LEGAL_WITH_RESTRICTIONS,
                        licensing_required=True
                    )
                ],
                overall_risk_level="medium",
                recommended_launch_markets=["UK", "Malta"],
                markets_to_avoid=["Belgium"]
            ),
            gap_analysis=[
                "IO games (Slither, Agar style)",
                "Word puzzle games",
                "Casual racing games"
            ]
        )
        
        job.progress = 100
        job.status = "complete"
        job.completed_at = datetime.utcnow()
        job.current_phase = "complete"
        job.result = mrd.model_dump()
        
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        job.status = "failed"
        job.error = str(e)


@app.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get status of a generation job."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/jobs/{job_id}/result")
async def get_job_result(job_id: str):
    """Get the result of a completed job."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != "complete":
        raise HTTPException(
            status_code=400, 
            detail=f"Job not complete (status: {job.status})"
        )
    
    return job.result


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
