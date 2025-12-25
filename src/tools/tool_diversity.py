"""
============================================================
Tool Diversity Manager
============================================================
PURPOSE: Ensure research uses multiple tools instead of just one.

ADDRESSES GAP: "Tool Diversity" - 85% Perplexity overreliance

This module provides:
1. Round-robin tool selection
2. Parallel multi-tool search
3. Result aggregation from multiple sources

100% PYDANTIC COMPLIANT
============================================================
"""

import asyncio
import logging
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field

from src.tools.web_search import search_with_fallback, SearchResponse, TavilySearch
from src.tools.exa_search import ExaSearchTool, ExaSearchParameters
from src.tools.web_scraping import scrape_url

logger = logging.getLogger(__name__)


class SearchTool(str, Enum):
    """Available search tools."""
    TAVILY = "tavily"
    EXA = "exa"
    FIRECRAWL = "firecrawl"


class ToolUsageTracker(BaseModel):
    """
    Track tool usage to ensure diversity.
    
    Pydantic model for strict type enforcement.
    """
    tavily_count: int = Field(default=0, ge=0, description="Number of Tavily searches")
    exa_count: int = Field(default=0, ge=0, description="Number of Exa searches")
    firecrawl_count: int = Field(default=0, ge=0, description="Number of Firecrawl scrapes")
    total_queries: int = Field(default=0, ge=0, description="Total queries executed")
    
    model_config = {"validate_assignment": True}
    
    def get_next_tool(self) -> SearchTool:
        """Get the least-used tool for the next query."""
        counts = {
            SearchTool.TAVILY: self.tavily_count,
            SearchTool.EXA: self.exa_count,
            SearchTool.FIRECRAWL: self.firecrawl_count,
        }
        # Return tool with lowest count
        return min(counts, key=counts.get)
    
    def record_usage(self, tool: SearchTool) -> None:
        """Record that a tool was used."""
        self.total_queries += 1
        if tool == SearchTool.TAVILY:
            self.tavily_count += 1
        elif tool == SearchTool.EXA:
            self.exa_count += 1
        elif tool == SearchTool.FIRECRAWL:
            self.firecrawl_count += 1
    
    def get_diversity_score(self) -> float:
        """Calculate how evenly distributed tool usage is (0-1)."""
        if self.total_queries == 0:
            return 1.0
        counts = [self.tavily_count, self.exa_count, self.firecrawl_count]
        ideal = self.total_queries / 3
        variance = sum((c - ideal) ** 2 for c in counts) / 3
        max_variance = (self.total_queries ** 2) / 3
        return 1 - (variance / max_variance) if max_variance > 0 else 1.0
    
    def get_summary(self) -> str:
        """Get a summary of tool usage."""
        return (
            f"Tool Usage: Tavily={self.tavily_count}, "
            f"Exa={self.exa_count}, Firecrawl={self.firecrawl_count} "
            f"(Diversity: {self.get_diversity_score():.0%})"
        )


# Global tracker instance
_tracker = ToolUsageTracker()


def get_tracker() -> ToolUsageTracker:
    """Get the global tool usage tracker."""
    return _tracker


def reset_tracker():
    """Reset tool usage for a new session."""
    global _tracker
    _tracker = ToolUsageTracker()


async def search_with_tavily(query: str, company_id: Optional[str] = None) -> SearchResponse:
    """Search using Tavily."""
    _tracker.record_usage(SearchTool.TAVILY)
    return await search_with_fallback(query, company_id)


async def search_with_exa(query: str) -> SearchResponse:
    """Search using Exa AI neural search."""
    _tracker.record_usage(SearchTool.EXA)
    
    try:
        exa = ExaSearchTool()
        params = ExaSearchParameters(
            query=query,
            num_results=5,
            type="neural",
            use_autoprompt=True,
        )
        result = await exa.search(params)
        
        if result.success:
            # Combine results into answer
            content_parts = []
            for r in result.results[:5]:
                content_parts.append(f"**{r.title}**: {r.text[:300] if r.text else ''}")
            
            return SearchResponse(
                success=True,
                query=query,
                results=[],
                answer="\n\n".join(content_parts) if content_parts else None,
                sources=[r.url for r in result.results],
                tool_used="exa",
                cost=result.cost_estimate,
            )
        else:
            return SearchResponse(
                success=False,
                query=query,
                results=[],
                tool_used="exa",
                error=result.error,
            )
    except Exception as e:
        logger.error(f"Exa search failed: {e}")
        return SearchResponse(
            success=False,
            query=query,
            results=[],
            tool_used="exa",
            error=str(e),
        )


async def search_with_scrape(url: str) -> SearchResponse:
    """Scrape a specific URL using Firecrawl."""
    _tracker.record_usage(SearchTool.FIRECRAWL)
    
    try:
        result = await scrape_url(url)
        
        if result.success:
            return SearchResponse(
                success=True,
                query=url,
                results=[],
                answer=result.markdown[:3000] if result.markdown else None,
                sources=[url],
                tool_used="firecrawl",
                cost=result.cost,
            )
        else:
            return SearchResponse(
                success=False,
                query=url,
                results=[],
                tool_used="firecrawl",
                error=result.error,
            )
    except Exception as e:
        logger.error(f"Firecrawl scrape failed: {e}")
        return SearchResponse(
            success=False,
            query=url,
            results=[],
            tool_used="firecrawl",
            error=str(e),
        )


async def diverse_search(
    query: str,
    company_id: Optional[str] = None,
    use_exa: bool = True,
    scrape_url: Optional[str] = None
) -> list[SearchResponse]:
    """
    Perform search across multiple tools for diversity.
    
    This is the MAIN entry point for diverse searching.
    
    Args:
        query: Search query
        company_id: Optional company ID for disambiguation
        use_exa: Whether to also search with Exa
        scrape_url: Optional URL to scrape with Firecrawl
        
    Returns:
        List of SearchResponse from different tools
    """
    tasks = [
        search_with_tavily(query, company_id),
    ]
    
    if use_exa:
        tasks.append(search_with_exa(query))
    
    if scrape_url:
        tasks.append(search_with_scrape(scrape_url))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out exceptions
    valid_results = []
    for r in results:
        if isinstance(r, SearchResponse):
            valid_results.append(r)
        elif isinstance(r, Exception):
            logger.error(f"Search task failed: {r}")
    
    return valid_results


async def multi_tool_research(
    queries: list[str],
    company_id: Optional[str] = None,
) -> list[SearchResponse]:
    """
    Run multiple queries with automatic tool rotation.
    
    Each query will use a different tool to ensure diversity.
    
    Args:
        queries: List of search queries
        company_id: Optional company ID for disambiguation
        
    Returns:
        List of SearchResponse from various tools
    """
    all_results = []
    
    for i, query in enumerate(queries):
        # Rotate tools based on query index
        tool = _tracker.get_next_tool()
        
        if tool == SearchTool.TAVILY:
            result = await search_with_tavily(query, company_id)
        elif tool == SearchTool.EXA:
            result = await search_with_exa(query)
        else:
            # For Firecrawl, we need a URL - fall back to Tavily
            result = await search_with_tavily(query, company_id)
        
        all_results.append(result)
    
    logger.info(_tracker.get_summary())
    
    return all_results


def merge_search_results(results: list[SearchResponse]) -> str:
    """
    Merge multiple search responses into a single content string.
    
    Args:
        results: List of SearchResponse
        
    Returns:
        Combined content from all successful searches
    """
    parts = []
    sources = set()
    
    for r in results:
        if r.success and r.answer:
            parts.append(f"[{r.tool_used.upper()}] {r.answer}")
            sources.update(r.sources)
    
    combined = "\n\n---\n\n".join(parts)
    
    if sources:
        combined += f"\n\nSources: {', '.join(list(sources)[:5])}"
    
    return combined
