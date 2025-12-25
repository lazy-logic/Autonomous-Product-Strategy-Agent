"""
============================================================
MRD Agent - Agents Package
============================================================
LangGraph-based agent orchestration.

This implements the architecture per Figma MRD-V4 spec:
- Orchestrator (StateGraph)
- Research agents (Market, Competitor, Regulatory)
- Synthesizer (MRD generation)
- Human-in-the-loop (Research plan approval)
============================================================
"""

from src.agents.orchestrator import (
    create_mrd_graph,
    run_mrd_agent,
    run_mrd_agent_sync,
)
from src.agents.researchers import (
    MarketResearcher,
    CompetitorAnalyzer,
    RegulatoryAnalyzer,
)
from src.agents.synthesizer import MRDSynthesizer
from src.agents.human_review import request_approval, display_research_plan

__all__ = [
    # Orchestrator
    "create_mrd_graph",
    "run_mrd_agent",
    "run_mrd_agent_sync",
    # Researchers
    "MarketResearcher",
    "CompetitorAnalyzer",
    "RegulatoryAnalyzer",
    # Synthesizer
    "MRDSynthesizer",
    # Human review
    "request_approval",
    "display_research_plan",
]
