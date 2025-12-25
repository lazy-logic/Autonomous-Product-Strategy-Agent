"""
============================================================
MRD Agent - LangGraph Orchestrator
============================================================
PURPOSE: Main orchestration using LangGraph StateGraph.

TASK 4 ARCHITECTURE REQUIREMENT:
"The 'Brain': How do you manage the state? How does the agent 
know it has enough data to move from 'Research' to 'Synthesis'?"

ANSWER: Using LangGraph StateGraph with:
- Typed state (MRDState Pydantic model)
- Conditional edges based on state conditions
- Self-correction loop (max 3 iterations)
- Human-in-the-loop checkpoints

FLOW:
1. INIT → Create research plan
2. HUMAN_REVIEW → Get approval for research plan
3. RESEARCH → Execute research tasks (parallel)
4. CHECK_RESEARCH → Verify enough data collected
5. SYNTHESIZE → Generate MRD from research
6. QA → Validate MRD quality
7. If QA fails and iterations < 3 → Back to RESEARCH
8. If QA passes → OUTPUT
============================================================
"""

import os
import json
from typing import Optional, Any, Literal
from datetime import datetime
import asyncio
import logging
from uuid import uuid4

# LangGraph imports
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.models.state import (
    MRDState,
    ResearchTask,
    ResearchResult,
    ResearchTaskType,
    AgentPhase,
    LangGraphState,
    to_langgraph_state,
    from_langgraph_state,
)
from src.models.mrd import MRDOutput
from src.models.companies import TRIUMPH, SKILLZ, get_focus_companies
from src.agents.researchers import (
    MarketResearcher,
    CompetitorAnalyzer,
    RegulatoryAnalyzer,
    run_all_research,
)
from src.agents.synthesizer import MRDSynthesizer
from src.agents.human_review import (
    display_research_plan,
    request_approval,
    display_mrd_preview,
    display_status_update,
    display_success,
    display_error,
    display_final_summary,
)

logger = logging.getLogger(__name__)


# ============================================================
# NODE FUNCTIONS
# ============================================================
# Each function is a node in the LangGraph StateGraph.
# They take the state dict and return updates to state.

def initialize_node(state: dict) -> dict:
    """
    INIT node: Initialize state and create research plan.
    
    Creates a research plan based on the user prompt and
    the verified companies (Triumph, Skillz).
    """
    mrd_state = MRDState(**state["state"])
    
    display_status_update("Initializing MRD Agent...")
    
    # Create research plan
    research_plan = [
        # Market research tasks
        ResearchTask(
            task_id=f"market_size_{uuid4().hex[:8]}",
            task_type=ResearchTaskType.MARKET_ANALYSIS,
            query="Real-money skill gaming market size TAM SAM 2024 2025",
            priority=1
        ),
        ResearchTask(
            task_id=f"market_trends_{uuid4().hex[:8]}",
            task_type=ResearchTaskType.MARKET_ANALYSIS,
            query="Skill-based gaming trends TikTok influencer marketing Gen Z",
            priority=2
        ),
        # Triumph research
        ResearchTask(
            task_id=f"triumph_analysis_{uuid4().hex[:8]}",
            task_type=ResearchTaskType.COMPETITOR_RESEARCH,
            target_company="triumph",
            query="Company overview, games, user growth, funding",
            priority=1
        ),
        ResearchTask(
            task_id=f"triumph_sentiment_{uuid4().hex[:8]}",
            task_type=ResearchTaskType.SENTIMENT_ANALYSIS,
            target_company="triumph",
            query="User reviews, app ratings, social media sentiment",
            priority=2
        ),
        # Skillz research
        ResearchTask(
            task_id=f"skillz_analysis_{uuid4().hex[:8]}",
            task_type=ResearchTaskType.COMPETITOR_RESEARCH,
            target_company="skillz",
            query="Company overview, stock performance, user decline reasons",
            priority=1
        ),
        ResearchTask(
            task_id=f"skillz_sentiment_{uuid4().hex[:8]}",
            task_type=ResearchTaskType.SENTIMENT_ANALYSIS,
            target_company="skillz",
            query="User complaints, negative reviews, pain points",
            priority=2
        ),
        # Comparison research
        ResearchTask(
            task_id=f"comparison_{uuid4().hex[:8]}",
            task_type=ResearchTaskType.COMPETITOR_RESEARCH,
            query="Why Triumph succeeding where Skillz failing",
            priority=1
        ),
        # Exa Deep Resource Search (Neural)
        ResearchTask(
            task_id=f"exa_deep_dive_{uuid4().hex[:8]}",
            task_type=ResearchTaskType.COMPETITOR_DISCOVERY,
            target_company="skillz",
            query="Deep financial analysis and user retention reports for Skillz vs Triumph",
            priority=2
        ),
        # TikTok/Influencer research
        ResearchTask(
            task_id=f"tiktok_{uuid4().hex[:8]}",
            task_type=ResearchTaskType.TIKTOK_INFLUENCER,
            target_company="triumph",
            query="TikTok marketing strategy, influencer partnerships",
            priority=2
        ),
        # Games gap analysis
        ResearchTask(
            task_id=f"games_gap_{uuid4().hex[:8]}",
            task_type=ResearchTaskType.COMPETITOR_RESEARCH,
            query="IO games Triumph doesn't offer, game catalog gaps",
            priority=3
        ),
        # Regulatory research
        ResearchTask(
            task_id=f"regulatory_uk_{uuid4().hex[:8]}",
            task_type=ResearchTaskType.REGULATORY_CHECK,
            query="UK gambling regulations skill gaming legality",
            priority=1
        ),
        ResearchTask(
            task_id=f"regulatory_eu_{uuid4().hex[:8]}",
            task_type=ResearchTaskType.REGULATORY_CHECK,
            query="EU gambling regulations Germany France skill gaming",
            priority=1
        ),
    ]
    
    mrd_state.research_plan = research_plan
    mrd_state.phase = AgentPhase.PLANNING
    
    display_status_update(
        f"Created research plan with {len(research_plan)} tasks",
        f"Targeting: {TRIUMPH.official_name}, {SKILLZ.official_name}"
    )
    
    return {"state": mrd_state.model_dump()}


def human_review_node(state: dict) -> dict:
    """
    HUMAN_REVIEW node: Display plan and get approval.
    
    Task 4: "Show where the 'Human in the Loop' sits 
    (e.g., approving the research plan)"
    """
    mrd_state = MRDState(**state["state"])
    
    # Display the research plan
    
    # NEW: Confirm Company URLs first
    from src.models.companies import TRIUMPH, SKILLZ
    from rich.panel import Panel
    from rich.console import Console
    from rich import box
    console = Console()
    
    console.print(Panel(
        f"[bold]Target Companies Verification[/bold]\n\n"
        f"1. [cyan]{TRIUMPH.official_name}[/cyan]\n"
        f"   URL: {TRIUMPH.website}\n"
        f"   Focus: {TRIUMPH.description[:50]}...\n\n"
        f"2. [cyan]{SKILLZ.official_name}[/cyan]\n"
        f"   URL: {SKILLZ.website}\n"
        f"   Focus: {SKILLZ.description[:50]}...",
        title="Ground Truth Check",
        border_style="yellow",
        box=box.ASCII
    ))
    
    display_research_plan(mrd_state)
    
    # Request approval
    approved = request_approval(
        "[bold green]Are these companies correct and do you approve the plan?[/bold green]",
        default=True
    )
    
    mrd_state.research_plan_approved = approved
    mrd_state.phase = AgentPhase.RESEARCHING if approved else AgentPhase.FAILED
    
    if approved:
        display_success("Target companies confirmed & plan approved!")
    else:
        display_error("Plan rejected by user", recoverable=False)
    
    return {"state": mrd_state.model_dump()}


async def research_node_async(state: dict) -> dict:
    """
    RESEARCH node: Execute all research tasks.
    
    Runs research agents in parallel for efficiency.
    """
    mrd_state = MRDState(**state["state"])
    
    display_status_update(
        f"Starting research (iteration {mrd_state.iteration + 1})..."
    )
    
    mrd_state.iteration += 1
    
    # Run all research
    results, cost = await run_all_research(mrd_state)
    
    # Add results to state
    for result in results:
        mrd_state.add_research_result(result)
    
    # Extract company-specific data
    for result in results:
        if result.success and result.data:
            if result.data.get("company_id") == "triumph":
                mrd_state.triumph_data = result.data
            elif result.data.get("company_id") == "skillz":
                mrd_state.skillz_data = result.data
    
    successful = len([r for r in results if r.success])
    failed = len([r for r in results if not r.success])
    
    display_status_update(
        f"Research complete: {successful} successful, {failed} failed",
        f"Total cost: ${mrd_state.total_cost:.4f}"
    )
    
    return {"state": mrd_state.model_dump()}


def research_node(state: dict) -> dict:
    """Sync wrapper for research node."""
    return asyncio.run(research_node_async(state))


def check_research_node(state: dict) -> dict:
    """
    CHECK_RESEARCH node: Verify we have enough data.
    
    Task 4: "How does the agent know it has enough data 
    to move from 'Research' to 'Synthesis'?"
    
    Answer: Check that we have:
    - At least 3 successful research results
    - Data on both Triumph and Skillz
    """
    mrd_state = MRDState(**state["state"])
    
    has_enough = mrd_state.has_enough_research()
    
    if has_enough:
        mrd_state.phase = AgentPhase.SYNTHESIZING
        display_status_update("Sufficient research data collected")
    else:
        display_status_update(
            "Insufficient research data",
            "Will attempt to fill gaps..."
        )
    
    return {"state": mrd_state.model_dump()}


async def synthesize_node_async(state: dict) -> dict:
    """
    SYNTHESIZE node: Generate MRD from research.
    """
    mrd_state = MRDState(**state["state"])
    
    display_status_update("Synthesizing MRD from research...")
    
    synthesizer = MRDSynthesizer()
    mrd_output = await synthesizer.synthesize(mrd_state)
    
    # Store draft in state
    mrd_state.mrd_draft = mrd_output.model_dump()
    mrd_state.phase = AgentPhase.QUALITY_ASSURANCE
    
    display_status_update("MRD draft generated")
    
    return {"state": mrd_state.model_dump()}


def synthesize_node(state: dict) -> dict:
    """Sync wrapper for synthesize node."""
    return asyncio.run(synthesize_node_async(state))


def qa_node(state: dict) -> dict:
    """
    QA node: Validate MRD quality using Pydantic-based validators.
    
    Checks:
    - All required sections present
    - Minimum content length
    - Data quality (ratings, revenue, etc.)
    - No placeholder text
    - Source URLs valid
    
    Sets confidence_score that determines if we loop back.
    """
    from src.utils.data_validator import validate_mrd_data, validate_and_clean
    
    mrd_state = MRDState(**state["state"])
    
    display_status_update("Running quality assurance checks...")
    
    qa_feedback = []
    score = 1.0  # Start at 100%
    
    if not mrd_state.mrd_draft:
        qa_feedback.append("No MRD draft found")
        score = 0.0
    else:
        draft = mrd_state.mrd_draft
        
        # === NEW: Run Pydantic Data Quality Validator ===
        cleaned_draft, validation_result = validate_and_clean(draft)
        
        # Apply cleaned data
        mrd_state.mrd_draft = cleaned_draft
        
        # Add validation issues to feedback
        for issue in validation_result.issues:
            if issue.severity.value == "error":
                qa_feedback.append(f"❌ {issue.field}: {issue.message}")
            elif issue.severity.value == "warning":
                qa_feedback.append(f"⚠️ {issue.field}: {issue.message}")
        
        # Combine scores
        score = validation_result.quality_score
        
        display_status_update(
            f"Data validation: {validation_result.get_summary()}"
        )
        # === END NEW ===
        
        # Additional structural checks
        strategic = draft.get("strategic_analysis", {})
        if len(strategic.get("executive_summary", "")) < 100:
            qa_feedback.append("Executive summary too short")
            score -= 0.1
        
        competitors = draft.get("competitors", [])
        if len(competitors) < 2:
            qa_feedback.append("Not enough competitor profiles")
            score -= 0.15
        
        swot = draft.get("swot", {})
        for key in ["strengths", "weaknesses", "opportunities", "threats"]:
            if len(swot.get(key, [])) < 2:
                qa_feedback.append(f"SWOT {key} needs more items")
                score -= 0.05
        
        features = draft.get("feature_recommendations", [])
        if len(features) < 3:
            qa_feedback.append("Need more feature recommendations")
            score -= 0.1
        
        regulatory = draft.get("regulatory", {})
        if len(regulatory.get("jurisdictions", [])) < 2:
            qa_feedback.append("Need more jurisdiction assessments")
            score -= 0.1
    
    mrd_state.qa_feedback = qa_feedback
    mrd_state.confidence_score = max(0.0, min(1.0, score))
    
    if mrd_state.confidence_score >= 0.7:
        display_status_update(
            f"QA passed with score {mrd_state.confidence_score:.0%}"
        )
    else:
        display_status_update(
            f"QA score {mrd_state.confidence_score:.0%} below threshold",
            f"Issues: {', '.join(qa_feedback[:3])}"
        )
    
    return {"state": mrd_state.model_dump()}


def output_node(state: dict) -> dict:
    """
    OUTPUT node: Finalize and output MRD.
    """
    mrd_state = MRDState(**state["state"])
    
    # Display preview and get final approval
    approved = display_mrd_preview(mrd_state)
    
    if approved:
        mrd_state.mrd_output = mrd_state.mrd_draft
        mrd_state.phase = AgentPhase.COMPLETE
        display_success("MRD generation complete!")
        display_final_summary(mrd_state)
    else:
        mrd_state.phase = AgentPhase.FAILED
        display_error("MRD rejected by reviewer", recoverable=False)
    
    return {"state": mrd_state.model_dump()}


# ============================================================
# CONDITIONAL EDGES
# ============================================================

def should_continue_after_review(state: dict) -> str:
    """Determine next node after human review."""
    mrd_state = MRDState(**state["state"])
    
    if mrd_state.research_plan_approved:
        return "research"
    else:
        return END


def should_continue_after_qa(state: dict) -> str:
    """
    Determine if we should output or loop back.
    
    Task 4: "The 'Loop' logic—how does the agent correct itself?"
    
    Answer: If confidence < 0.7 and iterations < 3, loop back to research.
    """
    mrd_state = MRDState(**state["state"])
    
    if mrd_state.confidence_score >= 0.7:
        return "output"
    elif mrd_state.iteration < mrd_state.max_iterations:
        display_status_update(
            f"Looping back for more research (iteration {mrd_state.iteration + 1})"
        )
        return "research"
    else:
        display_status_update("Max iterations reached, outputting current result")
        return "output"


# ============================================================
# GRAPH BUILDER
# ============================================================

def create_mrd_graph() -> StateGraph:
    """
    Create the MRD Agent StateGraph.
    
    ARCHITECTURE:
    
    ┌──────────┐     ┌──────────────┐     ┌──────────┐
    │   INIT   │────▶│ HUMAN_REVIEW │────▶│ RESEARCH │
    └──────────┘     └──────────────┘     └──────────┘
                            │                   │
                            │ (rejected)        ▼
                            ▼              ┌──────────────┐
                          [END]            │CHECK_RESEARCH│
                                           └──────────────┘
                                                 │
                                                 ▼
                                           ┌────────────┐
                                           │ SYNTHESIZE │
                                           └────────────┘
                                                 │
                                                 ▼
                           ┌─────────────────┌──────┐
                           │                 │  QA  │
                           │ (score < 0.7)   └──────┘
                           │                    │
                           ▼               (score >= 0.7)
                      ┌──────────┐              │
                      │ RESEARCH │◀─────────────┘
                      └──────────┘              │
                                                ▼
                                           ┌────────┐
                                           │ OUTPUT │
                                           └────────┘
                                                │
                                                ▼
                                              [END]
    """
    # Create graph with state type
    workflow = StateGraph(dict)
    
    # Add nodes
    workflow.add_node("init", initialize_node)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("research", research_node)
    workflow.add_node("check_research", check_research_node)
    workflow.add_node("synthesize", synthesize_node)
    workflow.add_node("qa", qa_node)
    workflow.add_node("output", output_node)
    
    # Add edges
    workflow.add_edge("init", "human_review")
    
    # Conditional edge after human review
    workflow.add_conditional_edges(
        "human_review",
        should_continue_after_review,
        {
            "research": "research",
            END: END
        }
    )
    
    workflow.add_edge("research", "check_research")
    workflow.add_edge("check_research", "synthesize")
    workflow.add_edge("synthesize", "qa")
    
    # Conditional edge after QA (self-correction loop)
    workflow.add_conditional_edges(
        "qa",
        should_continue_after_qa,
        {
            "output": "output",
            "research": "research"
        }
    )
    
    workflow.add_edge("output", END)
    
    # Set entry point
    workflow.set_entry_point("init")
    
    return workflow


# ============================================================
# RUNNER FUNCTIONS
# ============================================================

async def run_mrd_agent(
    prompt: str,
    domain: str = "gambling"
) -> MRDOutput:
    """
    Run the MRD Agent with the given prompt.
    
    Args:
        prompt: User's product/market query
        domain: Industry vertical (default: gambling)
        
    Returns:
        MRDOutput Pydantic model with complete MRD
    """
    logger.info(f"Starting MRD Agent for prompt: {prompt[:100]}...")
    
    # Create initial state
    initial_state = MRDState(
        prompt=prompt,
        domain=domain
    )
    
    # Create graph
    workflow = create_mrd_graph()
    
    # Compile with checkpointer for state persistence
    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)
    
    # Run the graph
    config = {"configurable": {"thread_id": uuid4().hex}}
    
    final_state = None
    async for state in app.astream(
        {"state": initial_state.model_dump()},
        config=config
    ):
        # Get the latest state
        for node_name, node_state in state.items():
            if "state" in node_state:
                final_state = node_state
    
    if final_state and final_state.get("state", {}).get("mrd_output"):
        return MRDOutput(**final_state["state"]["mrd_output"])
    
    # Check if failed phase (e.g. user rejected)
    if final_state and final_state.get("state", {}).get("phase") == AgentPhase.FAILED:
        logger.warning("MRD generation ended in FAILED phase (likely rejected by user)")
        return None
        
    raise RuntimeError("MRD generation failed - no output produced")


def run_mrd_agent_sync(
    prompt: str,
    domain: str = "gambling"
) -> MRDOutput:
    """Synchronous wrapper for run_mrd_agent."""
    return asyncio.run(run_mrd_agent(prompt, domain))


# ============================================================
# CLI INTERFACE
# ============================================================

def main():
    """Command-line interface for MRD Agent."""
    import sys
    from rich.console import Console
    from rich.panel import Panel
    
    console = Console()
    
    console.print(Panel.fit(
        "[bold blue]MRD Agent v2.0.0[/bold blue]\n"
        "Autonomous Product Strategy Agent\n"
        "[dim]Focus: Triumph vs Skillz Analysis[/dim]",
        border_style="blue",
        box=box.ASCII
    ))
    
    # Default prompt if none provided
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = (
            "I want to build a skill-based gambling app targeting young men, "
            "similar to Triumph but for the European market. "
            "Analyze why Triumph is succeeding where Skillz is failing."
        )
    
    console.print(f"\n[bold]Prompt:[/bold] {prompt}\n")
    
    try:
        mrd = run_mrd_agent_sync(prompt)
        
        # Save output
        output_dir = "outputs"
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save JSON
        json_path = f"{output_dir}/mrd_{timestamp}.json"
        with open(json_path, "w") as f:
            f.write(mrd.to_json())
        console.print(f"[green]Saved JSON: {json_path}[/green]")
        
        # Save Markdown summary
        md_path = f"{output_dir}/mrd_{timestamp}.md"
        with open(md_path, "w") as f:
            f.write(f"# Market Requirements Document\n\n")
            f.write(f"**Generated:** {mrd.metadata.generated_at}\n\n")
            f.write(f"**Prompt:** {mrd.metadata.prompt}\n\n")
            f.write(f"## Executive Summary\n\n{mrd.strategic_analysis.executive_summary}\n\n")
            f.write(f"## Competitors\n\n")
            for comp in mrd.competitors:
                f.write(f"### {comp.name}\n{comp.description}\n\n")
        console.print(f"[green]Saved Markdown: {md_path}[/green]")
        
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        raise


if __name__ == "__main__":
    main()
