"""
============================================================
MRD Agent - LangGraph State Models
============================================================
PURPOSE: Define the state that flows through the LangGraph 
         StateGraph orchestrator.

TASK 4 REQUIREMENT:
"How do you manage the state? How does the agent know it has 
enough data to move from 'Research' to 'Synthesis'?"

This module defines:
1. MRDState - The typed state that flows through the graph
2. ResearchTask - Input to research agents
3. ResearchResult - Output from research agents

The state machine transitions are based on these conditions:
- Research → Synthesis: When all required fields are populated
- Synthesis → QA: When MRD draft is complete
- QA → Output: When confidence >= 0.7
- QA → Research: When confidence < 0.7 (self-correction loop)
============================================================
"""

from pydantic import BaseModel, Field
from typing import Optional, Any, Annotated
from datetime import datetime
from enum import Enum
import operator


class AgentPhase(str, Enum):
    """Current phase of the MRD generation process."""
    INITIALIZING = "initializing"
    PLANNING = "planning"
    RESEARCHING = "researching"
    HUMAN_REVIEW = "human_review"
    SYNTHESIZING = "synthesizing"
    QUALITY_ASSURANCE = "quality_assurance"
    COMPLETE = "complete"
    FAILED = "failed"


class ResearchTaskType(str, Enum):
    """Types of research tasks."""
    MARKET_ANALYSIS = "market_analysis"
    COMPETITOR_RESEARCH = "competitor_research"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    REGULATORY_CHECK = "regulatory_check"
    TIKTOK_INFLUENCER = "tiktok_influencer"
    APP_STORE_REVIEWS = "app_store_reviews"
    COMPETITOR_DISCOVERY = "competitor_discovery"  # Uses Exa AI


# ============================================================
# RESEARCH TASK & RESULT MODELS
# ============================================================

class ResearchTask(BaseModel):
    """
    A single research task to be executed by an agent.
    
    Task 4: "Must have: Define the Pydantic models for the 
    ResearchTask inputs."
    """
    
    task_id: str = Field(
        ...,
        description="Unique task identifier"
    )
    task_type: ResearchTaskType = Field(
        ...,
        description="Type of research to perform"
    )
    target_company: Optional[str] = Field(
        default=None,
        description="Company ID to research (from verified database)"
    )
    query: str = Field(
        ...,
        description="The research question to answer"
    )
    required_sources: int = Field(
        default=2,
        ge=1,
        description="Minimum number of sources required"
    )
    priority: int = Field(
        default=1,
        ge=1, le=5,
        description="Priority 1 (highest) to 5 (lowest)"
    )
    max_retries: int = Field(
        default=3,
        description="Maximum retry attempts if tool fails"
    )


class ResearchResult(BaseModel):
    """
    Result from a completed research task.
    
    Task 4: "The 'Loop' logic—how does the agent correct itself 
    if a tool fails or returns empty data?"
    
    The 'success' and 'retry_count' fields enable self-correction.
    """
    
    task_id: str = Field(
        ...,
        description="ID of the completed task"
    )
    task_type: ResearchTaskType = Field(
        ...,
        description="Type of research performed"
    )
    success: bool = Field(
        ...,
        description="Whether the research succeeded"
    )
    data: Optional[dict[str, Any]] = Field(
        default=None,
        description="Research data if successful"
    )
    raw_content: Optional[str] = Field(
        default=None,
        description="Raw text content from research"
    )
    sources: list[str] = Field(
        default_factory=list,
        description="URLs of sources used"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if failed"
    )
    retry_count: int = Field(
        default=0,
        description="Number of retries attempted"
    )
    tool_used: str = Field(
        default="",
        description="Which tool was used (for cost tracking)"
    )
    cost: float = Field(
        default=0.0,
        description="API cost for this research"
    )
    completed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this research completed"
    )


# ============================================================
# MAIN STATE MODEL (LangGraph TypedDict Alternative)
# ============================================================

class StateSummary(BaseModel):
    """Summary of MRD state for logging/display."""
    phase: str
    iteration: int
    research_plan_approved: bool
    research_tasks_total: int
    research_results_success: int
    research_results_failed: int
    has_triumph_data: bool
    has_skillz_data: bool
    has_mrd_draft: bool
    confidence_score: float
    total_cost: float
    tools_used: list[str]
    errors_count: int


class MRDState(BaseModel):
    """
    The main state that flows through the LangGraph StateGraph.
    
    ARCHITECTURE DECISION:
    Using Pydantic instead of TypedDict because:
    1. Task 4 requires Pydantic for type safety
    2. Validation on every state transition
    3. Better error messages when state is invalid
    
    STATE TRANSITIONS:
    The agent knows it has enough data to move forward when:
    - Research → Synthesis: research_results has >= 3 successful results
    - Synthesis → QA: mrd_draft is not None
    - QA → Complete: confidence_score >= 0.7
    - QA → Research: confidence_score < 0.7 AND iteration < 3
    """
    
    # === INPUT ===
    prompt: str = Field(
        ...,
        description="Original user prompt"
    )
    domain: str = Field(
        default="gambling",
        description="Domain vertical"
    )
    
    # === PHASE TRACKING ===
    phase: AgentPhase = Field(
        default=AgentPhase.INITIALIZING,
        description="Current agent phase"
    )
    iteration: int = Field(
        default=0,
        ge=0, le=5,
        description="Current self-correction iteration"
    )
    max_iterations: int = Field(
        default=3,
        description="Maximum self-correction loops"
    )
    
    # === RESEARCH PLAN ===
    research_plan: list[ResearchTask] = Field(
        default_factory=list,
        description="Planned research tasks"
    )
    research_plan_approved: bool = Field(
        default=False,
        description="Has human approved the research plan?"
    )
    
    # === RESEARCH RESULTS ===
    research_results: list[ResearchResult] = Field(
        default_factory=list,
        description="Completed research results"
    )
    
    # === COMPANY DATA ===
    # These are populated from the verified company database
    triumph_data: Optional[dict[str, Any]] = Field(
        default=None,
        description="Researched data about Triumph"
    )
    skillz_data: Optional[dict[str, Any]] = Field(
        default=None,
        description="Researched data about Skillz"
    )
    
    # === SYNTHESIS ===
    mrd_draft: Optional[dict[str, Any]] = Field(
        default=None,
        description="Draft MRD before QA"
    )
    
    # === QUALITY ASSURANCE ===
    qa_feedback: list[str] = Field(
        default_factory=list,
        description="QA feedback items"
    )
    confidence_score: float = Field(
        default=0.0,
        ge=0.0, le=1.0,
        description="Confidence in MRD quality (0-1)"
    )
    
    # === OUTPUT ===
    mrd_output: Optional[dict[str, Any]] = Field(
        default=None,
        description="Final MRD output"
    )
    
    # === COST TRACKING ===
    total_cost: float = Field(
        default=0.0,
        description="Total API cost in USD"
    )
    tools_used: list[str] = Field(
        default_factory=list,
        description="Tools used during research"
    )
    
    # === ERROR TRACKING ===
    errors: list[str] = Field(
        default_factory=list,
        description="Errors encountered during execution"
    )

    # ============================================================
    # STATE TRANSITION HELPERS
    # ============================================================
    
    def has_enough_research(self) -> bool:
        """
        Check if we have enough research to proceed to synthesis.
        
        Criteria:
        - At least 3 successful research results
        - Must have data on both Triumph and Skillz
        """
        successful_results = [r for r in self.research_results if r.success]
        has_triumph = self.triumph_data is not None
        has_skillz = self.skillz_data is not None
        
        return len(successful_results) >= 3 and has_triumph and has_skillz
    
    def should_retry(self) -> bool:
        """
        Check if we should retry research (self-correction loop).
        
        Task 4: "The 'Loop' logic—how does the agent correct itself 
        if a tool fails or returns empty data?"
        """
        return (
            self.confidence_score < 0.7 and 
            self.iteration < self.max_iterations
        )
    
    def get_failed_tasks(self) -> list[ResearchTask]:
        """Get research tasks that failed and should be retried."""
        failed_task_ids = {
            r.task_id for r in self.research_results 
            if not r.success and r.retry_count < 3
        }
        return [t for t in self.research_plan if t.task_id in failed_task_ids]
    
    def add_research_result(self, result: ResearchResult) -> None:
        """Add a research result and update tools_used."""
        self.research_results.append(result)
        if result.tool_used and result.tool_used not in self.tools_used:
            self.tools_used.append(result.tool_used)
        self.total_cost += result.cost
    
    def get_status_summary(self) -> StateSummary:
        """Get a summary of current state for logging/display."""
        return StateSummary(
            phase=self.phase.value,
            iteration=self.iteration,
            research_plan_approved=self.research_plan_approved,
            research_tasks_total=len(self.research_plan),
            research_results_success=len([r for r in self.research_results if r.success]),
            research_results_failed=len([r for r in self.research_results if not r.success]),
            has_triumph_data=self.triumph_data is not None,
            has_skillz_data=self.skillz_data is not None,
            has_mrd_draft=self.mrd_draft is not None,
            confidence_score=self.confidence_score,
            total_cost=self.total_cost,
            tools_used=self.tools_used,
            errors_count=len(self.errors),
        )


# ============================================================
# LANGGRAPH STATE TYPE (for StateGraph)
# ============================================================
# LangGraph requires a TypedDict or Annotated types for state.
# We create a wrapper that provides LangGraph-compatible state.

from typing import TypedDict

class LangGraphState(TypedDict):
    """
    LangGraph-compatible state type.
    
    This is used as the state type for StateGraph.
    The actual data is a serialized MRDState.
    """
    state: dict  # Serialized MRDState


def to_langgraph_state(mrd_state: MRDState) -> LangGraphState:
    """Convert MRDState to LangGraph-compatible state."""
    return {"state": mrd_state.model_dump()}


def from_langgraph_state(lg_state: LangGraphState) -> MRDState:
    """Convert LangGraph state back to MRDState."""
    return MRDState(**lg_state["state"])
