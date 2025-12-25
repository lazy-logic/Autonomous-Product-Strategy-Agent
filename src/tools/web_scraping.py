"""
============================================================
MRD Agent - Web Scraping Tools
============================================================
PURPOSE: Scrape content from official websites.

CRITICAL FIX (Mark's Feedback):
This tool MUST scrape triumpharcade.com and skillz.com BEFORE
any general research to ensure correct company identification.

TOOLS:
1. Firecrawl - Primary (best for modern SPAs)
2. Jina - Fallback (good for static sites)

Error handling follows Task 4 requirements:
- Retry with exponential backoff
- Fallback to alternative provider
- Return structured error, never crash
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

logger = logging.getLogger(__name__)


# ============================================================
# RESPONSE MODELS
# ============================================================

class ScrapeResult(BaseModel):
    """Result from a scrape operation."""
    success: bool = Field(..., description="Whether scrape succeeded")
    url: str = Field(..., description="URL that was scraped")
    title: Optional[str] = Field(default=None, description="Page title")
    content: Optional[str] = Field(default=None, description="Extracted content")
    markdown: Optional[str] = Field(default=None, description="Content as markdown")
    links: list[str] = Field(default_factory=list, description="Links found on page")
    metadata: dict = Field(default_factory=dict, description="Page metadata")
    tool_used: str = Field(..., description="Which tool performed the scrape")
    cost: float = Field(default=0.0, description="API cost")
    error: Optional[str] = Field(default=None, description="Error if failed")
    retry_count: int = Field(default=0, description="Number of retries")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================
# FIRECRAWL SCRAPER
# ============================================================

class FirecrawlScraper:
    """
    Firecrawl web scraper.
    
    Best for: Modern JavaScript-heavy sites, SPAs
    Cost: ~$0.001 per page
    
    This is used to scrape official websites before research.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with API key from env or parameter."""
        self.api_key = api_key or os.getenv("FIRECRAWL_API_KEY")
        if not self.api_key:
            raise ValueError("FIRECRAWL_API_KEY not found in environment")
        
        self.base_url = "https://api.firecrawl.dev/v0"
        self.cost_per_page = 0.001
    
    async def scrape(
        self,
        url: str,
        max_retries: int = 3
    ) -> ScrapeResult:
        """
        Scrape a URL using Firecrawl API.
        
        Args:
            url: URL to scrape
            max_retries: Maximum retry attempts
            
        Returns:
            ScrapeResult with content or error
        """
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{self.base_url}/scrape",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "url": url,
                            "pageOptions": {
                                "includeHtml": False,
                                "onlyMainContent": True
                            }
                        }
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Extract data from response
                        page_data = data.get("data", {})
                        
                        return ScrapeResult(
                            success=True,
                            url=url,
                            title=page_data.get("title"),
                            content=page_data.get("content"),
                            markdown=page_data.get("markdown"),
                            links=page_data.get("links", []),
                            metadata=page_data.get("metadata", {}),
                            tool_used="firecrawl",
                            cost=self.cost_per_page,
                            retry_count=retry_count
                        )
                    else:
                        last_error = f"API error: {response.status_code} - {response.text}"
                        
            except httpx.TimeoutException:
                last_error = "Request timed out"
            except Exception as e:
                last_error = str(e)
            
            retry_count += 1
            if retry_count < max_retries:
                await asyncio.sleep(2 ** retry_count)
        
        return ScrapeResult(
            success=False,
            url=url,
            tool_used="firecrawl",
            error=last_error,
            retry_count=retry_count
        )
    
    def scrape_sync(self, url: str, max_retries: int = 3) -> ScrapeResult:
        """Synchronous wrapper for scrape."""
        return asyncio.run(self.scrape(url, max_retries))


# ============================================================
# JINA READER (FALLBACK)
# ============================================================

class JinaReader:
    """
    Jina Reader for web content extraction.
    
    Best for: Static sites, clean text extraction
    Cost: Free tier available
    
    Used as fallback when Firecrawl fails.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with optional API key."""
        self.api_key = api_key or os.getenv("JINA_API_KEY")
        # Jina Reader works without API key (with limits)
        self.base_url = "https://r.jina.ai"
        self.cost_per_page = 0.0  # Free tier
    
    async def scrape(
        self,
        url: str,
        max_retries: int = 3
    ) -> ScrapeResult:
        """
        Scrape a URL using Jina Reader.
        
        Args:
            url: URL to scrape
            max_retries: Maximum retry attempts
            
        Returns:
            ScrapeResult with content or error
        """
        retry_count = 0
        last_error = None
        
        # Jina Reader uses URL path format
        jina_url = f"{self.base_url}/{url}"
        
        headers = {"Accept": "text/markdown"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        while retry_count < max_retries:
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.get(jina_url, headers=headers)
                    
                    if response.status_code == 200:
                        markdown_content = response.text
                        
                        # Extract title from first line if possible
                        lines = markdown_content.split('\n')
                        title = None
                        for line in lines[:5]:
                            if line.startswith('# '):
                                title = line[2:].strip()
                                break
                        
                        return ScrapeResult(
                            success=True,
                            url=url,
                            title=title,
                            content=markdown_content,
                            markdown=markdown_content,
                            links=[],  # Jina doesn't extract links separately
                            metadata={},
                            tool_used="jina",
                            cost=self.cost_per_page,
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
        
        return ScrapeResult(
            success=False,
            url=url,
            tool_used="jina",
            error=last_error,
            retry_count=retry_count
        )
    
    def scrape_sync(self, url: str, max_retries: int = 3) -> ScrapeResult:
        """Synchronous wrapper for scrape."""
        return asyncio.run(self.scrape(url, max_retries))


# ============================================================
# SCRAPE WITH FALLBACK
# ============================================================

async def scrape_url(
    url: str,
    max_retries: int = 3
) -> ScrapeResult:
    """
    Scrape URL with automatic fallback.
    
    Order:
    1. Try Firecrawl first (best for SPAs)
    2. Fall back to Jina if Firecrawl fails
    """
    # Try Firecrawl first
    try:
        firecrawl = FirecrawlScraper()
        result = await firecrawl.scrape(url, max_retries)
        if result.success:
            return result
        logger.warning(f"Firecrawl failed: {result.error}, trying Jina")
    except ValueError as e:
        logger.warning(f"Firecrawl not configured: {e}")
    
    # Fall back to Jina
    jina = JinaReader()
    return await jina.scrape(url, max_retries)


def scrape_url_sync(url: str, max_retries: int = 3) -> ScrapeResult:
    """Synchronous wrapper for scrape_url."""
    return asyncio.run(scrape_url(url, max_retries))


# ============================================================
# COMPANY WEBSITE SCRAPER
# ============================================================

async def scrape_company_websites(
    company_ids: list[str] = ["triumph", "skillz"]
) -> dict[str, ScrapeResult]:
    """
    Scrape official websites for verified companies.
    
    This is called at the START of research to establish
    ground truth about the companies.
    
    Args:
        company_ids: List of company IDs to scrape
        
    Returns:
        Dictionary mapping company_id to ScrapeResult
    """
    results = {}
    
    for company_id in company_ids:
        company = get_company(company_id)
        if company:
            logger.info(f"Scraping {company.official_name} at {company.website}")
            result = await scrape_url(company.website)
            results[company_id] = result
            
            if result.success:
                logger.info(f"Successfully scraped {company.website}")
            else:
                logger.warning(f"Failed to scrape {company.website}: {result.error}")
        else:
            logger.warning(f"Company not found: {company_id}")
    
    return results


def scrape_company_websites_sync(
    company_ids: list[str] = ["triumph", "skillz"]
) -> dict[str, ScrapeResult]:
    """Synchronous wrapper for scrape_company_websites."""
    return asyncio.run(scrape_company_websites(company_ids))
