"""
============================================================
App Store Review Mining Tool
============================================================
Addresses GAP: "App Store Review Mining" - ❌ No SerpAPI

This module provides:
1. App Store review retrieval via SerpAPI (with fallback)
2. 1-star review mining for competitor intelligence
3. Zombie app filtering (low reviews = likely dead)
4. Sentiment aggregation from user reviews

Per Figma Design: Review mining is critical for:
- Understanding user pain points
- Competitor weakness identification
- Feature gap discovery
============================================================
"""

import os
import httpx
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime

from src.models.companies import get_company, VerifiedCompany


# ============================================================
# MODELS
# ============================================================

class ReviewSource(str, Enum):
    """Where the review came from."""
    APP_STORE = "app_store"
    GOOGLE_PLAY = "google_play"
    WEB_SEARCH = "web_search"  # Fallback source


class AppReview(BaseModel):
    """Individual app review."""
    source: ReviewSource
    rating: int = Field(ge=1, le=5)
    title: Optional[str] = None
    content: str
    author: Optional[str] = None
    date: Optional[str] = None
    helpful_count: int = 0
    version: Optional[str] = None


class ReviewSummary(BaseModel):
    """Aggregated review analysis."""
    app_name: str
    total_reviews: int
    average_rating: float
    rating_distribution: dict[int, int] = Field(
        default_factory=lambda: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    )
    top_complaints: list[str] = Field(default_factory=list)
    top_praises: list[str] = Field(default_factory=list)
    one_star_themes: list[str] = Field(default_factory=list)
    reviews: list[AppReview] = Field(default_factory=list)  # Added field
    is_zombie_app: bool = False  # True if low/no recent reviews
    source: ReviewSource = ReviewSource.WEB_SEARCH
    source_urls: list[str] = Field(default_factory=list)  # URLs for citation
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================
# SERPAPI CLIENT (Primary)
# ============================================================

class SerpAPIClient:
    """
    SerpAPI client for App Store and Google Play reviews.
    
    Requires SERPAPI_KEY environment variable.
    Falls back to web search if not available.
    """
    
    def __init__(self):
        self.api_key = os.getenv("SERPAPI_KEY", "")
        self.base_url = "https://serpapi.com/search"
        self.available = bool(self.api_key)
    
    async def get_app_store_reviews(
        self,
        app_name: str,
        app_id: Optional[str] = None,
        country: str = "us",
        max_reviews: int = 50
    ) -> list[AppReview]:
        """
        Fetch App Store reviews via SerpAPI.
        
        Args:
            app_name: Name of the app
            app_id: Apple App Store ID (optional)
            country: Country code
            max_reviews: Maximum reviews to fetch
            
        Returns:
            List of AppReview objects
        """
        if not self.available:
            return []
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # 1. Get App ID if missing
                if not app_id:
                    search_params = {
                        "engine": "apple_app_store",
                        "api_key": self.api_key,
                        "term": app_name,
                        "country": country,
                        "num": 1
                    }
                    resp = await client.get(self.base_url, params=search_params)
                    if resp.status_code == 200:
                        data = resp.json()
                        results = data.get("organic_results", [])
                        if results:
                            app_id = str(results[0].get("id"))
                
                if not app_id:
                    return []
                
                # 2. Get Reviews using apple_reviews engine
                params = {
                    "engine": "apple_reviews",  # Correct engine for reviews
                    "api_key": self.api_key,
                    "product_id": app_id,
                    "country": country,
                    "sort": "mostrecent",
                    "num": min(max_reviews, 100),
                }
                
                response = await client.get(self.base_url, params=params)
                
                if response.status_code != 200:
                    return []
                
                data = response.json()
                reviews = []
                
                for review in data.get("reviews", []):
                    reviews.append(AppReview(
                        source=ReviewSource.APP_STORE,
                        rating=review.get("rating", 3),
                        title=review.get("title"),
                        content=review.get("text") or review.get("review", ""), # 'text' or 'review'
                        author=review.get("author", {}).get("name") if isinstance(review.get("author"), dict) else str(review.get("author")),
                        date=review.get("date"),
                        helpful_count=review.get("vote_count", 0), # 'vote_count' usually
                        version=review.get("version")
                    ))
                
                return reviews
                
        except Exception as e:
            print(f"SerpAPI error: {e}")
            return []
    
    async def get_google_play_reviews(
        self,
        app_name: str,
        package_id: Optional[str] = None,
        max_reviews: int = 50
    ) -> list[AppReview]:
        """
        Fetch Google Play reviews via SerpAPI.
        
        Uses google_play_product engine with all_reviews=true as per SerpAPI docs.
        """
        if not self.available:
            print("    [dim]SerpAPI not available for Google Play[/]")
            return []
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # 1. Get Package ID if missing
                if not package_id:
                    print(f"    [dim]Searching Google Play for: {app_name}[/]")
                    search_params = {
                        "engine": "google_play",
                        "api_key": self.api_key,
                        "q": app_name,
                        "store": "apps",
                        "gl": "us",
                        "hl": "en",
                    }
                    resp = await client.get(self.base_url, params=search_params)
                    if resp.status_code == 200:
                        data = resp.json()
                        # Handle both List Type and Rows Type organic results
                        results = data.get("organic_results", [])
                        
                        for result in results:
                            # List Type: items directly under organic_results
                            items = result.get("items", [])
                            if items:
                                package_id = items[0].get("product_id")
                                if package_id:
                                    print(f"    [dim]Found package ID: {package_id}[/]")
                                    break
                        
                        # Also check app_highlight for direct search results
                        if not package_id:
                            app_highlight = data.get("app_highlight", {})
                            if app_highlight:
                                package_id = app_highlight.get("product_id")
                                if package_id:
                                    print(f"    [dim]Found package ID from app_highlight: {package_id}[/]")
                    else:
                        print(f"    [yellow]Google Play search returned status: {resp.status_code}[/]")
                
                if not package_id:
                    print(f"    [yellow]Could not find package ID for: {app_name}[/]")
                    return []
                
                # 2. Get Reviews using google_play_product engine with all_reviews=true
                # Per SerpAPI docs: https://serpapi.com/google-play-reviews
                params = {
                    "engine": "google_play_product",
                    "api_key": self.api_key,
                    "product_id": package_id,
                    "store": "apps",
                    "gl": "us",
                    "hl": "en",
                    "all_reviews": "true",  # Required to get reviews
                    "sort_by": "2",  # 2 = Newest first
                    "num": min(max_reviews, 199),  # Max 199 per SerpAPI docs
                }

                response = await client.get(self.base_url, params=params)
                
                if response.status_code != 200:
                    print(f"    [yellow]Reviews API returned status: {response.status_code}[/]")
                    return []
                
                data = response.json()
                reviews = []
                
                # Reviews are in the "reviews" array
                review_list = data.get("reviews", [])
                print(f"    [dim]Found {len(review_list)} raw reviews from Google Play[/]")
                
                for review in review_list:
                    # Parse author - can be dict or string
                    author = None
                    author_data = review.get("author")
                    if isinstance(author_data, dict):
                        author = author_data.get("name")
                    elif author_data:
                        author = str(author_data)
                    
                    # Get content from snippet or content field
                    content = review.get("snippet") or review.get("content") or review.get("text", "")
                    
                    if content:  # Only add reviews with actual content
                        reviews.append(AppReview(
                            source=ReviewSource.GOOGLE_PLAY,
                            rating=review.get("rating", 3),
                            title=review.get("title"),
                            content=content,
                            author=author,
                            date=review.get("date"),
                            helpful_count=review.get("likes", 0)
                        ))
                
                return reviews
                
        except Exception as e:
            print(f"    [red]SerpAPI Google Play error: {e}[/]")
            import traceback
            traceback.print_exc()
            return []


# ============================================================
# WEB SEARCH FALLBACK
# ============================================================

async def search_reviews_via_web(
    app_name: str,
    company: Optional[VerifiedCompany] = None
) -> list[AppReview]:
    """
    Fallback: Search for app reviews via web search.
    
    Uses Tavily or Perplexity to find review content.
    """
    from src.tools.web_search import search_with_fallback
    
    # Build disambiguated query
    if company:
        query = f"{company.official_name} {company.website} app reviews ratings user feedback"
    else:
        query = f"{app_name} app reviews App Store Google Play user feedback"
    
    result = await search_with_fallback(query)
    
    if not result or not result.success:
        return []
    
    # Parse reviews from search results (simplified)
    reviews = []
    content = result.answer or ""
    
    # Look for review-like content
    # This is a fallback, so we extract what we can
    if content:
        reviews.append(AppReview(
            source=ReviewSource.WEB_SEARCH,
            rating=3,  # Unknown, use neutral
            content=content[:500],  # Truncate
        ))
    
    return reviews


# ============================================================
# 1-STAR REVIEW MINING
# ============================================================

async def mine_one_star_reviews(
    app_name: str,
    company_id: Optional[str] = None
) -> list[AppReview]:
    """
    Specifically target 1-star reviews for competitor intelligence.
    
    Per Figma Design: 1-star reviews reveal:
    - Critical bugs
    - Missing features
    - User frustrations
    - Opportunities for differentiation
    
    Args:
        app_name: Name of the app
        company_id: Optional company ID for disambiguation
        
    Returns:
        List of 1-star reviews with themes extracted
    """
    company = get_company(company_id) if company_id else None
    
    # Get IDs from company to avoid finding wrong apps
    app_store_id = getattr(company, 'app_store_id', None) if company else None
    play_store_id = getattr(company, 'play_store_id', None) if company else None
    
    # Try SerpAPI first
    client = SerpAPIClient()
    one_star_reviews = []
    
    if client.available:
        # Get App Store reviews - use ID if available
        if app_store_id:
            app_store_reviews = await client.get_app_store_reviews(app_name, app_id=app_store_id)
            one_star_reviews.extend([r for r in app_store_reviews if r.rating == 1])
        
        # Get Google Play reviews - only if we have a known ID
        # (avoids finding wrong apps like Triumph Motorcycles)
        if play_store_id:
            play_reviews = await client.get_google_play_reviews(app_name, package_id=play_store_id)
            one_star_reviews.extend([r for r in play_reviews if r.rating == 1])
    
    # Fallback to web search for "complaints" and "problems"
    if not one_star_reviews:
        from src.tools.web_search import search_with_fallback
        
        if company:
            query = f"{company.official_name} {company.website} app complaints problems issues bugs 1-star"
        else:
            query = f"{app_name} app complaints problems issues bugs user reviews negative"
        
        result = await search_with_fallback(query)
        
        if result and result.success:
            one_star_reviews.append(AppReview(
                source=ReviewSource.WEB_SEARCH,
                rating=1,
                content=(result.answer or "")[:1000],
            ))
    
    return one_star_reviews


# ============================================================
# ZOMBIE APP FILTER
# ============================================================

def is_zombie_app(
    review_count: int,
    last_update: Optional[str] = None,
    last_review_date: Optional[str] = None
) -> bool:
    """
    Determine if an app is a "zombie" (abandoned/dead).
    
    Per Figma Design: Filter out zombie apps that:
    - Have very few reviews (< 100)
    - Haven't been updated in 1+ year
    - Have no recent reviews
    
    Args:
        review_count: Total number of reviews
        last_update: Last app update date (YYYY-MM-DD)
        last_review_date: Most recent review date
        
    Returns:
        True if app appears to be a zombie
    """
    # Low review count = likely dead
    if review_count < 100:
        return True
    
    # Check last update
    if last_update:
        try:
            update_date = datetime.fromisoformat(last_update.replace("Z", ""))
            days_since_update = (datetime.utcnow() - update_date).days
            if days_since_update > 365:  # 1 year
                return True
        except ValueError:
            pass
    
    # Check last review date
    if last_review_date:
        try:
            review_date = datetime.fromisoformat(last_review_date.replace("Z", ""))
            days_since_review = (datetime.utcnow() - review_date).days
            if days_since_review > 180:  # 6 months
                return True
        except ValueError:
            pass
    
    return False


# ============================================================
# MAIN FUNCTIONS
# ============================================================

async def get_app_reviews(
    company_id: str,
    include_one_star: bool = True,
    max_reviews: int = 100
) -> ReviewSummary:
    """
    Get comprehensive app review data for a company.
    
    This is the MAIN entry point for app review mining.
    Uses SerpAPI with actual App Store IDs for accurate results.
    
    Args:
        company_id: Company ID (e.g., "triumph", "skillz")
        include_one_star: Whether to specifically mine 1-star reviews
        max_reviews: Maximum reviews to fetch
        
    Returns:
        ReviewSummary with aggregated data
    """
    from rich.console import Console
    console = Console()
    
    company = get_company(company_id)
    
    if not company:
        console.print(f"    [dim]Company not found: {company_id}[/]")
        return ReviewSummary(
            app_name=company_id,
            total_reviews=0,
            average_rating=0.0,
            is_zombie_app=True
        )
    
    # Get app name and IDs from company
    app_name = company.common_names[0] if company.common_names else company.official_name
    app_store_id = getattr(company, 'app_store_id', None)
    play_store_id = getattr(company, 'play_store_id', None)
    
    console.print(f"    [dim]Fetching reviews for: {app_name}[/]")
    
    all_reviews: list[AppReview] = []
    source_urls: list[str] = []
    
    # Try SerpAPI with actual App Store IDs
    client = SerpAPIClient()
    
    if client.available:
        console.print(f"    [cyan]*[/] Using SerpAPI for app reviews")
        
        # 1. Apple App Store
        app_reviews = []
        if app_store_id:
            console.print(f"    [dim]App Store ID: {app_store_id}[/]")
            app_reviews = await client.get_app_store_reviews(app_name, app_id=app_store_id, max_reviews=max_reviews)
            if not app_reviews:
                console.print(f"    [yellow][!][/] ID lookup failed, retrying with name: {app_name}")
                app_reviews = await client.get_app_store_reviews(app_name, max_reviews=max_reviews)
        else:
            app_reviews = await client.get_app_store_reviews(app_name, max_reviews=max_reviews)
            
        console.print(f"    [green][+][/] App Store: {len(app_reviews)} reviews")
        if app_reviews:
            source_urls.append(f"https://apps.apple.com/app/id{app_store_id}" if app_store_id else f"https://www.apple.com/search/{app_name}")
        
        # 2. Google Play Store
        # Only fetch if we have a known play_store_id - prevents finding wrong apps
        if play_store_id:
            play_reviews = await client.get_google_play_reviews(
                app_name, 
                package_id=play_store_id,
                max_reviews=max_reviews
            )
            console.print(f"    [green][+][/] Google Play: {len(play_reviews)} reviews")
            if play_reviews:
                source_urls.append(f"https://play.google.com/store/apps/details?id={play_store_id}")
        else:
            play_reviews = []
            console.print(f"    [dim][-][/] Google Play: N/A (app not on Play Store)")
        
        all_reviews.extend(app_reviews)
        all_reviews.extend(play_reviews)
    else:
        console.print(f"    [yellow][!][/] SerpAPI not available, using web search fallback")
    
    # Fallback to web search
    if not all_reviews:
        console.print(f"    [dim]Falling back to web search...[/]")
        web_reviews = await search_reviews_via_web(app_name, company)
        all_reviews.extend(web_reviews)
        console.print(f"    [green][+][/] Web search: {len(web_reviews)} reviews")
        if web_reviews:
            source_urls.append(f"https://www.google.com/search?q={app_name}+reviews")
    
    # Mine 1-star reviews specifically
    one_star_reviews = []
    if include_one_star:
        one_star_reviews = await mine_one_star_reviews(app_name, company_id)
        if one_star_reviews:
            console.print(f"    [green][+][/] 1-star reviews: {len(one_star_reviews)}")
    
    # Calculate statistics
    total = len(all_reviews)
    avg_rating = 0.0
    distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    
    if total > 0:
        for review in all_reviews:
            distribution[review.rating] = distribution.get(review.rating, 0) + 1
        avg_rating = sum(r.rating for r in all_reviews) / total
    
    # Extract themes from 1-star reviews
    one_star_themes = []
    if one_star_reviews:
        # Simple keyword extraction
        complaint_keywords = ["bug", "crash", "slow", "scam", "rigged", "unfair", "support", "withdrawal", "payout"]
        for review in one_star_reviews:
            content_lower = review.content.lower()
            for keyword in complaint_keywords:
                if keyword in content_lower and keyword not in one_star_themes:
                    one_star_themes.append(keyword)
    
    # Check if zombie
    zombie = is_zombie_app(total)
    
    # Determine source
    source = ReviewSource.WEB_SEARCH
    if all_reviews:
        source = all_reviews[0].source
    
    console.print(f"    [bold]Total: {total} reviews, Avg: {avg_rating:.1f}[/]")
    
    return ReviewSummary(
        app_name=app_name,
        total_reviews=total,
        average_rating=round(avg_rating, 2),
        rating_distribution=distribution,
        source_urls=source_urls,  # Added source_urls
        reviews=all_reviews[:20],  # Keep sample of reviews
        one_star_themes=one_star_themes,
        is_zombie_app=zombie,
        source=source
    )


class ReviewComparison(BaseModel):
    """Comparison of app reviews between two companies."""
    company1: ReviewSummary
    company2: ReviewSummary
    rating_advantage: float
    review_count_ratio: float
    company1_zombie: bool
    company2_zombie: bool


async def compare_app_reviews(
    company1_id: str,
    company2_id: str
) -> ReviewComparison:
    """
    Compare app reviews between two companies.
    
    Useful for competitive analysis.
    
    Args:
        company1_id: First company ID
        company2_id: Second company ID
        
    Returns:
        ReviewComparison Pydantic model with both summaries
    """
    summary1 = await get_app_reviews(company1_id)
    summary2 = await get_app_reviews(company2_id)
    
    return ReviewComparison(
        company1=summary1,
        company2=summary2,
        rating_advantage=summary1.average_rating - summary2.average_rating,
        review_count_ratio=summary1.total_reviews / max(summary2.total_reviews, 1),
        company1_zombie=summary1.is_zombie_app,
        company2_zombie=summary2.is_zombie_app,
    )

