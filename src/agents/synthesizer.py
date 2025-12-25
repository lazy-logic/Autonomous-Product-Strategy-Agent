"""
============================================================
MRD Agent - MRD Synthesizer
============================================================
PURPOSE: Synthesize research results into a structured MRD.

TASK 4 REQUIREMENT:
"The final MRD cannot be a blob of text. It must be a strict 
JSON/Object structure (StrategicAnalysis, CompetitorList, SWOT, 
FeatureRecommendations)."

This agent takes all research results and produces a validated
Pydantic MRDOutput model.

MULTI-LLM SUPPORT:
- Gemini: Used for synthesis and writing tasks
- GPT-4o: Used for structured extraction
============================================================
"""

import os
import json
from typing import Optional, Any
from datetime import datetime
import asyncio
import logging
import httpx

from src.models.state import MRDState, ResearchResult, ResearchTaskType
from src.models.mrd import (
    MRDOutput,
    MRDMetadata,
    StrategicAnalysis,
    MarketSize,
    AudienceInsight,
    CompetitorProfile,
    MarketPosition,
    AppMetrics,
    FinancialMetrics,
    SWOTAnalysis,
    SWOTItem,
    FeatureRecommendation,
    RegulatoryAssessment,
    JurisdictionAssessment,
    RegulatoryStatus,
    DataSource,
    ConfidenceLevel,
    Sentiment,
    SampleReview,  # Added for sample app reviews
)
from src.models.companies import TRIUMPH, SKILLZ

# Multi-LLM support
from src.llm.multi_llm import (
    call_llm,
    synthesize_with_gemini,
    extract_structured_with_openai,
    get_llm_status,
    LLMTask,
    LLMProvider,
)

logger = logging.getLogger(__name__)


class MRDSynthesizer:
    """
    Synthesize research into structured MRD.
    
    Uses Multi-LLM architecture:
    - Gemini: Best for prose synthesis (executive summaries, analysis)
    - GPT-4o: Best for structured extraction (SWOT, competitors)
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with OpenAI API key (Gemini key loaded from env)."""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found")
        
        self.primary_model = "gpt-4o"  # For structured extraction
        self.synthesis_provider = LLMProvider.GEMINI  # For writing
        self.cost_per_1k_input = 0.005
        self.cost_per_1k_output = 0.015
        
        # Log available LLM providers
        logger.info(f"Multi-LLM Status: {get_llm_status()}")
    
    def _group_research_by_type(
        self, 
        results: list[ResearchResult]
    ) -> dict[str, list[ResearchResult]]:
        """Group research results by type."""
        grouped = {}
        for result in results:
            key = result.task_type.value
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(result)
        return grouped
    
    def _build_research_summary(
        self,
        results: list[ResearchResult]
    ) -> str:
        """Build a summary of all research for the LLM."""
        sections = []
        grouped = self._group_research_by_type(results)
        
        for task_type, type_results in grouped.items():
            section = f"\n## {task_type.replace('_', ' ').title()}\n"
            for result in type_results:
                if result.success and result.raw_content:
                    section += f"\n### Research Finding:\n{result.raw_content[:6000]}\n"
                    if result.sources:
                        section += f"Sources: {', '.join(result.sources[:3])}\n"
            sections.append(section)
        
        return "\n".join(sections)
    
    async def _call_llm_for_structure(
        self,
        prompt: str,
        research_summary: str,
        structure_name: str,
        structure_schema: dict
    ) -> Optional[dict]:
        """
        Call LLM to generate a structured output.
        
        Uses Multi-LLM with automatic provider selection:
        - GPT-4o for structured extraction (primary)
        - Gemini as fallback
        """
        system_prompt = f"""You are an expert Product Manager synthesizing research into structured data.
        
Your task: Generate a valid {structure_name} based on the research provided.

CRITICAL RULES:
1. Only use information from the research - DO NOT hallucinate
2. If data is missing, use null instead of placeholders
3. Output MUST be valid JSON matching the schema
4. Focus on Triumph (triumpharcade.com) and Skillz (skillz.com) only

Output JSON Schema:
{json.dumps(structure_schema, indent=2)}
"""
        
        user_prompt = f"""Original User Request: {prompt}

Research Data:
{research_summary}

Generate the {structure_name} as valid JSON. Output ONLY the JSON, no explanation."""
        
        try:
            # Use multi-LLM for structured extraction (GPT-4o preferred)
            response = await call_llm(
                prompt=f"{system_prompt}\n\n{user_prompt}",
                task_type=LLMTask.STRUCTURED_EXTRACTION,
                json_mode=True,
                temperature=0.3,
            )
            
            if response.success:
                logger.info(f"LLM extraction succeeded: {response.provider}/{response.model}")
                return response.structured_data or json.loads(response.content or "{}")
            else:
                logger.error(f"LLM call failed: {response.error}")
                return None
                    
        except Exception as e:
            logger.error(f"LLM synthesis failed: {e}")
            return None
    
    async def synthesize_strategic_analysis(
        self,
        state: MRDState
    ) -> StrategicAnalysis:
        """
        Synthesize strategic analysis from market research.
        
        Uses Multi-LLM:
        - GPT-4o: Structured data extraction (market_size, trends)
        - Gemini: Executive summary prose (better writing quality)
        """
        research_summary = self._build_research_summary(state.research_results)
        
        schema = {
            "executive_summary": "string (min 100 chars)",
            "market_size": {
                "tam": "number or null",
                "sam": "number or null",
                "cagr": "number or null",
                "year": "number"
            },
            "target_audience": {
                "demographic": "string",
                "behaviors": ["string"],
                "pain_points": ["string"],
                "channels": ["string"],
                "influencer_strategy": "string or null"
            },
            "key_trends": ["string"],
            "market_dynamics": "string"
        }
        
        result = await self._call_llm_for_structure(
            state.prompt,
            research_summary,
            "StrategicAnalysis",
            schema
        )
        
        # Try to enhance executive summary with Gemini (better prose)
        executive_summary = result.get("executive_summary", "") if result else ""
        if research_summary and len(research_summary) > 100:
            try:
                gemini_response = await synthesize_with_gemini(
                    research_summary[:10000],  # Limit to avoid token limits
                    "executive_summary"
                )
                if gemini_response.success and gemini_response.content:
                    executive_summary = gemini_response.content[:2000]  # Truncate
                    logger.info(f"Executive summary enhanced by Gemini")
            except Exception as e:
                logger.warning(f"Gemini synthesis failed, using GPT output: {e}")
        
        if result:
            try:
                market_size = MarketSize(
                    tam=result.get("market_size", {}).get("tam"),
                    sam=result.get("market_size", {}).get("sam"),
                    cagr=result.get("market_size", {}).get("cagr"),
                    year=result.get("market_size", {}).get("year", 2024)
                )
                
                audience = AudienceInsight(
                    demographic=result.get("target_audience", {}).get("demographic", "Males 18-35"),
                    behaviors=result.get("target_audience", {}).get("behaviors", []),
                    pain_points=result.get("target_audience", {}).get("pain_points", []),
                    channels=result.get("target_audience", {}).get("channels", []),
                    influencer_strategy=result.get("target_audience", {}).get("influencer_strategy")
                )
                
                return StrategicAnalysis(
                    executive_summary=executive_summary or result.get("executive_summary", "Analysis pending..."),
                    market_size=market_size,
                    target_audience=audience,
                    key_trends=result.get("key_trends", []),
                    market_dynamics=result.get("market_dynamics", "Analysis pending...")
                )
            except Exception as e:
                logger.error(f"Failed to parse strategic analysis: {e}")
        
        # Fallback
        return StrategicAnalysis(
            executive_summary="The strategic analysis could not be fully synthesized due to insufficient research data. However, preliminary findings suggest opportunities in the skill-based gaming market with focus on mobile platforms and social features.",
            market_size=MarketSize(year=2024),
            target_audience=AudienceInsight(
                demographic="Males 18-35",
                behaviors=["Mobile gaming", "Competitive play"],
                channels=["TikTok", "Instagram"]
            ),
            key_trends=["Skill-based gaming growth", "Mobile-first experiences"],
            market_dynamics="Market analysis pending."
        )
    
    async def _fetch_sample_reviews(self, company_id: str) -> list[SampleReview]:
        """Fetch sample reviews for a company from app stores."""
        try:
            from src.tools.app_reviews import get_app_reviews
            review_summary = await get_app_reviews(company_id, max_reviews=20)
            
            sample_reviews = []
            for review in review_summary.reviews[:3]:  # Top 3 reviews
                sample_reviews.append(SampleReview(
                    rating=review.rating,
                    content=review.content[:200],  # Truncate to 200 chars
                    author=review.author,
                    date=review.date,
                    source=review.source.value
                ))
            return sample_reviews
        except Exception as e:
            logger.warning(f"Failed to fetch reviews for {company_id}: {e}")
            return []
    
    async def synthesize_competitors(
        self,
        state: MRDState
    ) -> list[CompetitorProfile]:
        """Synthesize competitor profiles from research, including sample reviews."""
        research_summary = self._build_research_summary(state.research_results)
        
        # Fetch sample reviews for both competitors in parallel
        from rich.console import Console
        console = Console()
        console.print("  [dim]Fetching app store reviews...[/]")
        
        triumph_reviews, skillz_reviews = await asyncio.gather(
            self._fetch_sample_reviews("triumph"),
            self._fetch_sample_reviews("skillz")
        )
        
        # Schema for competitor extraction
        schema = {
            "competitors": [
                {
                    "name": "string",
                    "description": "string",
                    "position": "Leader|Challenger|Follower|Niche|Declining",
                    "target_audience": "string",
                    "app_metrics": {
                        "rating": "number",
                        "downloads": "string",
                        "mau": "number or null"
                    },
                    "financials": {
                        "revenue": "number or null",
                        "growth": "number or null",
                        "funding": "number or null"
                    },
                    "strengths": ["string"],
                    "weaknesses": ["string"],
                    "games": ["string"]
                }
            ]
        }
        
        result = await self._call_llm_for_structure(
            f"Compare {TRIUMPH.official_name} and {SKILLZ.official_name}. Extract their profiles.",
            research_summary,
            "CompetitorAnalysis",
            schema
        )
        
        competitors = []
        if result and "competitors" in result:
            for comp_data in result["competitors"]:
                try:
                    # Match with official objects for websites
                    website = ""
                    if "triumph" in comp_data["name"].lower():
                         website = TRIUMPH.website
                    elif "skillz" in comp_data["name"].lower():
                         website = SKILLZ.website
                    
                    # Helper to safely parse numeric values (handles "[NEEDS VERIFICATION]")
                    def safe_float(val):
                        if val is None:
                            return None
                        if isinstance(val, (int, float)):
                            return float(val)
                        try:
                            return float(val)
                        except (ValueError, TypeError):
                            return None
                    
                    # Helper to filter None values from lists and ensure strings
                    def safe_list(items, default=None):
                        if not items or not isinstance(items, list):
                            return default or []
                        return [str(item) for item in items if item is not None and item != ""]
                    
                    # Get sample reviews for this competitor
                    comp_reviews = []
                    if "triumph" in comp_data["name"].lower():
                        comp_reviews = triumph_reviews
                    elif "skillz" in comp_data["name"].lower():
                        comp_reviews = skillz_reviews
                    
                    profile = CompetitorProfile(
                        name=comp_data["name"],
                        website=website,
                        description=comp_data.get("description", "") or "",
                        position=MarketPosition(comp_data.get("position", "Challenger").lower()),
                        target_audience=comp_data.get("target_audience", "") or "",
                        app_metrics=AppMetrics(
                            app_store_rating=safe_float(comp_data.get("app_metrics", {}).get("rating")),
                            downloads_estimate=comp_data.get("app_metrics", {}).get("downloads"),
                            monthly_active_users=safe_float(comp_data.get("app_metrics", {}).get("mau")),
                            sample_reviews=comp_reviews  # Added sample reviews
                        ),
                        financials=FinancialMetrics(
                            revenue_annual=safe_float(comp_data.get("financials", {}).get("revenue")),
                            revenue_growth_yoy=safe_float(comp_data.get("financials", {}).get("growth")),
                            funding_total=safe_float(comp_data.get("financials", {}).get("funding"))
                        ),
                        key_strengths=safe_list(comp_data.get("strengths"), ["Strong presence"]),
                        key_weaknesses=safe_list(comp_data.get("weaknesses"), ["Areas for improvement"]),
                        games_offered=safe_list(comp_data.get("games"), ["Various games"]),
                        sources=[DataSource(source_type="research_synthesis", confidence=ConfidenceLevel.MEDIUM)]
                    )
                    competitors.append(profile)
                except Exception as e:
                    logger.error(f"Failed to parse competitor profile: {e}")

        # If LLM failed to return BOTH, fill gaps with defaults
        triumph_found = any("triumph" in c.name.lower() for c in competitors)
        skillz_found = any("skillz" in c.name.lower() for c in competitors)
        
        if not triumph_found:
            triumph_profile = CompetitorProfile(
                name=TRIUMPH.official_name,
                website=TRIUMPH.website,
                description="Real-money skill gaming platform with cash prizes (Fallback Data)",
                position=MarketPosition.CHALLENGER,
                target_audience="Males 18-35, casual gamers seeking cash rewards",
                app_metrics=AppMetrics(
                    app_store_rating=4.7, 
                    downloads_estimate="1M+",
                    sample_reviews=triumph_reviews  # Include sample reviews
                ),
                financials=FinancialMetrics(funding_total=22300000, last_funding_round="Series A"),
                key_strengths=["TikTok marketing", "Cash prizes", "High user ratings"],
                key_weaknesses=["Limited international presence", "Regulatory risks"],
                games_offered=["Pool", "Chaos Cannon", "Fish Frenzy", "Doodle Jump"],
                sources=[]
            )
            competitors.append(triumph_profile)
        
        if not skillz_found:
            skillz_profile = CompetitorProfile(
                name=SKILLZ.official_name,
                website=SKILLZ.website,
                description="Mobile eSports platform for real-money tournaments (Fallback Data)",
                position=MarketPosition.DECLINING,
                target_audience="Competitive mobile gamers",
                app_metrics=AppMetrics(
                    monthly_active_users=110000, 
                    downloads_estimate="10M+",
                    sample_reviews=skillz_reviews  # Include sample reviews
                ),
                financials=FinancialMetrics(revenue_annual=92870000, revenue_growth_yoy=-39.0),
                key_strengths=["Established brand", "Public company", "Large developer network"],
                key_weaknesses=["Declining revenue (-39% YoY)", "NYSE delisting concerns", "Negative user sentiment"],
                games_offered=["Blackout Bingo", "Solitaire Cube", "Pool Payday"],
                sources=[]
            )
            competitors.append(skillz_profile)

        return competitors
    
    async def synthesize_swot(
        self,
        state: MRDState
    ) -> SWOTAnalysis:
        """Synthesize SWOT analysis."""
        research_summary = self._build_research_summary(state.research_results)
        
        schema = {
            "strengths": [{"statement": "string", "impact": "high|medium|low"}],
            "weaknesses": [{"statement": "string", "impact": "high|medium|low"}],
            "opportunities": [{"statement": "string", "impact": "high|medium|low"}],
            "threats": [{"statement": "string", "impact": "high|medium|low"}]
        }
        
        result = await self._call_llm_for_structure(
            state.prompt,
            research_summary,
            "SWOTAnalysis",
            schema
        )
        
        if result:
            try:
                # Parse with defaults if items missing
                def parse_swot_items(items, default_statements):
                    parsed = []
                    if items:
                        for s in items[:5]:
                            if isinstance(s, dict) and s.get("statement"):
                                parsed.append(SWOTItem(
                                    statement=s["statement"],
                                    impact=s.get("impact", "medium")
                                ))
                    # Ensure minimum 2 items
                    while len(parsed) < 2:
                        if len(default_statements) > len(parsed):
                            parsed.append(SWOTItem(
                                statement=default_statements[len(parsed)],
                                impact="medium"
                            ))
                        else:
                            break
                    return parsed
                
                return SWOTAnalysis(
                    strengths=parse_swot_items(
                        result.get("strengths", []),
                        ["Skill-based gaming model has legal advantages", "Growing mobile gaming market"]
                    ),
                    weaknesses=parse_swot_items(
                        result.get("weaknesses", []),
                        ["Regulatory uncertainty in key markets", "User acquisition challenges"]
                    ),
                    opportunities=parse_swot_items(
                        result.get("opportunities", []),
                        ["Underserved European market", "TikTok influencer marketing potential"]
                    ),
                    threats=parse_swot_items(
                        result.get("threats", []),
                        ["Regulatory crackdowns", "Established competitor response"]
                    )
                )
            except Exception as e:
                logger.error(f"Failed to parse SWOT: {e}")
        
        # Fallback SWOT
        return SWOTAnalysis(
            strengths=[
                SWOTItem(statement="Skill-based gaming has legal advantages over gambling", impact="high"),
                SWOTItem(statement="Growing mobile gaming market", impact="high")
            ],
            weaknesses=[
                SWOTItem(statement="Regulatory uncertainty in key markets", impact="high"),
                SWOTItem(statement="User acquisition costs", impact="medium")
            ],
            opportunities=[
                SWOTItem(statement="Underserved European market", impact="high"),
                SWOTItem(statement="TikTok influencer marketing potential", impact="medium")
            ],
            threats=[
                SWOTItem(statement="Regulatory crackdowns", impact="high"),
                SWOTItem(statement="Established competitor response", impact="medium")
            ]
        )
    
    async def synthesize_features(
        self,
        state: MRDState
    ) -> list[FeatureRecommendation]:
        """Synthesize feature recommendations."""
        """Synthesize feature recommendations."""
        research_summary = self._build_research_summary(state.research_results)
        
        schema = {
            "recommendations": [
                {
                    "name": "string",
                    "description": "string",
                    "priority": "must_have|should_have|nice_to_have",
                    "rationale": "string",
                    "effort": "low|medium|high",
                    "competitor_reference": "string or null"
                }
            ]
        }
        
        result = await self._call_llm_for_structure(
            "Identify 5 key features for a new skill-based gaming app based on competitor gaps and market trends.",
            research_summary,
            "FeatureRecommendations",
            schema
        )
        
        features = []
        if result and "recommendations" in result:
            for item in result["recommendations"]:
                features.append(FeatureRecommendation(
                    name=item["name"],
                    description=item["description"],
                    priority=item["priority"],
                    rationale=item["rationale"],
                    effort_estimate=item.get("effort", "medium"),
                    competitor_reference=item.get("competitor_reference")
                ))
        
        if not features:
            # Fallback only if LLM fails
            return [
                FeatureRecommendation(
                    name="Social Tournament Mode",
                    description="Allow friends to create private tournaments",
                    priority="must_have",
                    rationale="Core mechanic for viral growth",
                    effort_estimate="medium"
                )
            ]
            
        return features
    
    async def synthesize_regulatory(
        self,
        state: MRDState
    ) -> RegulatoryAssessment:
        """Synthesize regulatory assessment from research."""
        jurisdictions = []
        
        # Extract regulatory results
        for result in state.research_results:
            if result.task_type == ResearchTaskType.REGULATORY_CHECK and result.success:
                data = result.data or {}
                jurisdictions.append(JurisdictionAssessment(
                    jurisdiction=data.get("jurisdiction", "unknown"),
                    status=RegulatoryStatus(data.get("status", "gray_area")),
                    key_regulations=data.get("key_regulations", []),
                    licensing_required=data.get("licensing_required", True),
                    licensing_authority=data.get("licensing_authority"),
                    notes=data.get("summary", "")
                ))
        
        # If no regulatory data, use defaults
        if not jurisdictions:
            jurisdictions = [
                JurisdictionAssessment(
                    jurisdiction="uk",
                    status=RegulatoryStatus.LEGAL_WITH_RESTRICTIONS,
                    licensing_required=True,
                    licensing_authority="UK Gambling Commission"
                ),
                JurisdictionAssessment(
                    jurisdiction="eu",
                    status=RegulatoryStatus.LEGAL_WITH_RESTRICTIONS,
                    licensing_required=True,
                    notes="Varies by member state"
                )
            ]
        
        return RegulatoryAssessment(
            jurisdictions=jurisdictions,
            overall_risk_level="medium",
            recommended_launch_markets=["UK", "Malta", "Ireland"],
            markets_to_avoid=["Belgium", "Netherlands (initially)"]
        )
    
    async def synthesize_gap_analysis(
        self,
        state: MRDState
    ) -> list[str]:
        """
        Synthesize gap analysis.
        
        Task 4: "What IO games exist that Triumph doesn't offer yet?"
        """
        research_summary = self._build_research_summary(state.research_results)
        
        schema = {
            "gaps": [
                {
                    "game_type": "string",
                    "description": "string",
                    "potential": "high|medium|low"
                }
            ]
        }
        
        result = await self._call_llm_for_structure(
            "Identify 6-8 specific game types or features that Triumph Arcade does NOT offer but are popular in the market or offered by Skillz. Be specific about game names and genres.",
            research_summary,
            "GapAnalysis",
            schema
        )
        
        if result and "gaps" in result:
            return [
                f"{g['game_type']} ({g.get('potential', 'medium')} potential) - {g['description']}"
                for g in result["gaps"]
            ]
        
        # Fallback only if LLM fails
        return [
            "Slither.io style games - highly popular, not offered by Triumph",
            "Agar.io variants - viral potential, missing from catalog",
            "Battle royale casual games - trending genre gap"
        ]
    
    async def synthesize(self, state: MRDState) -> MRDOutput:
        """
        Main synthesis method - produce complete MRD.
        
        Returns:
            Validated MRDOutput Pydantic model
        """
        from rich.console import Console
        console = Console()
        
        console.print()
        console.print("[cyan]━━━ MRD Synthesis ━━━[/]")
        console.print()
        
        logger.info("Starting MRD synthesis...")
        
        # Show synthesis steps
        synthesis_steps = [
            ("Strategic Analysis", self.synthesize_strategic_analysis),
            ("Competitor Profiles", self.synthesize_competitors),
            ("SWOT Analysis", self.synthesize_swot),
            ("Feature Recommendations", self.synthesize_features),
            ("Regulatory Assessment", self.synthesize_regulatory),
            ("Gap Analysis", self.synthesize_gap_analysis),
        ]
        
        console.print(f"  [dim]Running {len(synthesis_steps)} synthesis tasks...[/]")
        
        # Run all synthesis tasks in parallel
        async def run_with_logging(name, func):
            console.print(f"  [yellow]*[/] Synthesizing: {name}")
            try:
                result = await func(state)
                console.print(f"  [green][OK][/] Complete: {name}")
                return result
            except Exception as e:
                console.print(f"  [red][X][/] Failed: {name} - {str(e)[:40]}")
                raise
        
        tasks = [run_with_logging(name, func) for name, func in synthesis_steps]
        strategic, competitors, swot, features, regulatory, gaps = await asyncio.gather(*tasks)
        
        console.print()
        console.print("  [dim]Building metadata...[/]")
        
        # Build metadata
        metadata = MRDMetadata(
            generated_at=datetime.utcnow(),
            prompt=state.prompt,
            domain=state.domain,
            version="2.0.0",
            total_research_cost=state.total_cost,
            tools_used=state.tools_used,
            iteration_count=state.iteration
        )
        
        console.print("  [dim]Assembling final MRD...[/]")
        
        # Collect references (Task 4 requirement: stated sources)
        references = set()
        
        # 1. From Competitors
        for comp in competitors:
            for source in comp.sources:
                if source.url:
                    references.add(source.url)
                    
        # 2. From SWOT
        for category in [swot.strengths, swot.weaknesses, swot.opportunities, swot.threats]:
            for item in category:
                if item.source and item.source.url:
                    references.add(item.source.url)
                    
        # 3. From Features
        for feature in features:
            if feature.source and feature.source.url:
                references.add(feature.source.url)
                
        # 4. From Regulatory
        for reg in regulatory.jurisdictions:  # It's a list, not a dict
            if reg.source and reg.source.url:
                references.add(reg.source.url)
                    
        sorted_references = sorted(list(references))

        # Assemble final MRD
        mrd = MRDOutput(
            metadata=metadata,
            strategic_analysis=strategic,
            competitors=competitors,
            swot=swot,
            feature_recommendations=features,
            regulatory=regulatory,
            gap_analysis=gaps,
            references=sorted_references  # Added references
        )
        
        console.print()
        console.print("  [bold green][OK] MRD synthesis complete[/]")
        console.print(f"  [dim]Competitors: {len(competitors)} | Features: {len(features)} | SWOT items: {len(swot.strengths) + len(swot.weaknesses)}[/]")
        
        logger.info("MRD synthesis complete")
        return mrd
    
    def synthesize_sync(self, state: MRDState) -> MRDOutput:
        """Synchronous wrapper."""
        return asyncio.run(self.synthesize(state))
