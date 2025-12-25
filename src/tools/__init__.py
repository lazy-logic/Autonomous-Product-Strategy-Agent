"""
============================================================
MRD Agent - Tools Package
============================================================
Research tools for data gathering.

Tools implemented:
1. web_search - Perplexity and Tavily search
2. web_scraping - Firecrawl and Jina scraping  
3. sentiment - Sentiment analysis
4. regulatory - Compliance checking
5. app_reviews - App Store/Google Play review mining
6. influencer - TikTok/Instagram/YouTube tracking
7. tool_diversity - Multi-tool rotation for balanced research [NEW]
============================================================
"""

from src.tools.web_search import PerplexitySearch, TavilySearch, search_with_fallback
from src.tools.web_scraping import FirecrawlScraper, scrape_url
from src.tools.sentiment import SentimentAnalyzer, analyze_sentiment
from src.tools.regulatory import RegulatoryChecker, check_regulatory_compliance
from src.tools.app_reviews import get_app_reviews, mine_one_star_reviews, is_zombie_app
from src.tools.influencer import get_influencer_mentions, compare_influencer_presence
from src.tools.tool_diversity import (
    diverse_search,
    multi_tool_research,
    get_tracker,
    reset_tracker,
)

__all__ = [
    # Web search
    "PerplexitySearch",
    "TavilySearch", 
    "search_with_fallback",
    # Web scraping
    "FirecrawlScraper",
    "scrape_url",
    # Sentiment
    "SentimentAnalyzer",
    "analyze_sentiment",
    # Regulatory
    "RegulatoryChecker",
    "check_regulatory_compliance",
    # App Reviews
    "get_app_reviews",
    "mine_one_star_reviews",
    "is_zombie_app",
    # Influencer
    "get_influencer_mentions",
    "compare_influencer_presence",
    # Tool Diversity (NEW - addresses GAP)
    "diverse_search",
    "multi_tool_research",
    "get_tracker",
    "reset_tracker",
]

