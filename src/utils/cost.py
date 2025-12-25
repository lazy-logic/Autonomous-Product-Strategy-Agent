"""
============================================================
MRD Agent - Cost Tracking
============================================================
PURPOSE: Track API costs across all tools.

This helps monitor and optimize API usage.
============================================================
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class APICall(BaseModel):
    """Record of a single API call."""
    tool: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    cost: float
    tokens_input: Optional[int] = None
    tokens_output: Optional[int] = None
    success: bool = True


class CostSummary(BaseModel):
    """Summary of API costs."""
    total_cost: float
    total_calls: int
    cost_by_tool: dict[str, float]
    calls_by_tool: dict[str, int]
    successful_calls: int
    failed_calls: int


class MRDCostEstimate(BaseModel):
    """Cost estimate for MRD generation."""
    perplexity_search: float
    firecrawl_scraping: float
    sentiment_analysis: float
    regulatory_checks: float
    llm_synthesis: float
    total: float


class CostTracker:
    """
    Track costs across API calls.
    
    Usage:
        tracker = CostTracker()
        tracker.add_call("perplexity", 0.005)
        tracker.add_call("openai", 0.01, tokens_input=500, tokens_output=200)
        print(tracker.get_summary())
    """
    
    def __init__(self):
        self.calls: list[APICall] = []
    
    def add_call(
        self,
        tool: str,
        cost: float,
        tokens_input: Optional[int] = None,
        tokens_output: Optional[int] = None,
        success: bool = True
    ) -> None:
        """Record an API call."""
        self.calls.append(APICall(
            tool=tool,
            cost=cost,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            success=success
        ))
    
    def get_total_cost(self) -> float:
        """Get total cost across all calls."""
        return sum(call.cost for call in self.calls)
    
    def get_cost_by_tool(self) -> dict[str, float]:
        """Get cost breakdown by tool."""
        costs: dict[str, float] = {}
        for call in self.calls:
            if call.tool not in costs:
                costs[call.tool] = 0.0
            costs[call.tool] += call.cost
        return costs
    
    def get_call_count_by_tool(self) -> dict[str, int]:
        """Get call count by tool."""
        counts: dict[str, int] = {}
        for call in self.calls:
            if call.tool not in counts:
                counts[call.tool] = 0
            counts[call.tool] += 1
        return counts
    
    def get_summary(self) -> CostSummary:
        """Get a summary of all costs as Pydantic model."""
        return CostSummary(
            total_cost=self.get_total_cost(),
            total_calls=len(self.calls),
            cost_by_tool=self.get_cost_by_tool(),
            calls_by_tool=self.get_call_count_by_tool(),
            successful_calls=len([c for c in self.calls if c.success]),
            failed_calls=len([c for c in self.calls if not c.success]),
        )
    
    def format_summary(self) -> str:
        """Format summary as readable string."""
        summary = self.get_summary()
        
        lines = [
            "=== API Cost Summary ===",
            f"Total Cost: ${summary.total_cost:.4f}",
            f"Total Calls: {summary.total_calls}",
            f"Successful: {summary.successful_calls}",
            f"Failed: {summary.failed_calls}",
            "",
            "Cost by Tool:",
        ]
        
        for tool, cost in summary.cost_by_tool.items():
            calls = summary.calls_by_tool[tool]
            lines.append(f"  {tool}: ${cost:.4f} ({calls} calls)")
        
        return "\n".join(lines)


# ============================================================
# COST ESTIMATION CONSTANTS
# ============================================================

COST_ESTIMATES: dict[str, float] = {
    # Search tools
    "perplexity": 0.005,
    "tavily": 0.003,
    "exa": 0.004,
    
    # Scraping tools
    "firecrawl": 0.001,
    "jina": 0.0,  # Free tier
    
    # LLM calls
    "openai_gpt4o": 0.01,  # Average per call
    "openai_gpt4o_mini": 0.001,
    "anthropic_claude": 0.015,
    
    # Analysis tools
    "sentiment": 0.002,
    "regulatory": 0.005,
}


def estimate_cost(tool: str, calls: int = 1) -> float:
    """
    Estimate cost for a tool.
    
    Args:
        tool: Tool name
        calls: Number of calls
        
    Returns:
        Estimated cost in USD
    """
    per_call = COST_ESTIMATES.get(tool.lower(), 0.005)
    return per_call * calls


def estimate_mrd_generation_cost() -> MRDCostEstimate:
    """
    Estimate total cost for a complete MRD generation.
    
    Returns:
        MRDCostEstimate Pydantic model with cost breakdown
    """
    perplexity = estimate_cost("perplexity", 5)
    firecrawl = estimate_cost("firecrawl", 4)
    sentiment = estimate_cost("sentiment", 2)
    regulatory = estimate_cost("regulatory", 5)
    llm = estimate_cost("openai_gpt4o", 3)
    
    return MRDCostEstimate(
        perplexity_search=perplexity,
        firecrawl_scraping=firecrawl,
        sentiment_analysis=sentiment,
        regulatory_checks=regulatory,
        llm_synthesis=llm,
        total=perplexity + firecrawl + sentiment + regulatory + llm,
    )

