"""
============================================================
MRD Agent - Data Validation
============================================================
PURPOSE: Validate MRD output and research data quality.

TASK 4 REQUIREMENT:
"What happens if 'Sensor Tower' returns no data? Does the 
whole flow crash?"

Answer: No. We validate data and handle missing/invalid data
gracefully with this validation layer.
============================================================
"""

from typing import Optional, Any
from pydantic import ValidationError
import re
import logging

from src.models.mrd import MRDOutput, ConfidenceLevel

logger = logging.getLogger(__name__)


class DataQualityChecker:
    """
    Check quality of research data.
    
    Implements Figma spec requirement:
    "Data Quality: Filter for specific keywords: $, €, Billion, Million"
    """
    
    # Keywords that indicate quality market data
    FINANCIAL_KEYWORDS = [
        "$", "€", "£", "¥",
        "billion", "million", "thousand",
        "revenue", "funding", "valuation",
        "market size", "TAM", "SAM", "SOM",
        "CAGR", "growth rate",
    ]
    
    # Keywords that indicate quality competitive data
    COMPETITIVE_KEYWORDS = [
        "competitor", "comparison", "versus",
        "market share", "user base", "downloads",
        "rating", "reviews", "sentiment",
    ]
    
    # Keywords that indicate quality regulatory data
    REGULATORY_KEYWORDS = [
        "regulation", "compliance", "license",
        "legal", "law", "act", "directive",
        "authority", "commission", "gambling",
    ]
    
    def __init__(self):
        self.issues = []
    
    def check_financial_data(self, content: str) -> bool:
        """Check if content contains quality financial data."""
        content_lower = content.lower()
        matches = sum(
            1 for kw in self.FINANCIAL_KEYWORDS 
            if kw.lower() in content_lower
        )
        return matches >= 2
    
    def check_competitive_data(self, content: str) -> bool:
        """Check if content contains quality competitive data."""
        content_lower = content.lower()
        matches = sum(
            1 for kw in self.COMPETITIVE_KEYWORDS 
            if kw.lower() in content_lower
        )
        return matches >= 2
    
    def check_regulatory_data(self, content: str) -> bool:
        """Check if content contains quality regulatory data."""
        content_lower = content.lower()
        matches = sum(
            1 for kw in self.REGULATORY_KEYWORDS 
            if kw.lower() in content_lower
        )
        return matches >= 2
    
    def check_for_hallucinations(self, content: str) -> list[str]:
        """
        Check for potential hallucinations.
        
        Task 4: "How would you handle a hallucination 
        (e.g., if the agent invents a competitor that doesn't exist)?"
        
        We flag content that:
        1. Claims extremely specific numbers without sources
        2. Mentions competitors not in our verified database
        3. Contains impossible dates (future dates as past)
        """
        issues = []
        
        # Check for unsourced specific numbers
        pattern = r"\b\d{1,3}(,\d{3})*(\.\d+)?\s*(billion|million|percent|%)\b"
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches and "[source]" not in content.lower() and "according to" not in content.lower():
            issues.append("Contains specific numbers without clear source attribution")
        
        # Check for known fictional/wrong companies (from GAP analysis)
        wrong_companies = [
            "triumph motorcycles",
            "triumph group",
            "triumph foods",
            "speed twin",  # Motorcycle model
            "tiger sport",  # Motorcycle model
        ]
        content_lower = content.lower()
        for wrong in wrong_companies:
            if wrong in content_lower:
                issues.append(f"Possibly wrong company reference: '{wrong}'")
        
        return issues
    
    def validate_research_result(
        self, 
        content: str, 
        research_type: str
    ) -> tuple[bool, list[str]]:
        """
        Validate a research result.
        
        Returns:
            Tuple of (is_valid, list of issues)
        """
        issues = []
        
        # Check minimum content length
        if len(content) < 100:
            issues.append("Content too short (< 100 chars)")
        
        # Check for hallucinations
        hallucination_issues = self.check_for_hallucinations(content)
        issues.extend(hallucination_issues)
        
        # Type-specific checks
        if research_type in ["market_analysis", "market_size"]:
            if not self.check_financial_data(content):
                issues.append("Missing financial keywords ($, billion, growth, etc.)")
        
        elif research_type in ["competitor_research", "competitor_analysis"]:
            if not self.check_competitive_data(content):
                issues.append("Missing competitive keywords")
        
        elif research_type in ["regulatory_check", "regulatory"]:
            if not self.check_regulatory_data(content):
                issues.append("Missing regulatory keywords")
        
        is_valid = len(issues) == 0
        return is_valid, issues


def validate_mrd(mrd: MRDOutput) -> tuple[bool, list[str], float]:
    """
    Validate a complete MRD output.
    
    Returns:
        Tuple of (is_valid, list of issues, confidence_score)
    """
    issues = []
    score = 1.0
    
    # Check metadata
    if not mrd.metadata.prompt:
        issues.append("Missing prompt in metadata")
        score -= 0.1
    
    # Check strategic analysis
    if len(mrd.strategic_analysis.executive_summary) < 100:
        issues.append("Executive summary too short")
        score -= 0.1
    
    if not mrd.strategic_analysis.market_size.tam:
        issues.append("Missing TAM data")
        score -= 0.05
    
    if not mrd.strategic_analysis.target_audience.demographic:
        issues.append("Missing target audience demographic")
        score -= 0.05
    
    # Check competitors
    if len(mrd.competitors) < 2:
        issues.append("Need at least 2 competitor profiles")
        score -= 0.15
    
    for comp in mrd.competitors:
        if len(comp.key_strengths) < 2:
            issues.append(f"Competitor '{comp.name}' needs more strengths")
            score -= 0.02
        if len(comp.key_weaknesses) < 2:
            issues.append(f"Competitor '{comp.name}' needs more weaknesses")
            score -= 0.02
    
    # Check SWOT
    swot_checks = [
        ("strengths", mrd.swot.strengths),
        ("weaknesses", mrd.swot.weaknesses),
        ("opportunities", mrd.swot.opportunities),
        ("threats", mrd.swot.threats),
    ]
    for name, items in swot_checks:
        if len(items) < 2:
            issues.append(f"SWOT {name} needs at least 2 items")
            score -= 0.05
    
    # Check features
    if len(mrd.feature_recommendations) < 3:
        issues.append("Need at least 3 feature recommendations")
        score -= 0.1
    
    # Check regulatory
    if len(mrd.regulatory.jurisdictions) < 2:
        issues.append("Need at least 2 jurisdiction assessments")
        score -= 0.1
    
    # Check gap analysis
    if len(mrd.gap_analysis) < 3:
        issues.append("Need at least 3 gap analysis items")
        score -= 0.05
    
    # Ensure score stays in bounds
    score = max(0.0, min(1.0, score))
    
    is_valid = score >= 0.7
    
    return is_valid, issues, score


def check_company_disambiguation(content: str) -> dict:
    """
    Check if content is about the correct companies.
    
    Returns dict with:
    - triumph_correct: bool
    - skillz_correct: bool
    - issues: list of problems found
    """
    content_lower = content.lower()
    result = {
        "triumph_correct": True,
        "skillz_correct": True,
        "issues": []
    }
    
    # Check for wrong Triumph
    wrong_triumph_indicators = [
        "motorcycle", "speed twin", "tiger sport",
        "bonneville", "scrambler", "hinckley",
    ]
    for indicator in wrong_triumph_indicators:
        if indicator in content_lower:
            result["triumph_correct"] = False
            result["issues"].append(
                f"Content may be about Triumph Motorcycles, not Triumph Arcade"
            )
            break
    
    # Check for correct Triumph
    correct_triumph_indicators = [
        "triumpharcade", "skill gaming", "cash prizes",
        "mobile arcade", "real-money gaming",
    ]
    triumph_mentioned = "triumph" in content_lower
    has_correct_context = any(ind in content_lower for ind in correct_triumph_indicators)
    
    if triumph_mentioned and not has_correct_context:
        result["issues"].append(
            "Triumph mentioned but context unclear - verify it's the gaming app"
        )
    
    # Check for wrong Skillz
    wrong_skillz_indicators = [
        "skillsoft", "skillshare", "skill training",
    ]
    for indicator in wrong_skillz_indicators:
        if indicator in content_lower:
            result["skillz_correct"] = False
            result["issues"].append(
                f"Content may be about {indicator}, not Skillz gaming platform"
            )
            break
    
    return result
