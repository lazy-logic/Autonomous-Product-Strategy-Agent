"""
============================================================
MRD Agent - Web Search Tools
============================================================
PURPOSE: Perform web searches using Perplexity and Tavily APIs.

KEY DESIGN DECISIONS:
1. Perplexity is primary (best for research synthesis)
2. Tavily is fallback (RAG-optimized, good for specific queries)
3. Both support company disambiguation via search_keywords

TASK 4 REQUIREMENT:
"What happens if 'Sensor Tower' returns no data? Does the whole 
flow crash?"
- Answer: No. We have fallback chains and retry logic.

ERROR HANDLING:
- Retry up to 3 times with exponential backoff
- Fall back to alternative search provider
- Return structured error, don't crash
============================================================
"""

import os
import httpx
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
import asyncio
import logging

from src.models.companies import VerifiedCompany, get_company

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================
# RESPONSE MODELS
# ============================================================

class SearchResult(BaseModel):
    """A single search result."""
    title: str = Field(..., description="Result title")
    url: str = Field(..., description="Result URL")
    snippet: str = Field(..., description="Text snippet")
    published_date: Optional[str] = Field(default=None, description="Publication date")


class SearchResponse(BaseModel):
    """Response from a search operation."""
    success: bool = Field(..., description="Whether search succeeded")
    query: str = Field(..., description="The query that was searched")
    results: list[SearchResult] = Field(default_factory=list, description="Search results")
    answer: Optional[str] = Field(default=None, description="Synthesized answer (Perplexity)")
    sources: list[str] = Field(default_factory=list, description="Source URLs")
    tool_used: str = Field(..., description="Which tool performed the search")
    cost: float = Field(default=0.0, description="API cost estimate")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    retry_count: int = Field(default=0, description="Number of retries")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================
# PERPLEXITY SEARCH
# ============================================================

class PerplexitySearch:
    """
    Perplexity AI search tool.
    
    Best for: Research synthesis, getting comprehensive answers
    Cost: ~$0.005 per query
    
    Uses sonar-pro model for best quality results.
    """
    
    _auth_failed = False

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with API key from env or parameter."""
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise ValueError("PERPLEXITY_API_KEY not found in environment")
        
        self.base_url = "https://api.perplexity.ai"
        self.model = "sonar-pro"  # Best model for research
        self.cost_per_query = 0.005  # Approximate cost
    
    def _build_disambiguated_query(
        self, 
        query: str, 
        company: Optional[VerifiedCompany] = None
    ) -> str:
        """
        Build a query that won't confuse companies.
        
        This is the FIX for the Triumph Motorcycles problem.
        """
        if company:
            # Use the company's search query builder
            return company.get_search_query(query)
        return query
    
    async def search(
        self,
        query: str,
        company_id: Optional[str] = None,
        max_retries: int = 3
    ) -> SearchResponse:
        """
        Perform a search with Perplexity API.
        
        Args:
            query: The search query
            company_id: Optional company ID for disambiguation
            max_retries: Maximum retry attempts
            
        Returns:
            SearchResponse with results or error
        """
        # Fail fast if auth has already failed
        if PerplexitySearch._auth_failed:
             return SearchResponse(
                success=False,
                query=query,
                tool_used="perplexity",
                error="Perplexity disabled due to previous 401 Auth error",
                retry_count=0
            )

        # Get company for disambiguation if provided
        company = get_company(company_id) if company_id else None
        disambiguated_query = self._build_disambiguated_query(query, company)
        
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": self.model,
                            "messages": [
                                {
                                    "role": "system",
                                    "content": (
                                        "You are a market research assistant. "
                                        "Provide accurate, sourced information. "
                                        "Focus on the specific company mentioned, "
                                        "not similarly-named companies."
                                    )
                                },
                                {
                                    "role": "user",
                                    "content": disambiguated_query
                                }
                            ],
                            "return_citations": True
                        }
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Extract answer and citations
                        answer = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                        citations = data.get("citations", [])
                        
                        return SearchResponse(
                            success=True,
                            query=disambiguated_query,
                            results=[],  # Perplexity returns synthesized answer, not results
                            answer=answer,
                            sources=citations,
                            tool_used="perplexity",
                            cost=self.cost_per_query,
                            retry_count=retry_count
                        )
                    elif response.status_code == 401:
                        PerplexitySearch._auth_failed = True
                        last_error = "API error: 401 (Unauthorized) - Disabling Perplexity for this session"
                        break # Don't retry auth errors
                    else:
                        last_error = f"API error: {response.status_code}"
                        
            except httpx.TimeoutException:
                last_error = "Request timed out"
            except Exception as e:
                last_error = str(e)
            
            retry_count += 1
            if retry_count < max_retries:
                # Exponential backoff
                await asyncio.sleep(2 ** retry_count)
        
        return SearchResponse(
            success=False,
            query=disambiguated_query,
            tool_used="perplexity",
            error=last_error,
            retry_count=retry_count
        )
    
    def search_sync(
        self,
        query: str,
        company_id: Optional[str] = None,
        max_retries: int = 3
    ) -> SearchResponse:
        """Synchronous wrapper for search."""
        return asyncio.run(self.search(query, company_id, max_retries))


# ============================================================
# TAVILY SEARCH
# ============================================================

class TavilySearch:
    """
    Tavily search tool.
    
    Best for: Specific queries, RAG-optimized search
    Cost: ~$0.003 per query
    
    Used as fallback when Perplexity fails.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with API key from env or parameter."""
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            logger.warning("TAVILY_API_KEY not found - Tavily search disabled")
            
        self.base_url = "https://api.tavily.com"
        self.cost_per_query = 0.003
    
    def _build_disambiguated_query(
        self, 
        query: str, 
        company: Optional[VerifiedCompany] = None
    ) -> str:
        """Build a query that won't confuse companies."""
        if company:
            return company.get_search_query(query)
        return query
    
    async def search(
        self,
        query: str,
        company_id: Optional[str] = None,
        max_retries: int = 3,
        search_depth: str = "advanced"
    ) -> SearchResponse:
        """
        Perform a search with Tavily API.
        
        Args:
            query: The search query
            company_id: Optional company ID for disambiguation
            max_retries: Maximum retry attempts
            search_depth: 'basic' or 'advanced'
            
        Returns:
            SearchResponse with results or error
        """
        if not self.api_key:
            return SearchResponse(
                success=False,
                query=query,
                tool_used="tavily",
                error="Tavily API key not configured"
            )
        
        company = get_company(company_id) if company_id else None
        disambiguated_query = self._build_disambiguated_query(query, company)
        
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{self.base_url}/search",
                        headers={"Content-Type": "application/json"},
                        json={
                            "api_key": self.api_key,
                            "query": disambiguated_query,
                            "search_depth": search_depth,
                            "include_answer": True,
                            "include_raw_content": False,
                            "max_results": 10
                        }
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        results = [
                            SearchResult(
                                title=r.get("title", ""),
                                url=r.get("url", ""),
                                snippet=r.get("content", ""),
                                published_date=r.get("published_date")
                            )
                            for r in data.get("results", [])
                        ]
                        
                        return SearchResponse(
                            success=True,
                            query=disambiguated_query,
                            results=results,
                            answer=data.get("answer"),
                            sources=[r.url for r in results],
                            tool_used="tavily",
                            cost=self.cost_per_query,
                            retry_count=retry_count
                        )
                    else:
                        last_error = f"API error: {response.status_code}"
                        
            except httpx.TimeoutException:
                last_error = "Request timed out"
            except Exception as e:
                last_error = str(e)
            
            retry_count += 1
            if retry_count < max_retries:
                await asyncio.sleep(2 ** retry_count)
        
        return SearchResponse(
            success=False,
            query=disambiguated_query,
            tool_used="tavily",
            error=last_error,
            retry_count=retry_count
        )
    
    def search_sync(
        self,
        query: str,
        company_id: Optional[str] = None,
        max_retries: int = 3
    ) -> SearchResponse:
        """Synchronous wrapper for search."""
        return asyncio.run(self.search(query, company_id, max_retries))


# ============================================================
# SEARCH WITH FALLBACK
# ============================================================

async def search_with_fallback(
    query: str,
    company_id: Optional[str] = None,
    max_retries: int = 3
) -> SearchResponse:
    """
    Search with automatic fallback to alternative provider.
    
    Order:
    1. Try Tavily first (Best reliability & RAG optimization)
    2. Fall back to Perplexity if Tavily fails
    
    Updated: Switched to Tavily as primary due to 401 auth issues with Perplexity.
    """
    # Try Tavily first (Primary)
    try:
        tavily = TavilySearch()
        # Enable AI answer generation to match Perplexity's behavior
        response = await tavily.search(query, company_id, max_retries)
        if response.success:
            return response
        logger.warning(f"Tavily failed: {response.error}, trying Perplexity")
    except ValueError as e:
        logger.warning(f"Tavily not configured: {e}")

    # Fall back to Perplexity
    try:
        perplexity = PerplexitySearch()
        response = await perplexity.search(query, company_id, max_retries)
        return response
    except ValueError as e:
        logger.warning(f"Tavily not configured: {e}")
    
    # Fall back to Perplexity
    try:
        perplexity = PerplexitySearch()
        response = await perplexity.search(query, company_id, max_retries)
        return response
    except ValueError as e:
        return SearchResponse(
            success=False,
            query=query,
            tool_used="none",
            error=f"No search providers available: {e}"
        )


def search_sync(
    query: str,
    company_id: Optional[str] = None,
    max_retries: int = 3
) -> SearchResponse:
    """Synchronous wrapper for search_with_fallback."""
    return asyncio.run(search_with_fallback(query, company_id, max_retries))
