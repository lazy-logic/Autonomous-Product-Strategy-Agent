"""
============================================================
MRD Agent - Verified Companies Database
============================================================
PURPOSE: Fix the critical bug where "Triumph" was researched as 
         Triumph Motorcycles instead of Triumph Arcade.

This module contains VERIFIED company information that serves as
the ground truth for all research. Before any web search, the agent
MUST use this data to ensure correct company identification.

SUPERVISOR FEEDBACK (Mark):
1. Fix research prompt to use actual Triumph (triumpharcade.com)
2. Fix research prompt to use actual Skillz (skillz.com)
3. Focus research ONLY on these two companies
============================================================
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from enum import Enum


class CompanyStatus(str, Enum):
    """Company operational status."""
    PRIVATE = "private"
    PUBLIC = "public"
    ACQUIRED = "acquired"
    DEFUNCT = "defunct"


class VerifiedCompany(BaseModel):
    """
    Verified company information.
    
    This model contains GROUND TRUTH data that must be used to 
    disambiguate company searches. Every field is intentional.
    """
    
    # === IDENTITY (Required for disambiguation) ===
    id: str = Field(
        ...,
        description="Unique identifier (lowercase, no spaces)"
    )
    official_name: str = Field(
        ...,
        description="Legal company name as registered"
    )
    common_names: list[str] = Field(
        default_factory=list,
        description="Alternative names the company is known by"
    )
    
    # === DIGITAL PRESENCE (Required for scraping) ===
    website: str = Field(
        ...,
        description="Official website URL - USE THIS FOR RESEARCH"
    )
    app_store_id: Optional[str] = Field(
        default=None,
        description="Apple App Store ID for app-based companies"
    )
    play_store_id: Optional[str] = Field(
        default=None,
        description="Google Play Store ID"
    )
    
    # === BUSINESS INFO ===
    industry: str = Field(
        ...,
        description="Primary industry vertical"
    )
    description: str = Field(
        ...,
        description="One-line company description"
    )
    founded_year: Optional[int] = Field(
        default=None,
        description="Year company was founded"
    )
    headquarters: Optional[str] = Field(
        default=None,
        description="City, Country of headquarters"
    )
    
    # === MARKET STATUS ===
    status: CompanyStatus = Field(
        ...,
        description="Current operational status"
    )
    stock_symbol: Optional[str] = Field(
        default=None,
        description="Stock ticker if publicly traded"
    )
    
    # === DISAMBIGUATION ===
    not_to_confuse_with: list[str] = Field(
        default_factory=list,
        description="Common confusions to AVOID in searches"
    )
    search_keywords: list[str] = Field(
        default_factory=list,
        description="Keywords to ADD to searches for disambiguation"
    )

    def get_search_query(self, topic: str) -> str:
        """
        Generate a disambiguated search query.
        
        Instead of searching "Triumph revenue", this generates:
        "Triumph Arcade triumpharcade.com real-money gaming revenue"
        
        This prevents the Triumph Motorcycles confusion.
        """
        keywords = " ".join(self.search_keywords[:3])  # Top 3 keywords
        return f"{self.official_name} {self.website} {keywords} {topic}"


# ============================================================
# VERIFIED COMPANY DATABASE
# ============================================================
# These are the ONLY two companies for Task 4.
# All research MUST use these as ground truth.
# ============================================================

TRIUMPH = VerifiedCompany(
    # Identity
    id="triumph",
    official_name="Triumph Labs, Inc.",
    common_names=["Triumph", "Triumph Arcade", "Triumph Play"],
    
    # Digital Presence
    website="https://triumpharcade.com",
    app_store_id="1608987929",  # Triumph: Play for Cash
    # NOTE: Triumph is NOT on Google Play - distributed via APK from website
    # due to Google's real-money gaming policies. Previous apps were unpublished in 2025.
    play_store_id=None,
    
    # Business Info
    industry="Real-money Skill Gaming",
    description="Mobile skill-based gaming platform with real cash prizes",
    founded_year=2021,
    headquarters="San Francisco, USA",
    
    # Market Status
    status=CompanyStatus.PRIVATE,
    stock_symbol=None,
    
    # Disambiguation - CRITICAL
    not_to_confuse_with=[
        "Triumph Motorcycles",     # UK motorcycle manufacturer
        "Triumph Group",           # Aerospace company
        "Triumph Foods",           # Meat processing
        "Triumph Bancshares",      # Banking
    ],
    search_keywords=[
        "real-money gaming",
        "skill-based",
        "mobile arcade",
        "cash prizes",
        "triumpharcade.com",
    ],
)

SKILLZ = VerifiedCompany(
    # Identity
    id="skillz",
    official_name="Skillz Inc.",
    common_names=["Skillz", "Skillz Platform", "Skillz Gaming"],
    
    # Digital Presence
    website="https://www.skillz.com",
    app_store_id="1524107950",  # Skillz: Compete & Win Cash
    # NOTE: Skillz is NOT on Google Play due to Google's cash prize policies.
    # They distribute via Samsung Galaxy Store and direct APK downloads.
    play_store_id=None,
    
    # Business Info
    industry="Mobile eSports Platform",
    description="Mobile eSports platform enabling real-money tournaments",
    founded_year=2012,
    headquarters="San Francisco, USA",
    
    # Market Status
    status=CompanyStatus.PUBLIC,
    stock_symbol="SKLZ",  # NYSE listed
    
    # Disambiguation
    not_to_confuse_with=[
        "Skills training",
        "Skillsoft",              # Corporate learning
        "Skillshare",             # Online courses
    ],
    search_keywords=[
        "mobile esports",
        "SKLZ stock",
        "real-money tournaments",
        "skillz.com",
        "NYSE SKLZ",
    ],
)


# ============================================================
# COMPANY LOOKUP FUNCTIONS
# ============================================================

# Registry of all verified companies
_COMPANY_REGISTRY: dict[str, VerifiedCompany] = {
    "triumph": TRIUMPH,
    "skillz": SKILLZ,
}


def get_company(name: str) -> Optional[VerifiedCompany]:
    """
    Look up a verified company by name.
    
    Args:
        name: Company name or ID (case-insensitive)
        
    Returns:
        VerifiedCompany if found, None otherwise
        
    Example:
        >>> company = get_company("triumph")
        >>> company.website
        'https://triumpharcade.com'
    """
    name_lower = name.lower().strip()
    
    # Direct ID match
    if name_lower in _COMPANY_REGISTRY:
        return _COMPANY_REGISTRY[name_lower]
    
    # Search by common names
    for company in _COMPANY_REGISTRY.values():
        if name_lower in [n.lower() for n in company.common_names]:
            return company
    
    return None


def get_all_companies() -> list[VerifiedCompany]:
    """Return all verified companies."""
    return list(_COMPANY_REGISTRY.values())


def get_focus_companies() -> tuple[VerifiedCompany, VerifiedCompany]:
    """
    Return the two focus companies for Task 4.
    
    Returns:
        Tuple of (TRIUMPH, SKILLZ) - the only companies to research.
    """
    return (TRIUMPH, SKILLZ)


# ============================================================
# DYNAMIC COMPANY REGISTRATION
# ============================================================
# These functions allow adding new companies at runtime,
# so the agent can research ANY company, not just the 
# pre-defined ones.
# ============================================================

def register_company(company: VerifiedCompany) -> None:
    """
    Register a new company in the database.
    
    This allows dynamic addition of companies for research.
    
    Args:
        company: VerifiedCompany to add
        
    Example:
        >>> new_company = VerifiedCompany(
        ...     id="pocket7",
        ...     official_name="Pocket7Games",
        ...     website="https://pocket7games.com",
        ...     industry="Skill Gaming",
        ...     description="Mobile skill gaming platform",
        ...     status=CompanyStatus.PRIVATE
        ... )
        >>> register_company(new_company)
    """
    _COMPANY_REGISTRY[company.id.lower()] = company


def create_company_from_url(
    url: str,
    name: Optional[str] = None,
    industry: str = "Technology",
    description: str = ""
) -> VerifiedCompany:
    """
    Create a company profile from just a URL.
    
    This is the EASY WAY to add a new company for research.
    The agent will use the URL for disambiguation in searches.
    
    Args:
        url: Official website URL (e.g., "https://example.com")
        name: Company name (optional, extracted from URL if not provided)
        industry: Industry vertical
        description: One-line description
        
    Returns:
        VerifiedCompany that's automatically registered
        
    Example:
        >>> company = create_company_from_url(
        ...     "https://pocket7games.com",
        ...     name="Pocket7Games",
        ...     industry="Skill Gaming"
        ... )
        >>> # Now you can use company.id in searches
    """
    from urllib.parse import urlparse
    
    # Extract domain for ID and name
    parsed = urlparse(url if url.startswith("http") else f"https://{url}")
    domain = parsed.netloc.replace("www.", "")
    
    # Generate ID from domain
    company_id = domain.split(".")[0].lower()
    
    # Use provided name or generate from domain
    if not name:
        name = company_id.title()
    
    # Create company with URL as primary search keyword
    company = VerifiedCompany(
        id=company_id,
        official_name=name,
        common_names=[name, company_id],
        website=url if url.startswith("http") else f"https://{url}",
        industry=industry,
        description=description or f"Company at {domain}",
        status=CompanyStatus.PRIVATE,
        search_keywords=[domain, name.lower()],
    )
    
    # Auto-register
    register_company(company)
    
    return company


def create_company_pair(
    company1_url: str,
    company1_name: str,
    company2_url: str,
    company2_name: str,
    industry: str = "Technology"
) -> tuple[VerifiedCompany, VerifiedCompany]:
    """
    Create a pair of companies for comparison research.
    
    This is the RECOMMENDED way to set up a new research task
    comparing two companies.
    
    Args:
        company1_url: First company's website
        company1_name: First company's name
        company2_url: Second company's website
        company2_name: Second company's name
        industry: Shared industry vertical
        
    Returns:
        Tuple of two VerifiedCompany instances
        
    Example:
        >>> notion, coda = create_company_pair(
        ...     "https://notion.so", "Notion",
        ...     "https://coda.io", "Coda",
        ...     industry="Productivity SaaS"
        ... )
    """
    c1 = create_company_from_url(company1_url, company1_name, industry)
    c2 = create_company_from_url(company2_url, company2_name, industry)
    return (c1, c2)


def clear_registry_except_defaults() -> None:
    """
    Clear all dynamically added companies, keeping only defaults.
    
    Useful for resetting between research sessions.
    """
    global _COMPANY_REGISTRY
    _COMPANY_REGISTRY = {
        "triumph": TRIUMPH,
        "skillz": SKILLZ,
    }
