"""
============================================================
MRD Agent - Sentiment Analysis Tool
============================================================
PURPOSE: Analyze sentiment about companies from various sources.

TASK 4 REQUIREMENT:
"analyze_sentiment(social_source)" - Interface with sentiment tools

CRITICAL FIX:
Previous implementation searched generic "Triumph" and got
Triumph Motorcycles data. Now we use the verified company
database to ensure we're analyzing the RIGHT company.

SOURCES ANALYZED:
1. App Store reviews (via search)
2. Social media mentions (TikTok, Twitter)
3. News articles
4. Reddit/forums
============================================================
"""

import os
import httpx
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum
import asyncio
import logging

from src.models.companies import VerifiedCompany, get_company
from src.models.mrd import Sentiment, DataSource, ConfidenceLevel

logger = logging.getLogger(__name__)


# ============================================================
# RESPONSE MODELS
# ============================================================

class SentimentMention(BaseModel):
    """A single mention with sentiment."""
    text: str = Field(..., description="The mention text")
    source: str = Field(..., description="Where this came from")
    url: Optional[str] = Field(default=None, description="URL of source")
    sentiment: Sentiment = Field(..., description="Sentiment classification")
    score: float = Field(default=0.0, ge=-1.0, le=1.0, description="Sentiment score -1 to 1")
    date: Optional[str] = Field(default=None, description="Date of mention")


class SentimentAnalysisResult(BaseModel):
    """Result from sentiment analysis."""
    success: bool = Field(..., description="Whether analysis succeeded")
    company_id: str = Field(..., description="Company analyzed")
    company_name: str = Field(..., description="Official company name")
    
    # Aggregate sentiment
    overall_sentiment: Sentiment = Field(default=Sentiment.NEUTRAL)
    overall_score: float = Field(default=0.0, ge=-1.0, le=1.0)
    
    # Breakdown
    positive_count: int = Field(default=0)
    neutral_count: int = Field(default=0)
    negative_count: int = Field(default=0)
    
    # Individual mentions
    mentions: list[SentimentMention] = Field(default_factory=list)
    
    # Key themes
    key_themes: list[str] = Field(default_factory=list)
    positive_themes: list[str] = Field(default_factory=list)
    negative_themes: list[str] = Field(default_factory=list)

    
    # Metadata
    sources_analyzed: list[str] = Field(default_factory=list)
    tool_used: str = Field(default="openai")
    cost: float = Field(default=0.0)
    error: Optional[str] = Field(default=None)
    timestamp: datetime = Field(default_factory=datetime.utcnow)





# ============================================================
# SENTIMENT ANALYZER
# ============================================================

class SentimentAnalyzer:
    """
    Sentiment analyzer using OpenAI for classification.
    
    Process:
    1. Get verified company info (prevents Triumph Motorcycles bug)
    2. Search for mentions using company's search keywords
    3. Classify sentiment of each mention
    4. Aggregate results
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with OpenAI API key."""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
        
        self.model = "gpt-4o-mini"  # Fast and cheap for classification
        self.cost_per_call = 0.001
    
    async def _classify_sentiment(self, text: str) -> tuple[Sentiment, float]:
        """
        Classify sentiment of a piece of text.
        
        Returns:
            Tuple of (Sentiment enum, score from -1 to 1)
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
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
                                    "You are a sentiment classifier. "
                                    "Respond with ONLY a JSON object: "
                                    '{"sentiment": "positive|neutral|negative|mixed", "score": 0.0}'
                                    " Score ranges from -1 (very negative) to 1 (very positive)."
                                )
                            },
                            {
                                "role": "user",
                                "content": f"Classify the sentiment of: {text[:500]}"
                            }
                        ],
                        "temperature": 0,
                        "max_tokens": 50
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    
                    # Parse response
                    import json
                    result = json.loads(content)
                    sentiment_str = result.get("sentiment", "neutral").lower()
                    score = float(result.get("score", 0.0))
                    
                    sentiment_map = {
                        "positive": Sentiment.POSITIVE,
                        "negative": Sentiment.NEGATIVE,
                        "neutral": Sentiment.NEUTRAL,
                        "mixed": Sentiment.MIXED
                    }
                    
                    return sentiment_map.get(sentiment_str, Sentiment.NEUTRAL), score
                    
        except Exception as e:
            logger.error(f"Sentiment classification failed: {e}")
        
        return Sentiment.NEUTRAL, 0.0
    
    async def _search_mentions(
        self,
        company: VerifiedCompany,
        source_type: str = "all"
    ) -> list[SentimentMention]:
        """
        Search for mentions of a company.
        
        Uses the company's search keywords to ensure correct results.
        """
        from src.tools.web_search import search_with_fallback
        
        mentions = []
        
        # Build search queries using company disambiguation
        queries = []
        
        if source_type in ["all", "reviews"]:
            queries.append(f"{company.official_name} app reviews user feedback")
        if source_type in ["all", "social"]:
            queries.append(f"{company.official_name} TikTok influencer mentions")
        if source_type in ["all", "news"]:
            queries.append(f"{company.official_name} news coverage media")
        if source_type in ["all", "reddit"]:
            queries.append(f"{company.official_name} reddit discussion opinions")
        
        for query in queries:
            result = await search_with_fallback(query, company.id)
            
            if result.success and result.answer:
                # Split answer into potential mentions
                sentences = result.answer.split('. ')
                for sentence in sentences[:10]:  # Limit to 10 mentions per query
                    if len(sentence) > 20:  # Skip very short snippets
                        sentiment, score = await self._classify_sentiment(sentence)
                        mentions.append(SentimentMention(
                            text=sentence.strip(),
                            source=result.tool_used,
                            url=result.sources[0] if result.sources else None,
                            sentiment=sentiment,
                            score=score
                        ))
        
        return mentions
    
    async def analyze(
        self,
        company_id: str,
        source_type: str = "all"
    ) -> SentimentAnalysisResult:
        """
        Analyze sentiment for a company.
        
        Args:
            company_id: ID of company from verified database
            source_type: 'all', 'reviews', 'social', 'news', 'reddit'
            
        Returns:
            SentimentAnalysisResult with analysis
        """
        company = get_company(company_id)
        if not company:
            return SentimentAnalysisResult(
                success=False,
                company_id=company_id,
                company_name="Unknown",
                error=f"Company not found: {company_id}"
            )
        
        logger.info(f"Analyzing sentiment for {company.official_name}")
        
        # Search for mentions
        mentions = await self._search_mentions(company, source_type)
        
        if not mentions:
            return SentimentAnalysisResult(
                success=False,
                company_id=company_id,
                company_name=company.official_name,
                error="No mentions found"
            )
        
        # Aggregate results
        positive = [m for m in mentions if m.sentiment == Sentiment.POSITIVE]
        negative = [m for m in mentions if m.sentiment == Sentiment.NEGATIVE]
        neutral = [m for m in mentions if m.sentiment == Sentiment.NEUTRAL]
        
        total = len(mentions)
        avg_score = sum(m.score for m in mentions) / total if total > 0 else 0.0
        
        # Determine overall sentiment
        if avg_score > 0.3:
            overall = Sentiment.POSITIVE
        elif avg_score < -0.3:
            overall = Sentiment.NEGATIVE
        elif len(positive) > 0 and len(negative) > 0:
            overall = Sentiment.MIXED
        else:
            overall = Sentiment.NEUTRAL
        
        # Extract themes (simplified - would use NLP in production)
        positive_themes = list(set(
            m.text[:50] + "..." for m in positive[:5]
        ))
        negative_themes = list(set(
            m.text[:50] + "..." for m in negative[:5]
        ))
        
        return SentimentAnalysisResult(
            success=True,
            company_id=company_id,
            company_name=company.official_name,
            overall_sentiment=overall,
            overall_score=avg_score,
            positive_count=len(positive),
            neutral_count=len(neutral),
            negative_count=len(negative),
            mentions=mentions,
            positive_themes=positive_themes,
            negative_themes=negative_themes,
            key_themes=positive_themes + negative_themes,
            sources_analyzed=[source_type],
            cost=self.cost_per_call * len(mentions)
        )
    
    def analyze_sync(
        self,
        company_id: str,
        source_type: str = "all"
    ) -> SentimentAnalysisResult:
        """Synchronous wrapper for analyze."""
        return asyncio.run(self.analyze(company_id, source_type))


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================

async def analyze_sentiment(
    company_id: str,
    source_type: str = "all"
) -> SentimentAnalysisResult:
    """
    Analyze sentiment for a company.
    
    Task 4 interface: analyze_sentiment(social_source)
    
    Args:
        company_id: ID from verified company database
        source_type: Source to analyze
        
    Returns:
        SentimentAnalysisResult
    """
    analyzer = SentimentAnalyzer()
    return await analyzer.analyze(company_id, source_type)


def analyze_sentiment_sync(
    company_id: str,
    source_type: str = "all"
) -> SentimentAnalysisResult:
    """Synchronous wrapper."""
    return asyncio.run(analyze_sentiment(company_id, source_type))
