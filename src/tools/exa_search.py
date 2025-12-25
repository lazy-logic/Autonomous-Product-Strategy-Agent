"""
============================================================
MRD Agent - Exa (Neural) Search Tool
============================================================
PURPOSE: Perform neural search using Exa AI (formerly Metaphor).

ROLE: "Competitor Discovery Agent"
- Unlike Perplexity (which answers questions), Exa finds *resources*.
- Specific Superpower: "Find companies similar to X" (using embeddings).
- Specific Superpower: "Find PDFs/Whitepapers about Y".

COMPLIANCE: 100% Pydantic input/output models.
============================================================
"""

import os
import httpx
import logging
import asyncio
from typing import Optional, List, Literal
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl

logger = logging.getLogger(__name__)

# ============================================================
# PYDANTIC MODELS (100% Compliance)
# ============================================================

class ExaSearchParameters(BaseModel):
    """Input parameters for an Exa search."""
    query: str = Field(..., description="Natural language query")
    num_results: int = Field(default=5, ge=1, le=20, description="Number of results")
    use_autoprompt: bool = Field(default=True, description="Let Exa optimize the query")
    type: Literal["neural", "keyword"] = Field(default="neural", description="Search type")
    category: Optional[str] = Field(default=None, description="Filter: company, news, pdf, etc.")
    include_domains: Optional[List[str]] = Field(default=None, description="Limit to specific domains")
    exclude_domains: Optional[List[str]] = Field(default=None, description="Exclude specific domains")

class ExaResultItem(BaseModel):
    """A single result from Exa."""
    title: Optional[str] = Field(default=None, description="Page title")
    url: str = Field(..., description="Page URL")
    author: Optional[str] = Field(default=None, description="Author name")
    published_date: Optional[str] = Field(default=None, description="Publication date")
    text: Optional[str] = Field(default=None, description="Extracted clean text")
    score: Optional[float] = Field(default=None, description="Relevance score")

class ExaResponse(BaseModel):
    """Structured response from Exa tool."""
    success: bool = Field(..., description="Whether search succeeded")
    results: List[ExaResultItem] = Field(default_factory=list, description="Found items")
    effective_query: Optional[str] = Field(default=None, description="The autoprompted query used")
    tool_used: str = Field(default="exa_ai", description="Tool identifier")
    cost_estimate: float = Field(default=0.0, description="Estimated API cost")
    error: Optional[str] = Field(default=None, description="Error message if failed")


# ============================================================
# EXA CLIENT
# ============================================================

class ExaSearchTool:
    """
    Exa AI Tool for Competitor Discovery & Resource Finding.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("EXA_API_KEY")
        self.base_url = "https://api.exa.ai"
        
        # approximate cost per 1k results (for tracking)
        # Exa is roughly $10/mo for 1k searches
        self.cost_per_search = 0.01 

    async def search(self, params: ExaSearchParameters) -> ExaResponse:
        """
        Execute a search against Exa API.
        
        Args:
            params: Validated Pydantic search parameters
            
        Returns:
            ExaResponse: Validated Pydantic response
        """
        if not self.api_key:
            return ExaResponse(
                success=False,
                error="EXA_API_KEY not configured in environment"
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "x-api-key": self.api_key # Supports both headers
        }

        # Construct payload
        payload = {
            "query": params.query,
            "numResults": params.num_results,
            "useAutoprompt": params.use_autoprompt,
            "type": params.type,
            "contents": {
                "text": True,  # We want the text content
                "highlights": False
            }
        }
        
        if params.include_domains:
            payload["includeDomains"] = params.include_domains
        if params.exclude_domains:
            payload["excludeDomains"] = params.exclude_domains

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/search",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    return ExaResponse(
                        success=False,
                        error=f"Exa API error {response.status_code}: {response.text}"
                    )
                
                data = response.json()
                
                # Parse results into Pydantic models
                results = []
                for item in data.get("results", []):
                    results.append(ExaResultItem(
                        title=item.get("title"),
                        url=item.get("url"),
                        author=item.get("author"),
                        published_date=item.get("publishedDate"),
                        text=item.get("text", "")[:5000],  # Truncate strictly for memory safety
                        score=item.get("score")
                    ))
                
                return ExaResponse(
                    success=True,
                    results=results,
                    effective_query=data.get("autopromptString"), # Exa returns the optimized query
                    cost_estimate=self.cost_per_search
                )

        except Exception as e:
            logger.error(f"Exa search failed: {e}")
            return ExaResponse(
                success=False,
                error=f"Exception during Exa search: {str(e)}"
            )

    async def find_similar_companies(self, url: str) -> ExaResponse:
        """
        Specialized method: Find competitors using a URL as seed.
        Exa is uniquely good at 'search by URL'.
        """
        # "Find companies that are similar to..."
        query = f"Here is a real-money skill gaming platform: {url}. Find 5 other similar competitor websites."
        
        params = ExaSearchParameters(
            query=query,
            num_results=5,
            use_autoprompt=True,
            type="neural",
            category="company" # Hint for autoprompt
        )
        return await self.search(params)
