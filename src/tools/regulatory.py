"""
============================================================
MRD Agent - Regulatory Compliance Tool
============================================================
PURPOSE: Check regulatory compliance for skill gaming in 
         different jurisdictions.

TASK 4 REQUIREMENT:
"check_regulatory_compliance(region)" - Interface with regulatory tools
"Is this model legal in the UK/EU?" - Specific question to answer

This tool researches gambling/skill gaming regulations and
provides structured compliance assessments.
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

from src.models.mrd import RegulatoryStatus, JurisdictionAssessment, DataSource, ConfidenceLevel

logger = logging.getLogger(__name__)


# ============================================================
# REGULATORY KNOWLEDGE BASE
# ============================================================
# This provides baseline regulatory info that is then 
# supplemented by web research.

JURISDICTION_INFO = {
    "uk": {
        "name": "United Kingdom",
        "authority": "UK Gambling Commission (UKGC)",
        "key_laws": [
            "Gambling Act 2005",
            "National Lottery etc Act 1993",
            "Consumer Rights Act 2015"
        ],
        "skill_gaming_notes": (
            "Skill-based games where outcome is predominantly determined by skill "
            "may not require a license. However, if there's a significant chance element "
            "or real money prizes, licensing is typically required."
        ),
        "licensing_required": True,
        "base_status": RegulatoryStatus.LEGAL_WITH_RESTRICTIONS
    },
    "germany": {
        "name": "Germany",
        "authority": "Gemeinsame Glücksspielbehörde der Länder (GGL)",
        "key_laws": [
            "Interstate Treaty on Gambling 2021 (GlüStV)",
            "State gambling laws"
        ],
        "skill_gaming_notes": (
            "Germany has strict gambling regulations. Online skill gaming "
            "with real money requires a license. Individual states may have "
            "additional requirements."
        ),
        "licensing_required": True,
        "base_status": RegulatoryStatus.LEGAL_WITH_RESTRICTIONS
    },
    "france": {
        "name": "France",
        "authority": "Autorité nationale des jeux (ANJ)",
        "key_laws": [
            "Gambling Act of 2010",
            "ANJ regulations"
        ],
        "skill_gaming_notes": (
            "France has a regulated online gambling market. Skill gaming "
            "may fall under gaming regulations if prizes exceed certain thresholds."
        ),
        "licensing_required": True,
        "base_status": RegulatoryStatus.LEGAL_WITH_RESTRICTIONS
    },
    "spain": {
        "name": "Spain",
        "authority": "Dirección General de Ordenación del Juego (DGOJ)",
        "key_laws": [
            "Gambling Act 13/2011",
            "Royal Decree 1614/2011"
        ],
        "skill_gaming_notes": (
            "Spain requires licenses for online gambling. Skill-based games "
            "are regulated if they involve monetary prizes."
        ),
        "licensing_required": True,
        "base_status": RegulatoryStatus.LEGAL_WITH_RESTRICTIONS
    },
    "italy": {
        "name": "Italy",
        "authority": "Agenzia delle Dogane e dei Monopoli (ADM)",
        "key_laws": [
            "Decree Law 158/2012",
            "Budget Law provisions"
        ],
        "skill_gaming_notes": (
            "Italy has a regulated online gambling market with strict "
            "licensing requirements for games with monetary prizes."
        ),
        "licensing_required": True,
        "base_status": RegulatoryStatus.LEGAL_WITH_RESTRICTIONS
    },
    "netherlands": {
        "name": "Netherlands",
        "authority": "Kansspelautoriteit (KSA)",
        "key_laws": [
            "Remote Gambling Act (KOA) 2021",
            "Betting and Gaming Act"
        ],
        "skill_gaming_notes": (
            "The Netherlands legalized online gambling in 2021 with strict "
            "licensing requirements. Skill gaming falls under these regulations."
        ),
        "licensing_required": True,
        "base_status": RegulatoryStatus.LEGAL_WITH_RESTRICTIONS
    },
    "eu": {
        "name": "European Union",
        "authority": "Member State authorities (no EU-wide regulator)",
        "key_laws": [
            "No unified EU gambling law",
            "Individual member state laws apply",
            "EU consumer protection directives"
        ],
        "skill_gaming_notes": (
            "The EU does not have a unified gambling regulation. Each member "
            "state has its own laws. Generally, skill-based gaming with real "
            "money prizes requires licensing in the respective country."
        ),
        "licensing_required": True,
        "base_status": RegulatoryStatus.LEGAL_WITH_RESTRICTIONS
    },
    "us": {
        "name": "United States",
        "authority": "State-by-state (no federal gaming authority)",
        "key_laws": [
            "Unlawful Internet Gambling Enforcement Act (UIGEA)",
            "Wire Act (1961)",
            "Individual state laws"
        ],
        "skill_gaming_notes": (
            "US gambling law is primarily state-by-state. Skill gaming is "
            "generally more permissible than games of chance. Many states "
            "allow skill-based games with real money, but some require licensing."
        ),
        "licensing_required": False,  # Varies by state
        "base_status": RegulatoryStatus.GRAY_AREA
    }
}


# ============================================================
# RESPONSE MODELS
# ============================================================

class RegulatoryCheckResult(BaseModel):
    """Result from regulatory compliance check."""
    success: bool = Field(..., description="Whether check succeeded")
    jurisdiction: str = Field(..., description="Jurisdiction checked")
    jurisdiction_name: str = Field(..., description="Full jurisdiction name")
    
    # Assessment
    status: RegulatoryStatus = Field(...)
    licensing_required: bool = Field(default=True)
    licensing_authority: Optional[str] = Field(default=None)
    key_regulations: list[str] = Field(default_factory=list)
    
    # Details
    summary: str = Field(default="", description="Summary of requirements")
    requirements: list[str] = Field(default_factory=list)
    restrictions: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    
    # Sources
    sources: list[DataSource] = Field(default_factory=list)
    
    # Metadata
    tool_used: str = Field(default="regulatory_checker")
    cost: float = Field(default=0.0)
    error: Optional[str] = Field(default=None)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================
# REGULATORY CHECKER
# ============================================================

class RegulatoryChecker:
    """
    Check regulatory compliance for skill gaming.
    
    Process:
    1. Get baseline info from knowledge base
    2. Supplement with web research for recent changes
    3. Generate structured assessment
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with OpenAI API key for research."""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
    
    def _get_baseline_info(self, jurisdiction: str) -> dict:
        """Get baseline regulatory info from knowledge base."""
        jurisdiction_lower = jurisdiction.lower().strip()
        
        # Check direct match
        if jurisdiction_lower in JURISDICTION_INFO:
            return JURISDICTION_INFO[jurisdiction_lower]
        
        # Check common variations
        variations = {
            "united kingdom": "uk",
            "britain": "uk",
            "great britain": "uk",
            "england": "uk",
            "european union": "eu",
            "europe": "eu",
            "usa": "us",
            "united states": "us",
            "america": "us",
        }
        
        if jurisdiction_lower in variations:
            return JURISDICTION_INFO[variations[jurisdiction_lower]]
        
        return None
    
    async def _research_recent_changes(
        self,
        jurisdiction: str,
        jurisdiction_name: str
    ) -> Optional[str]:
        """Research recent regulatory changes via web search."""
        from src.tools.web_search import search_with_fallback
        
        query = (
            f"{jurisdiction_name} skill gaming gambling regulation 2024 2025 "
            f"real money gaming law license requirements recent changes"
        )
        
        result = await search_with_fallback(query)
        
        if result.success and result.answer:
            return result.answer
        
        return None
    
    async def check(
        self,
        jurisdiction: str,
        game_type: str = "skill_gaming"
    ) -> RegulatoryCheckResult:
        """
        Check regulatory compliance for a jurisdiction.
        
        Args:
            jurisdiction: Country/region code (e.g., 'uk', 'germany', 'eu')
            game_type: Type of gaming (default: skill_gaming)
            
        Returns:
            RegulatoryCheckResult with assessment
        """
        jurisdiction_lower = jurisdiction.lower().strip()
        
        # Get baseline info
        baseline = self._get_baseline_info(jurisdiction_lower)
        
        if not baseline:
            return RegulatoryCheckResult(
                success=False,
                jurisdiction=jurisdiction_lower,
                jurisdiction_name=jurisdiction,
                status=RegulatoryStatus.GRAY_AREA,
                error=f"No regulatory data available for: {jurisdiction}"
            )
        
        # Research recent changes
        recent_info = await self._research_recent_changes(
            jurisdiction_lower,
            baseline["name"]
        )
        
        # Build comprehensive summary
        summary = baseline["skill_gaming_notes"]
        if recent_info:
            summary += f"\n\nRecent developments:\n{recent_info[:500]}"
        
        # Generate requirements and recommendations
        requirements = []
        restrictions = []
        recommendations = []
        
        if baseline["licensing_required"]:
            requirements.append(f"Obtain license from {baseline['authority']}")
            requirements.append("Comply with local age verification requirements")
            requirements.append("Implement responsible gambling measures")
        
        if baseline["base_status"] == RegulatoryStatus.LEGAL_WITH_RESTRICTIONS:
            restrictions.append("Subject to advertising restrictions")
            restrictions.append("May have stake/prize limits")
            restrictions.append("Regular compliance reporting required")
        
        recommendations.append("Consult local legal counsel before launch")
        recommendations.append("Consider phased market entry approach")
        recommendations.append("Monitor regulatory developments actively")
        
        return RegulatoryCheckResult(
            success=True,
            jurisdiction=jurisdiction_lower,
            jurisdiction_name=baseline["name"],
            status=baseline["base_status"],
            licensing_required=baseline["licensing_required"],
            licensing_authority=baseline["authority"],
            key_regulations=baseline["key_laws"],
            summary=summary,
            requirements=requirements,
            restrictions=restrictions,
            recommendations=recommendations,
            sources=[
                DataSource(
                    source_type="regulation_database",
                    confidence=ConfidenceLevel.HIGH
                )
            ],
            cost=0.005 if recent_info else 0.0
        )
    
    def check_sync(
        self,
        jurisdiction: str,
        game_type: str = "skill_gaming"
    ) -> RegulatoryCheckResult:
        """Synchronous wrapper for check."""
        return asyncio.run(self.check(jurisdiction, game_type))
    
    async def check_multiple(
        self,
        jurisdictions: list[str]
    ) -> list[RegulatoryCheckResult]:
        """Check multiple jurisdictions in parallel."""
        tasks = [self.check(j) for j in jurisdictions]
        return await asyncio.gather(*tasks)


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

async def check_regulatory_compliance(
    region: str
) -> RegulatoryCheckResult:
    """
    Check regulatory compliance for a region.
    
    Task 4 interface: check_regulatory_compliance(region)
    
    Args:
        region: Country/region to check (e.g., 'uk', 'eu', 'germany')
        
    Returns:
        RegulatoryCheckResult with assessment
    """
    checker = RegulatoryChecker()
    return await checker.check(region)


def check_regulatory_compliance_sync(region: str) -> RegulatoryCheckResult:
    """Synchronous wrapper."""
    return asyncio.run(check_regulatory_compliance(region))


async def check_uk_eu_compliance() -> dict[str, RegulatoryCheckResult]:
    """
    Check compliance for UK and EU specifically.
    
    This directly answers Task 4 question:
    "Is this model legal in the UK/EU?"
    """
    checker = RegulatoryChecker()
    
    results = {}
    
    # Check UK
    results["uk"] = await checker.check("uk")
    
    # Check major EU markets
    for market in ["germany", "france", "spain", "italy", "netherlands"]:
        results[market] = await checker.check(market)
    
    # Check EU overall
    results["eu"] = await checker.check("eu")
    
    return results
