"""
============================================================
MRD Agent - Research Agents
============================================================
PURPOSE: Specialized agents for different research tasks.

AGENTS:
1. MarketResearcher - TAM/SAM, market trends, growth data
2. CompetitorAnalyzer - Company profiles, features, positioning
3. RegulatoryAnalyzer - Compliance checks for target markets
4. CompetitorDiscoveryAgent - Exa AI neural search for deep resources

Each agent uses the verified company database to ensure
correct company identification (fixing the Triumph bug).
============================================================
"""

import os
from typing import Optional, Any
from datetime import datetime
import asyncio
import logging

from src.models.companies import get_company, get_focus_companies, TRIUMPH, SKILLZ
from src.models.state import (
    MRDState, 
    ResearchTask, 
    ResearchResult, 
    ResearchTaskType
)
from src.models.mrd import (
    CompetitorProfile,
    MarketPosition,
    AppMetrics,
    FinancialMetrics,
    MarketSize,
    DataSource,
    ConfidenceLevel,
)
from src.tools.web_search import search_with_fallback
from src.tools.web_scraping import scrape_url, scrape_company_websites
from src.tools.sentiment import analyze_sentiment, SentimentAnalysisResult
from src.tools.regulatory import check_regulatory_compliance
from src.tools.exa_search import ExaSearchTool, ExaSearchParameters
from src.tools.app_reviews import get_app_reviews, compare_app_reviews
from src.tools.influencer import get_influencer_mentions, compare_influencer_presence
from src.tools.tool_diversity import (
    diverse_search, 
    multi_tool_research, 
    merge_search_results,
    get_tracker,
    reset_tracker,
    search_with_exa,
    search_with_tavily,
)

logger = logging.getLogger(__name__)


# ============================================================
# COMPETITOR DISCOVERY AGENT (New for Exa)
# ============================================================

class CompetitorDiscoveryAgent:
    """
    Finds new competitors using Exa AI neural search.
    
    Specific Superpower: "Find companies similar to X"
    """
    
    def __init__(self):
        self.name = "Competitor Discovery Agent"
        self.exa_tool = ExaSearchTool()
        
    async def discover_competitors(self, task: ResearchTask) -> ResearchResult:
        """
        Execute a deep resource search using Exa neural capabilities.
        Focused strictly on the verified comparison (Triumph vs Skillz).
        """
        logger.info(f"Exa running deep neural search: {task.query}")
        
        # Use neural search to find high-quality analysis/reports
        params = ExaSearchParameters(
            query=task.query,
            num_results=5,  # Increased for better coverage
            type="neural",
            use_autoprompt=True,
            # We want in-depth content, often found in news or PDFs
            category="news" 
        )
        exa_response = await self.exa_tool.search(params)
            
        if exa_response.success:
            # Format results into a structured list
            resources_found = []
            for res in exa_response.results:
                resources_found.append(f"- [{res.title}]({res.url}) (Score: {res.score})")
            
            content = f"Exa Deep Search Results for '{task.query}':\n" + "\n".join(resources_found)
            
            return ResearchResult(
                task_id=task.task_id,
                task_type=ResearchTaskType.COMPETITOR_DISCOVERY,
                success=True,
                data={
                    "resources": [r.model_dump() for r in exa_response.results],
                    "query": exa_response.effective_query
                },
                raw_content=content,
                sources=[r.url for r in exa_response.results],
                tool_used="exa_ai",
                cost=exa_response.cost_estimate
            )
        else:
             return ResearchResult(
                task_id=task.task_id,
                task_type=ResearchTaskType.COMPETITOR_DISCOVERY,
                success=False,
                error=exa_response.error
            )


# ============================================================
# MARKET RESEARCHER
# ============================================================

class MarketResearcher:
    """
    Research market size, trends, and dynamics.
    
    Focuses on:
    - TAM/SAM/SOM for skill-based gaming
    - Market growth rates (CAGR)
    - Key market trends
    - Audience demographics
    """
    
    def __init__(self):
        self.name = "Market Researcher"
    
    async def research_market_size(
        self,
        domain: str = "gambling"
    ) -> ResearchResult:
        """
        Research market size for the domain.
        
        Uses DIVERSE tools: Tavily + Exa for better coverage.
        
        Args:
            domain: Industry vertical
            
        Returns:
            ResearchResult with market data
        """
        task_id = f"market_size_{datetime.utcnow().timestamp()}"
        
        # Query 1: General Market Size & Forecast
        query1 = (
            "real-money skill gaming market size TAM SAM 2024 2025 "
            "mobile gaming tournaments cash prizes market growth CAGR "
            "billion dollars market value forecast"
        )
        
        # Query 2: Specific Reports & Data
        query2 = (
            "global skill-based gaming market report 2024 2025 pdf "
            "Skillz vs Triumph market share revenue comparison "
            "real money gaming industry statistics"
        )
        
        # Use DIVERSE search: Tavily for query1, Exa for query2
        r1, r2 = await asyncio.gather(
            search_with_tavily(query1),  # Tavily for general search
            search_with_exa(query2)       # Exa for neural search on reports
        )
        
        if r1.success or r2.success:
            # Combine answers with tool attribution
            combined_answer = (
                f"### Market Overview [Tavily]\n{r1.answer if r1.success else 'No data'}\n\n"
                f"### Industry Reports [Exa]\n{r2.answer if r2.success else 'No data'}"
            )
            
            # Combine sources
            sources = []
            if r1.success: sources.extend(r1.sources)
            if r2.success: sources.extend(r2.sources)
            
            return ResearchResult(
                task_id=task_id,
                task_type=ResearchTaskType.MARKET_ANALYSIS,
                success=True,
                data={
                    "market_query": [query1, query2],
                    "answer": combined_answer,
                    "domain": domain
                },
                raw_content=combined_answer,
                sources=list(set(sources)), # Deduplicate
                tool_used=f"{r1.tool_used}+{r2.tool_used}",
                cost=(r1.cost if r1.success else 0) + (r2.cost if r2.success else 0)
            )
        else:
            return ResearchResult(
                task_id=task_id,
                task_type=ResearchTaskType.MARKET_ANALYSIS,
                success=False,
                error=f"Both searches failed: {r1.error} | {r2.error}",
                retry_count=r1.retry_count + r2.retry_count
            )
    
    async def research_market_trends(
        self,
        domain: str = "gambling"
    ) -> ResearchResult:
        """Research key market trends using diverse tools."""
        task_id = f"market_trends_{datetime.utcnow().timestamp()}"
        
        query1 = (
            "skill-based gaming trends 2024 2025 mobile gaming "
            "real money tournaments esports casual gaming influencer marketing "
            "TikTok gaming Gen Z gaming habits"
        )
        
        query2 = (
            "emerging trends in real money gaming 2025 "
            "impact of crypto on skill gaming "
            "Skillz vs Triumph business model comparison trends"
        )
        
        # DIVERSE: Exa for trends (neural), Tavily for comparisons
        r1, r2 = await asyncio.gather(
            search_with_exa(query1),      # Exa neural search for trends
            search_with_tavily(query2)    # Tavily for business comparisons
        )
        
        if r1.success or r2.success:
            combined_answer = (
                f"### Key Trends [Exa]\n{r1.answer if r1.success else ''}\n\n"
                f"### Emerging & Business Trends [Tavily]\n{r2.answer if r2.success else ''}"
            )
            
            sources = []
            if r1.success: sources.extend(r1.sources)
            if r2.success: sources.extend(r2.sources)

            return ResearchResult(
                task_id=task_id,
                task_type=ResearchTaskType.MARKET_ANALYSIS,
                success=True,
                data={
                    "trends_query": [query1, query2],
                    "answer": combined_answer
                },
                raw_content=combined_answer,
                sources=list(set(sources)),
                tool_used=f"{r1.tool_used}+{r2.tool_used}",
                cost=(r1.cost if r1.success else 0) + (r2.cost if r2.success else 0)
            )
        else:
            return ResearchResult(
                task_id=task_id,
                task_type=ResearchTaskType.MARKET_ANALYSIS,
                success=False,
                error=r1.error or r2.error
            )
    
    async def research_audience(
        self,
        domain: str = "gambling"
    ) -> ResearchResult:
        """
        Research target audience.
        
        Task 4: "Audience: How are they using TikTok/Influencers?"
        """
        task_id = f"audience_{datetime.utcnow().timestamp()}"
        
        # Get Triumph-specific audience data
        triumph = TRIUMPH
        
        query1 = (
            f"{triumph.official_name} {triumph.website} "
            "target audience demographics TikTok influencer marketing "
            "young men gaming mobile app user acquisition strategy"
        )
        
        query2 = (
            "demographics of skill based mobile gamers "
            "who plays skillz vs triumph arcade "
            "psychographics of real money gamers"
        )
        
        # Query 3: TikTok-specific marketing data
        query3 = (
            "Triumph Arcade TikTok marketing strategy influencer partnerships "
            "gaming influencers promoting real money apps Gen Z user acquisition "
            "site:tiktok.com OR site:ads.tiktok.com triumph gaming"
        )
        
        # Run all searches + influencer tool in parallel
        r1, r2, r3, influencer_comparison = await asyncio.gather(
            search_with_fallback(query1, "triumph"),
            search_with_fallback(query2),
            search_with_fallback(query3, "triumph"),
            compare_influencer_presence("triumph", "skillz")
        )
        
        # Format influencer comparison data
        influencer_summary = ""
        if influencer_comparison:
            influencer_summary = (
                f"\n\n### TikTok/Influencer Comparison\n"
                f"**Triumph Mentions:** {influencer_comparison.company1.total_mentions}\n"
                f"**Skillz Mentions:** {influencer_comparison.company2.total_mentions}\n"
                f"**Triumph Platforms:** {', '.join(influencer_comparison.company1_platforms)}\n"
                f"**Triumph Sponsored Content:** {influencer_comparison.company1.sponsored_content_count}\n"
                f"**Key Themes:** {', '.join(influencer_comparison.company1.key_themes)}\n"
            )
        
        if r1.success or r2.success or r3.success:
            combined_answer = (
                f"### Triumph Audience\n{r1.answer if r1.success else ''}\n\n"
                f"### General Market Demographics\n{r2.answer if r2.success else ''}\n\n"
                f"### TikTok Marketing Strategy\n{r3.answer if r3.success else ''}"
                f"{influencer_summary}"
            )
            
            sources = []
            if r1.success: sources.extend(r1.sources)
            if r2.success: sources.extend(r2.sources)
            if r3.success: sources.extend(r3.sources)

            return ResearchResult(
                task_id=task_id,
                task_type=ResearchTaskType.TIKTOK_INFLUENCER,
                success=True,
                data={
                    "audience_query": [query1, query2, query3],
                    "answer": combined_answer,
                    "company": "triumph",
                    "influencer_comparison": {
                        "triumph_mentions": influencer_comparison.company1.total_mentions if influencer_comparison else 0,
                        "skillz_mentions": influencer_comparison.company2.total_mentions if influencer_comparison else 0,
                        "triumph_themes": influencer_comparison.company1.key_themes if influencer_comparison else [],
                    }
                },
                raw_content=combined_answer,
                sources=list(set(sources)),
                tool_used=f"{r1.tool_used}+{r2.tool_used}+{r3.tool_used}+influencer_tool",
                cost=(r1.cost if r1.success else 0) + (r2.cost if r2.success else 0) + (r3.cost if r3.success else 0)
            )
        else:
            return ResearchResult(
                task_id=task_id,
                task_type=ResearchTaskType.TIKTOK_INFLUENCER,
                success=False,
                error=r1.error or r2.error or r3.error
            )
    
    async def run_all(self, domain: str = "gambling") -> list[ResearchResult]:
        """Run all market research tasks."""
        tasks = [
            self.research_market_size(domain),
            self.research_market_trends(domain),
            self.research_audience(domain)
        ]
        return await asyncio.gather(*tasks)


# ============================================================
# COMPETITOR ANALYZER
# ============================================================

class CompetitorAnalyzer:
    """
    Analyze competitors in the market.
    
    For Task 4, focuses specifically on:
    - Triumph (triumpharcade.com) - the successful one
    - Skillz (skillz.com) - the struggling one
    
    Answers: "Why is Triumph succeeding where Skillz is failing?"
    """
    
    def __init__(self):
        self.name = "Competitor Analyzer"
        self.focus_companies = [TRIUMPH, SKILLZ]
    
    async def scrape_official_websites(self) -> dict[str, Any]:
        """
        Scrape official websites first to establish ground truth.
        
        This is the CRITICAL first step that prevents the
        Triumph Motorcycles confusion.
        """
        print("  → Scraping official websites (Ground Truth)...")
        return await scrape_company_websites(["triumph", "skillz"])
    
    async def analyze_company(
        self,
        company_id: str
    ) -> ResearchResult:
        """
        Analyze a single company.
        
        Args:
            company_id: ID from verified company database
            
        Returns:
            ResearchResult with company data
        """
        task_id = f"competitor_{company_id}_{datetime.utcnow().timestamp()}"
        
        company = get_company(company_id)
        if not company:
            return ResearchResult(
                task_id=task_id,
                task_type=ResearchTaskType.COMPETITOR_RESEARCH,
                success=False,
                error=f"Unknown company: {company_id}"
            )
        
        # First, scrape official website
        website_data = await scrape_url(company.website)
        
        # Then, search for additional info
        # Query 1: Business & Financials
        query1 = company.get_search_query(
            "company overview revenue funding investors recent news business model"
        )
        
        # Query 2: Product & Sentiment
        query2 = company.get_search_query(
            "mobile games list features app store ratings user reviews complaints scam allegations"
        )
        
        # Run searches + Sentiment + App Reviews + Influencer in parallel
        r1, r2, sentiment_result, app_reviews, influencer_data = await asyncio.gather(
            search_with_fallback(query1, company_id),
            search_with_fallback(query2, company_id),
            analyze_sentiment(company_id),
            get_app_reviews(company_id),
            get_influencer_mentions(company_id)
        )
        
        # Combine search answers
        combined_search = (
            f"### Business Overview\n{r1.answer if r1.success else ''}\n\n"
            f"### Product & User Sentiment\n{r2.answer if r2.success else ''}"
        )
        
        sources = []
        if website_data.success: sources.append(company.website)
        if r1.success: sources.extend(r1.sources)
        if r2.success: sources.extend(r2.sources)
        
        # Combine data
        data = {
            "company_id": company_id,
            "official_name": company.official_name,
            "website": company.website,
            "website_content": website_data.markdown if website_data.success else None,
            "search_data": combined_search,
            "queries": [query1, query2],
            "sentiment": {
                "overall": sentiment_result.overall_sentiment.value,
                "score": sentiment_result.overall_score,
                "positive_count": sentiment_result.positive_count,
                "negative_count": sentiment_result.negative_count,
            } if sentiment_result.success else None,
            "app_reviews": {
                "total_reviews": app_reviews.total_reviews,
                "average_rating": app_reviews.average_rating,
                "one_star_themes": app_reviews.one_star_themes,
                "is_zombie_app": app_reviews.is_zombie_app,
            } if app_reviews else None,
            "influencer": {
                "total_mentions": influencer_data.total_mentions,
                "platforms": [p.value for p in influencer_data.platforms],
                "sponsored_count": influencer_data.sponsored_content_count,
                "key_themes": influencer_data.key_themes,
            } if influencer_data else None
        }
        
        total_cost = (
            (website_data.cost if website_data.success else 0) +
            (r1.cost if r1.success else 0) +
            (r2.cost if r2.success else 0) +
            (sentiment_result.cost if sentiment_result.success else 0)
        )
        
        return ResearchResult(
            task_id=task_id,
            task_type=ResearchTaskType.COMPETITOR_RESEARCH,
            success=True,
            data=data,
            raw_content=str(data),
            sources=list(set(sources)),
            tool_used="multi_tool_enhanced",
            cost=total_cost
        )
    
    async def compare_companies(self) -> ResearchResult:
        """
        Compare Triumph vs Skillz.
        
        Task 4: "Why is Triumph succeeding where Skillz is failing?"
        """
        task_id = f"comparison_{datetime.utcnow().timestamp()}"
        
        # Get both company names correctly
        triumph = TRIUMPH
        skillz = SKILLZ
        
        query1 = (
            f"{triumph.official_name} versus {skillz.official_name} comparison "
            f"real-money skill gaming why {triumph.official_name} growing "
            f"{skillz.official_name} declining SKLZ stock performance"
        )
        
        query2 = (
            f"{triumph.official_name} vs {skillz.official_name} user experience "
            "app store rating comparison withdrawal times customer support "
            "game fairness complaints"
        )
        
        r1, r2 = await asyncio.gather(
            search_with_fallback(query1),
            search_with_fallback(query2)
        )
        
        if r1.success or r2.success:
            combined_answer = (
                f"### Business Comparison\n{r1.answer if r1.success else ''}\n\n"
                f"### UX & Product Comparison\n{r2.answer if r2.success else ''}"
            )
            
            sources = []
            if r1.success: sources.extend(r1.sources)
            if r2.success: sources.extend(r2.sources)

            return ResearchResult(
                task_id=task_id,
                task_type=ResearchTaskType.COMPETITOR_RESEARCH,
                success=True,
                data={
                    "comparison_query": [query1, query2],
                    "answer": combined_answer,
                    "companies": ["triumph", "skillz"]
                },
                raw_content=combined_answer,
                sources=list(set(sources)),
                tool_used=f"{r1.tool_used}+{r2.tool_used}",
                cost=(r1.cost if r1.success else 0) + (r2.cost if r2.success else 0)
            )
        else:
            return ResearchResult(
                task_id=task_id,
                task_type=ResearchTaskType.COMPETITOR_RESEARCH,
                success=False,
                error=r1.error or r2.error
            )
    
    async def analyze_games_gap(self) -> ResearchResult:
        """
        Analyze game offerings gap.
        
        Task 4: "What IO games exist that Triumph doesn't offer yet?"
        """
        task_id = f"games_gap_{datetime.utcnow().timestamp()}"
        
        triumph = TRIUMPH
        
        query = (
            f"{triumph.official_name} games offered list "
            "IO games .io games browser games popular mobile skill games "
            "games not on Triumph Arcade potential games to add"
        )
        
        result = await search_with_fallback(query, "triumph")
        
        if result.success:
            return ResearchResult(
                task_id=task_id,
                task_type=ResearchTaskType.COMPETITOR_RESEARCH,
                success=True,
                data={
                    "gap_query": query,
                    "answer": result.answer
                },
                raw_content=result.answer,
                sources=result.sources,
                tool_used=result.tool_used,
                cost=result.cost
            )
        else:
            return ResearchResult(
                task_id=task_id,
                task_type=ResearchTaskType.COMPETITOR_RESEARCH,
                success=False,
                error=result.error
            )
    
    async def run_all(self) -> list[ResearchResult]:
        """Run all competitor analysis tasks."""
        tasks = [
            self.analyze_company("triumph"),
            self.analyze_company("skillz"),
            self.compare_companies(),
            self.analyze_games_gap()
        ]
        return await asyncio.gather(*tasks)


# ============================================================
# REGULATORY ANALYZER
# ============================================================

class RegulatoryAnalyzer:
    """
    Analyze regulatory compliance.
    
    Task 4: "Is this model legal in the UK/EU?"
    """
    
    def __init__(self):
        self.name = "Regulatory Analyzer"
        self.target_jurisdictions = ["uk", "germany", "france", "spain", "eu"]
    
    async def check_jurisdiction(
        self,
        jurisdiction: str
    ) -> ResearchResult:
        """
        Check regulatory compliance for a jurisdiction.
        
        Args:
            jurisdiction: Country/region code
            
        Returns:
            ResearchResult with compliance data
        """
        task_id = f"regulatory_{jurisdiction}_{datetime.utcnow().timestamp()}"
        
        result = await check_regulatory_compliance(jurisdiction)
        
        if result.success:
            return ResearchResult(
                task_id=task_id,
                task_type=ResearchTaskType.REGULATORY_CHECK,
                success=True,
                data={
                    "jurisdiction": result.jurisdiction,
                    "jurisdiction_name": result.jurisdiction_name,
                    "status": result.status.value,
                    "licensing_required": result.licensing_required,
                    "licensing_authority": result.licensing_authority,
                    "key_regulations": result.key_regulations,
                    "summary": result.summary,
                    "requirements": result.requirements,
                    "restrictions": result.restrictions,
                    "recommendations": result.recommendations
                },
                raw_content=result.summary,
                sources=[s.url for s in result.sources if s.url],
                tool_used=result.tool_used,
                cost=result.cost
            )
        else:
            return ResearchResult(
                task_id=task_id,
                task_type=ResearchTaskType.REGULATORY_CHECK,
                success=False,
                error=result.error
            )
    
    async def run_all(self) -> list[ResearchResult]:
        """Check all target jurisdictions."""
        tasks = [
            self.check_jurisdiction(j) 
            for j in self.target_jurisdictions
        ]
        return await asyncio.gather(*tasks)


# ============================================================
# RESEARCH COORDINATOR
# ============================================================

async def run_research_task(task: ResearchTask, state: MRDState) -> ResearchResult:
    """Execute a single research task based on its type."""
    print(f"  → Starting task: {task.task_type}...")
    
    try:
        if task.task_type == ResearchTaskType.MARKET_ANALYSIS:
            agent = MarketResearcher()
            if "size" in task.query.lower():
                return await agent.research_market_size(state.domain)
            elif "trend" in task.query.lower():
                return await agent.research_market_trends(state.domain)
            else:
                # Default generic market search
                return await agent.research_market_size(state.domain) # Simplification
                
        elif task.task_type == ResearchTaskType.COMPETITOR_RESEARCH:
            agent = CompetitorAnalyzer()
            if task.target_company:
                return await agent.analyze_company(task.target_company)
            elif "gap" in task.query.lower():
                return await agent.analyze_games_gap()
            elif "comparison" in task.task_id or "vs" in task.query.lower():
                return await agent.compare_companies()
            else:
                 return await agent.compare_companies() # Default
                 
        elif task.task_type == ResearchTaskType.REGULATORY_CHECK:
            agent = RegulatoryAnalyzer()
            # Extract jurisdiction keyword or default to UK
            jurisdiction = "uk"
            if "eu" in task.query.lower() or "europe" in task.query.lower():
                jurisdiction = "eu"
            elif "germany" in task.query.lower():
                jurisdiction = "germany"
            
            return await agent.check_jurisdiction(jurisdiction)
            
        elif task.task_type == ResearchTaskType.TIKTOK_INFLUENCER:
            agent = MarketResearcher()
            return await agent.research_audience(state.domain)
            
        elif task.task_type == ResearchTaskType.COMPETITOR_DISCOVERY:
            agent = CompetitorDiscoveryAgent()
            return await agent.discover_competitors(task)
        
        elif task.task_type == ResearchTaskType.SENTIMENT_ANALYSIS:
            # Sentiment analysis for app reviews or social media
            from src.tools.sentiment import analyze_sentiment
            target = task.target_company or "triumph"
            
            # Pass company_id (target) directly, not a query string
            result = await analyze_sentiment(target, source_type="all")
            
            return ResearchResult(
                task_id=task.task_id,
                task_type=task.task_type,
                success=result.success,
                data={
                    "sentiment": result.overall_sentiment.value if result.success else "neutral",
                    "positive_count": result.positive_count,
                    "negative_count": result.negative_count,
                    "themes": result.key_themes,
                    "tool_used": result.tool_used
                },
                tool_used="sentiment_analyzer",
                cost=result.cost
            )
        
        elif task.task_type == ResearchTaskType.APP_STORE_REVIEWS:
            # App store review analysis
            from src.tools.app_reviews import get_app_reviews
            target = task.target_company or "triumph"
            result = await get_app_reviews(target)
            return ResearchResult(
                task_id=task.task_id,
                task_type=task.task_type,
                success=True if result else False,
                data={
                    "reviews": result.reviews[:10] if result and result.reviews else [],
                    "average_rating": result.average_rating if result else None,
                    "total_reviews": result.total_reviews if result else 0,
                    "tool_used": "app_reviews"
                } if result else None,
                tool_used="app_reviews",
                cost=0.01
            )
            
        else:
            return ResearchResult(
                task_id=task.task_id,
                task_type=task.task_type,
                success=False,
                error=f"Unsupported task type: {task.task_type}"
            )
            
    except Exception as e:
        logger.error(f"Task {task.task_id} failed: {e}")
        return ResearchResult(
            task_id=task.task_id,
            task_type=task.task_type,
            success=False,
            error=str(e)
        )


async def run_all_research(
    state: MRDState
) -> tuple[list[ResearchResult], float]:
    """
    Run all research tasks defined in the plan.
    
    Args:
        state: Current MRD state containing the research plan
        
    Returns:
        Tuple of (results list, total cost)
    """
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich import print as rprint
    
    console = Console()
    
    # Display task count
    total_tasks = len(state.research_plan)
    console.print(f"  [cyan]→[/] Scraping official websites (Ground Truth)...")
    
    # 1. Scrape official websites first (Critical for accuracy)
    analyzer = CompetitorAnalyzer()
    await analyzer.scrape_official_websites()
    
    console.print(f"  [cyan]→[/] Running {total_tasks} research tasks in parallel...")
    console.print()
    
    # Display all tasks that will run
    for i, task in enumerate(state.research_plan, 1):
        task_name = task.task_type.value.replace("_", " ").title()
        target = task.target_company or "General"
        console.print(f"  [dim]{i:2d}.[/] [cyan]{task_name}[/] → {target}")
    
    console.print()
    
    # 2. Execute all tasks in parallel with progress
    async def run_task_with_logging(task, index):
        """Wrapper to log task progress."""
        task_name = task.task_type.value.replace("_", " ").title()
        target = task.target_company or "General"
        
        console.print(f"  [yellow]*[/] Starting: {task_name} [{target}]")
        
        try:
            result = await run_research_task(task, state)
            
            if result.success:
                # Show what was found
                data_items = 0
                if result.data:
                    if isinstance(result.data, dict):
                        data_items = len([v for v in result.data.values() if v])
                console.print(f"  [green][OK][/] Complete: {task_name} [{target}] - {data_items} data points")
            else:
                console.print(f"  [red][X][/] Failed: {task_name} [{target}] - {result.error or 'Unknown error'}")
            
            return result
            
        except Exception as e:
            console.print(f"  [red][X][/] Error: {task_name} [{target}] - {str(e)[:50]}")
            return ResearchResult(
                task_id=task.task_id,
                task_type=task.task_type,
                success=False,
                error=str(e)
            )
    
    # Create tasks with index for logging
    tasks = []
    for i, task in enumerate(state.research_plan):
        tasks.append(run_task_with_logging(task, i))
    
    results = await asyncio.gather(*tasks)
    
    # Calculate total cost
    total_cost = sum(r.cost for r in results)
    
    # Summary
    success_count = len([r for r in results if r.success])
    fail_count = len([r for r in results if not r.success])
    
    console.print()
    console.print(f"  [bold]Results:[/] [green]{success_count} succeeded[/], [red]{fail_count} failed[/]")
    console.print(f"  [bold]Cost:[/] ${total_cost:.4f}")
    
    return results, total_cost

