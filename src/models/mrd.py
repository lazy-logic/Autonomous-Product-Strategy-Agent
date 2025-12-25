"""
============================================================
MRD Agent - MRD Output Pydantic Models
============================================================
PURPOSE: Define the structured output format for the Market 
         Requirements Document.

TASK 4 REQUIREMENT:
"The final MRD cannot be a blob of text. It must be a strict 
JSON/Object structure (e.g., StrategicAnalysis object containing 
CompetitorList, SWOT, FeatureRecommendations)."

Every model here is designed to be:
1. Database-ready (can be serialized to JSON/stored in DB)
2. Type-safe (Pydantic validation prevents invalid data)
3. Self-documenting (Field descriptions explain purpose)
============================================================
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


# ============================================================
# ENUMS - Constrained choices for structured data
# ============================================================

class ConfidenceLevel(str, Enum):
    """How confident are we in this data point?"""
    HIGH = "high"          # Multiple reliable sources
    MEDIUM = "medium"      # Single reliable source
    LOW = "low"            # Inferred or single weak source
    UNVERIFIED = "unverified"  # Placeholder, needs verification


class MarketPosition(str, Enum):
    """Competitive position in market."""
    LEADER = "leader"
    CHALLENGER = "challenger"
    FOLLOWER = "follower"
    NICHE = "niche"
    DECLINING = "declining"


class RegulatoryStatus(str, Enum):
    """Legal status in a jurisdiction."""
    LEGAL = "legal"
    LEGAL_WITH_RESTRICTIONS = "legal_with_restrictions"
    GRAY_AREA = "gray_area"
    ILLEGAL = "illegal"
    PENDING_LEGISLATION = "pending_legislation"


class Sentiment(str, Enum):
    """Sentiment classification."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    MIXED = "mixed"


# ============================================================
# SOURCE TRACKING - Every claim must have a source
# ============================================================

class DataSource(BaseModel):
    """
    Track where data came from.
    
    Task 4: "Every claim in the MRD is backed by a data source"
    """
    url: Optional[str] = Field(
        default=None,
        description="URL where data was found"
    )
    source_type: str = Field(
        ...,
        description="Type: 'official_website', 'news', 'app_store', 'social_media', 'financial_report'"
    )
    retrieved_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this data was retrieved"
    )
    confidence: ConfidenceLevel = Field(
        default=ConfidenceLevel.MEDIUM,
        description="Confidence in this source"
    )


# ============================================================
# COMPETITOR ANALYSIS MODELS
# ============================================================

class SampleReview(BaseModel):
    """A sample user review from an app store."""
    
    rating: int = Field(..., ge=1, le=5, description="Star rating (1-5)")
    content: str = Field(..., description="Review text content")
    author: Optional[str] = Field(default=None, description="Reviewer name")
    date: Optional[str] = Field(default=None, description="Review date")
    source: str = Field(default="app_store", description="Source: 'app_store' or 'google_play'")


class AppMetrics(BaseModel):
    """App store metrics for a mobile application."""
    
    app_store_rating: Optional[float] = Field(
        default=None,
        ge=0.0, le=5.0,
        description="iOS App Store rating (0-5 stars)"
    )
    play_store_rating: Optional[float] = Field(
        default=None,
        ge=0.0, le=5.0,
        description="Google Play rating (0-5 stars)"
    )
    total_reviews: Optional[int] = Field(
        default=None,
        ge=0,
        description="Total number of reviews across platforms"
    )
    monthly_active_users: Optional[int] = Field(
        default=None,
        description="Estimated MAU (from Sensor Tower or similar)"
    )
    downloads_estimate: Optional[str] = Field(
        default=None,
        description="Download range estimate (e.g., '1M-5M')"
    )
    sample_reviews: list[SampleReview] = Field(
        default_factory=list,
        description="Sample user reviews (up to 3)"
    )


class FinancialMetrics(BaseModel):
    """Financial data for a company."""
    
    revenue_annual: Optional[float] = Field(
        default=None,
        description="Annual revenue in USD"
    )
    revenue_growth_yoy: Optional[float] = Field(
        default=None,
        description="Year-over-year revenue growth percentage"
    )
    funding_total: Optional[float] = Field(
        default=None,
        description="Total funding raised in USD"
    )
    last_funding_round: Optional[str] = Field(
        default=None,
        description="Most recent funding round (e.g., 'Series A')"
    )
    valuation: Optional[float] = Field(
        default=None,
        description="Latest valuation in USD"
    )


class CompetitorProfile(BaseModel):
    """
    Complete profile of a competitor.
    
    This is what gets stored in CompetitorList.
    """
    
    # Identity
    name: str = Field(..., description="Company name")
    website: str = Field(..., description="Official website URL")
    description: str = Field(..., description="One-line description")
    
    # Market position
    position: MarketPosition = Field(
        ..., 
        description="Current market position"
    )
    target_audience: str = Field(
        ...,
        description="Primary target demographic"
    )
    
    # Metrics
    app_metrics: Optional[AppMetrics] = Field(
        default=None,
        description="App store metrics if applicable"
    )
    financials: Optional[FinancialMetrics] = Field(
        default=None,
        description="Financial metrics if available"
    )
    
    # Qualitative
    key_strengths: list[str] = Field(
        default_factory=list,
        min_length=1,
        description="Top 3-5 competitive advantages"
    )
    key_weaknesses: list[str] = Field(
        default_factory=list,
        min_length=1,
        description="Top 3-5 known weaknesses"
    )
    
    # Games/Products (specific to gaming vertical)
    games_offered: list[str] = Field(
        default_factory=list,
        description="List of games/products offered"
    )
    
    # Sources
    sources: list[DataSource] = Field(
        default_factory=list,
        description="Where this data came from"
    )


# ============================================================
# SWOT ANALYSIS MODEL
# ============================================================

class SWOTItem(BaseModel):
    """Single SWOT item with source backing."""
    
    statement: str = Field(
        ...,
        min_length=10,
        description="The SWOT statement"
    )
    impact: str = Field(
        default="medium",
        description="Impact level: high, medium, low"
    )
    source: Optional[DataSource] = Field(
        default=None,
        description="Source backing this claim"
    )


class SWOTAnalysis(BaseModel):
    """
    SWOT Analysis for the target market/product.
    
    Each item must have source backing per Task 4 requirements.
    """
    
    strengths: list[SWOTItem] = Field(
        default_factory=list,
        min_length=2,
        description="Internal strengths"
    )
    weaknesses: list[SWOTItem] = Field(
        default_factory=list,
        min_length=2,
        description="Internal weaknesses"
    )
    opportunities: list[SWOTItem] = Field(
        default_factory=list,
        min_length=2,
        description="External opportunities"
    )
    threats: list[SWOTItem] = Field(
        default_factory=list,
        min_length=2,
        description="External threats"
    )


# ============================================================
# FEATURE RECOMMENDATIONS
# ============================================================

class FeatureRecommendation(BaseModel):
    """
    A recommended feature for the product.
    
    Task 4: Output includes FeatureRecommendations
    """
    
    name: str = Field(
        ...,
        description="Feature name"
    )
    description: str = Field(
        ...,
        min_length=20,
        description="What this feature does"
    )
    priority: str = Field(
        default="medium",
        description="Priority: must_have, should_have, nice_to_have"
    )
    rationale: str = Field(
        ...,
        min_length=20,
        description="Why this feature is recommended"
    )
    effort_estimate: str = Field(
        default="medium",
        description="Implementation effort: low, medium, high"
    )
    competitor_reference: Optional[str] = Field(
        default=None,
        description="Which competitor has this feature (if any)"
    )
    source: Optional[DataSource] = Field(
        default=None,
        description="Source for the recommendation rationale"
    )


# ============================================================
# REGULATORY ASSESSMENT
# ============================================================

class JurisdictionAssessment(BaseModel):
    """Regulatory assessment for a specific jurisdiction."""
    
    jurisdiction: str = Field(
        ...,
        description="Country or region (e.g., 'UK', 'EU', 'Germany')"
    )
    status: RegulatoryStatus = Field(
        ...,
        description="Current legal status"
    )
    key_regulations: list[str] = Field(
        default_factory=list,
        description="Relevant laws/regulations"
    )
    licensing_required: bool = Field(
        default=False,
        description="Is a license required to operate?"
    )
    licensing_authority: Optional[str] = Field(
        default=None,
        description="Which authority grants licenses"
    )
    notes: str = Field(
        default="",
        description="Additional regulatory notes"
    )
    source: Optional[DataSource] = Field(
        default=None,
        description="Source for regulatory info"
    )


class RegulatoryAssessment(BaseModel):
    """
    Complete regulatory assessment across jurisdictions.
    
    Task 4: "Is this model legal in the UK/EU?"
    """
    
    jurisdictions: list[JurisdictionAssessment] = Field(
        default_factory=list,
        description="Assessment by jurisdiction"
    )
    overall_risk_level: str = Field(
        default="medium",
        description="Overall regulatory risk: low, medium, high"
    )
    recommended_launch_markets: list[str] = Field(
        default_factory=list,
        description="Recommended markets to launch in first"
    )
    markets_to_avoid: list[str] = Field(
        default_factory=list,
        description="Markets to avoid or delay entry"
    )


# ============================================================
# MARKET ANALYSIS
# ============================================================

class MarketSize(BaseModel):
    """Market size and growth data."""
    
    tam: Optional[float] = Field(
        default=None,
        description="Total Addressable Market in USD"
    )
    sam: Optional[float] = Field(
        default=None,
        description="Serviceable Addressable Market in USD"
    )
    som: Optional[float] = Field(
        default=None,
        description="Serviceable Obtainable Market in USD"
    )
    cagr: Optional[float] = Field(
        default=None,
        description="Compound Annual Growth Rate percentage"
    )
    year: int = Field(
        default=2024,
        description="Year this data refers to"
    )
    source: Optional[DataSource] = Field(
        default=None,
        description="Source for market data"
    )


class AudienceInsight(BaseModel):
    """Insights about target audience."""
    
    demographic: str = Field(
        ...,
        description="Demographic segment (e.g., 'Males 18-34')"
    )
    behaviors: list[str] = Field(
        default_factory=list,
        description="Key behavioral patterns"
    )
    pain_points: list[str] = Field(
        default_factory=list,
        description="Frustrations with current solutions"
    )
    channels: list[str] = Field(
        default_factory=list,
        description="Where to reach this audience"
    )
    influencer_strategy: Optional[str] = Field(
        default=None,
        description="TikTok/influencer marketing approach"
    )


class StrategicAnalysis(BaseModel):
    """
    Top-level strategic analysis container.
    
    Task 4: "StrategicAnalysis object containing..."
    """
    
    executive_summary: str = Field(
        ...,
        min_length=100,
        description="Executive summary of findings"
    )
    market_size: MarketSize = Field(
        ...,
        description="Market size and growth data"
    )
    target_audience: AudienceInsight = Field(
        ...,
        description="Target audience insights"
    )
    key_trends: list[str] = Field(
        default_factory=list,
        description="Key market trends"
    )
    market_dynamics: str = Field(
        ...,
        description="Current market dynamics and forces"
    )


# ============================================================
# MAIN MRD OUTPUT MODEL
# ============================================================

class MRDMetadata(BaseModel):
    """Metadata about the MRD generation."""
    
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this MRD was generated"
    )
    prompt: str = Field(
        ...,
        description="Original user prompt"
    )
    domain: str = Field(
        default="gambling",
        description="Domain vertical (gambling, saas, healthcare, fintech)"
    )
    version: str = Field(
        default="2.0.0",
        description="MRD Agent version"
    )
    total_research_cost: float = Field(
        default=0.0,
        description="Total API cost in USD"
    )
    tools_used: list[str] = Field(
        default_factory=list,
        description="List of tools that were used"
    )
    iteration_count: int = Field(
        default=1,
        description="Number of self-correction iterations"
    )


class MRDOutput(BaseModel):
    """
    The complete Market Requirements Document output.
    
    This is the MAIN deliverable. It contains all structured data
    that can be saved to a database or exported as JSON.
    
    Task 4: "The final MRD cannot be a blob of text. It must be a 
    strict JSON/Object structure."
    """
    
    # Metadata
    metadata: MRDMetadata = Field(
        ...,
        description="MRD generation metadata"
    )
    
    # Strategic Analysis (Task 4 required)
    strategic_analysis: StrategicAnalysis = Field(
        ...,
        description="High-level strategic analysis"
    )
    
    # Competitor List (Task 4 required)
    competitors: list[CompetitorProfile] = Field(
        default_factory=list,
        min_length=1,
        description="Analyzed competitors"
    )
    
    # SWOT (Task 4 required)
    swot: SWOTAnalysis = Field(
        ...,
        description="SWOT analysis"
    )
    
    # Feature Recommendations (Task 4 required)
    feature_recommendations: list[FeatureRecommendation] = Field(
        default_factory=list,
        min_length=3,
        description="Recommended features for the product"
    )
    
    # Regulatory Assessment (Task 4: UK/EU legality)
    regulatory: RegulatoryAssessment = Field(
        ...,
        description="Regulatory assessment by jurisdiction"
    )
    
    # Gap Analysis (Task 4: What games don't Triumph offer?)
    gap_analysis: list[str] = Field(
        default_factory=list,
        description="Identified gaps in competitor offerings"
    )
    
    # References (Task 4 required: "stated sources")
    references: list[str] = Field(
        default_factory=list,
        description="List of all sources used in this research"
    )
    
    def to_json(self, indent: int = 2) -> str:
        """Export as JSON string."""
        return self.model_dump_json(indent=indent)
    
    def to_dict(self) -> dict:
        """Export as dictionary (database-ready)."""
        return self.model_dump()

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "metadata": {
                    "generated_at": "2024-12-22T12:00:00Z",
                    "prompt": "Skill-based gambling app for EU market",
                    "domain": "gambling"
                },
                "strategic_analysis": {
                    "executive_summary": "The skill-based gaming market..."
                }
            }
        }
