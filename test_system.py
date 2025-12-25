"""
============================================================
MRD Agent - Test Script
============================================================
Quick test to verify the system works.
============================================================
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all imports work."""
    print("Testing imports...")
    
    try:
        from src.models.companies import (
            VerifiedCompany, 
            TRIUMPH, 
            SKILLZ, 
            get_company,
            create_company_from_url,
            create_company_pair
        )
        print("  [OK] Companies module imported")
        
        from src.models.mrd import MRDOutput, StrategicAnalysis, CompetitorProfile
        print("  [OK] MRD models imported")
        
        from src.models.state import MRDState, ResearchTask, ResearchTaskType
        print("  [OK] State models imported")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Import error: {e}")
        return False


def test_company_database():
    """Test the company database."""
    print("\nTesting company database...")
    
    try:
        from src.models.companies import TRIUMPH, SKILLZ, get_company, create_company_from_url
        
        # Test TRIUMPH
        assert TRIUMPH.id == "triumph"
        assert "triumpharcade.com" in TRIUMPH.website
        assert TRIUMPH.official_name == "Triumph Labs, Inc."
        print(f"  [OK] TRIUMPH: {TRIUMPH.official_name} ({TRIUMPH.website})")
        
        # Test SKILLZ
        assert SKILLZ.id == "skillz"
        assert "skillz.com" in SKILLZ.website
        assert SKILLZ.stock_symbol == "SKLZ"
        print(f"  [OK] SKILLZ: {SKILLZ.official_name} ({SKILLZ.website})")
        
        # Test lookup
        company = get_company("triumph")
        assert company is not None
        assert company.id == "triumph"
        print("  [OK] get_company('triumph') works")
        
        # Test disambiguation query
        query = TRIUMPH.get_search_query("revenue growth")
        assert "triumpharcade.com" in query
        assert "Triumph Labs" in query
        print(f"  [OK] Disambiguated query: {query[:60]}...")
        
        # Test dynamic company creation
        new_company = create_company_from_url(
            "https://example.com",
            name="Example Corp",
            industry="Technology"
        )
        assert new_company.id == "example"
        assert get_company("example") is not None
        print("  [OK] Dynamic company creation works")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Company test error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mrd_models():
    """Test MRD output models."""
    print("\nTesting MRD models...")
    
    try:
        from src.models.mrd import (
            MRDOutput, MRDMetadata, StrategicAnalysis, MarketSize,
            AudienceInsight, CompetitorProfile, MarketPosition,
            SWOTAnalysis, SWOTItem, FeatureRecommendation,
            RegulatoryAssessment, JurisdictionAssessment, RegulatoryStatus
        )
        from datetime import datetime
        
        # Create a minimal valid MRD
        mrd = MRDOutput(
            metadata=MRDMetadata(
                prompt="Test prompt",
                domain="gambling"
            ),
            strategic_analysis=StrategicAnalysis(
                executive_summary="This is a comprehensive test executive summary for the MRD Agent system. It analyzes the competitive landscape between Triumph and Skillz in the real-money gaming market, focusing on market dynamics, user acquisition strategies, and regulatory compliance across key jurisdictions.",
                market_size=MarketSize(year=2024),
                target_audience=AudienceInsight(
                    demographic="Males 18-35",
                    behaviors=["Gaming"],
                    channels=["TikTok"]
                ),
                key_trends=["Trend 1"],
                market_dynamics="Test dynamics"
            ),
            competitors=[
                CompetitorProfile(
                    name="Test Company",
                    website="https://test.com",
                    description="A test company",
                    position=MarketPosition.CHALLENGER,
                    target_audience="Test audience",
                    key_strengths=["Strong"],
                    key_weaknesses=["Weak"]
                )
            ],
            swot=SWOTAnalysis(
                strengths=[
                    SWOTItem(statement="Strong brand recognition in gaming"),
                    SWOTItem(statement="Proprietary technology platform")
                ],
                weaknesses=[
                    SWOTItem(statement="Limited geographic coverage"),
                    SWOTItem(statement="High customer acquisition costs")
                ],
                opportunities=[
                    SWOTItem(statement="Expanding into new markets"),
                    SWOTItem(statement="Partnership opportunities with casinos")
                ],
                threats=[
                    SWOTItem(statement="Increasing regulatory pressure"),
                    SWOTItem(statement="Competition from established players")
                ]
            ),
            feature_recommendations=[
                FeatureRecommendation(
                    name="Social Gaming Features",
                    description="Add social features like friend challenges",
                    rationale="Increases engagement and retention"
                ),
                FeatureRecommendation(
                    name="Live Tournaments System",
                    description="Implement scheduled tournament events",
                    rationale="Creates recurring engagement loops"
                ),
                FeatureRecommendation(
                    name="Advanced Analytics Dashboard",
                    description="Provide users with gameplay statistics",
                    rationale="Improves user skill and satisfaction"
                )
            ],
            regulatory=RegulatoryAssessment(
                jurisdictions=[
                    JurisdictionAssessment(
                        jurisdiction="uk",
                        status=RegulatoryStatus.LEGAL_WITH_RESTRICTIONS
                    )
                ]
            ),
            gap_analysis=["Gap 1", "Gap 2"]
        )
        
        # Test serialization
        json_output = mrd.to_json()
        assert len(json_output) > 100
        print("  [OK] MRDOutput created and serialized to JSON")
        
        dict_output = mrd.to_dict()
        assert "metadata" in dict_output
        assert "strategic_analysis" in dict_output
        print("  [OK] MRDOutput serialized to dict (database-ready)")
        
        return True
    except Exception as e:
        print(f"  [FAIL] MRD model error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_state_model():
    """Test state model for LangGraph."""
    print("\nTesting state model...")
    
    try:
        from src.models.state import MRDState, ResearchTask, ResearchTaskType, AgentPhase
        
        # Create initial state
        state = MRDState(
            prompt="Test prompt for MRD generation",
            domain="gambling"
        )
        
        assert state.phase == AgentPhase.INITIALIZING
        assert state.iteration == 0
        assert state.confidence_score == 0.0
        print("  [OK] MRDState created with defaults")
        
        # Test state methods
        assert not state.has_enough_research()  # No research yet
        assert state.should_retry()  # Confidence is 0
        print("  [OK] State transition methods work")
        
        # Test status summary - now returns Pydantic StateSummary
        summary = state.get_status_summary()
        assert summary.phase == "initializing"
        assert summary.iteration == 0
        print(f"  [OK] Status summary: phase={summary.phase}, iteration={summary.iteration}")
        
        return True
    except Exception as e:
        print(f"  [FAIL] State model error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("  MRD Agent v2.0 - System Test")
    print("=" * 60)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Company Database", test_company_database()))
    results.append(("MRD Models", test_mrd_models()))
    results.append(("State Model", test_state_model()))
    
    print("\n" + "=" * 60)
    print("  Test Results")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for name, result in results:
        status = "[OK] PASS" if result else "[FAIL] FAIL"
        print(f"  {name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n  Total: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
