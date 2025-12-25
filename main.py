"""
============================================================
MRD Agent - Main Entry Point
============================================================
Usage:
    python main.py                  # Run in CLI mode
    python main.py --api            # Start API server
    python main.py --test           # Run system tests
    
Task 4 Requirement: Production-ready entry point with
multiple execution modes.
============================================================
"""

import sys
import os
import asyncio
import argparse

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_cli():
    """
    Run the MRD Agent in CLI (command line) mode.
    
    This is the interactive mode where:
    1. User provides a prompt
    2. Agent creates research plan
    3. Human approves the plan
    4. Agent executes research
    5. Agent synthesizes MRD
    6. Human reviews final output
    """
    from src.agents.orchestrator import run_mrd_agent
    from src.models.companies import TRIUMPH, SKILLZ
    
    print("=" * 60)
    print("  MRD Agent v2.0 - CLI Mode")
    print("=" * 60)
    print()
    print("Focus Companies:")
    print(f"  1. {TRIUMPH.official_name} ({TRIUMPH.website})")
    print(f"  2. {SKILLZ.official_name} ({SKILLZ.website})")
    print()
    
    # Default prompt for Task 4
    default_prompt = (
        "I'm building a skill-based real-money gaming app. "
        "Create a competitive analysis comparing Triumph (triumpharcade.com) "
        "and Skillz (skillz.com). Include market analysis, SWOT, "
        "regulatory assessment for UK/EU, and feature recommendations."
    )
    
    print("Default prompt:")
    print(f"  {default_prompt[:80]}...")
    print()
    
    user_input = input("Press Enter to use default, or type your prompt: ").strip()
    prompt = user_input if user_input else default_prompt
    
    print()
    print("Starting MRD Agent...")
    print("-" * 60)
    
    # Run the agent
    try:
        result = asyncio.run(run_mrd_agent(prompt))
        
        if result:
            print()
            print("=" * 60)
            print("  MRD Generation Complete!")
            print("=" * 60)
            
            # Save output
            output_dir = os.path.join(os.path.dirname(__file__), "outputs")
            os.makedirs(output_dir, exist_ok=True)
            
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(output_dir, f"mrd_{timestamp}.json")
            
            # Handle both Pydantic model and dict output
            if hasattr(result, 'model_dump'):
                output_data = result.model_dump()
            else:
                output_data = result
            
            with open(output_file, "w", encoding="utf-8") as f:
                import json
                json.dump(output_data, f, indent=2, default=str)
            
            print(f"Output saved to: {output_file}")
            
            # ------------------------------------------------------------------
            # Generate Markdown
            # ------------------------------------------------------------------
            md_path = os.path.join(output_dir, f"mrd_{timestamp}.md")
            
            # Construct MD content
            # (Assuming mrd_output structure)
            mrd = result # result is the Pydantic model
            
            md_content = f"# Market Requirements Document\n\n"
            if hasattr(mrd, 'metadata'):
               md_content += f"**Prompt:** {mrd.metadata.prompt}\n"
               md_content += f"**Generated:** {mrd.metadata.generated_at}\n"
               md_content += f"**Cost:** ${mrd.metadata.total_research_cost:.4f}\n\n"
            
            # === Strategic Analysis ===
            if hasattr(mrd, 'strategic_analysis'):
                sa = mrd.strategic_analysis
                md_content += f"## Executive Summary\n\n{sa.executive_summary}\n\n"

                # Market Size
                if hasattr(sa, 'market_size') and sa.market_size:
                    ms = sa.market_size
                    md_content += "### Market Size\n\n"
                    if ms.tam: md_content += f"- **TAM:** ${ms.tam:.2f}B\n"
                    if ms.sam: md_content += f"- **SAM:** ${ms.sam:.2f}B\n"
                    if ms.cagr: md_content += f"- **CAGR:** {ms.cagr:.1f}%\n"
                    md_content += f"- **Projection Year:** {ms.year}\n\n"

                # Target Audience
                if hasattr(sa, 'target_audience') and sa.target_audience:
                    ta = sa.target_audience
                    md_content += "### Target Audience\n\n"
                    md_content += f"**Demographics:** {ta.demographic}\n\n"
                    if ta.behaviors:
                        md_content += "**Behaviors:**\n"
                        for b in ta.behaviors: md_content += f"- {b}\n"
                        md_content += "\n"
                    if ta.channels:
                        md_content += "**Channels:**\n"
                        for c in ta.channels: md_content += f"- {c}\n"
                        md_content += "\n"
                    if ta.influencer_strategy:
                        md_content += f"**Influencer Strategy:** {ta.influencer_strategy}\n\n"

                # Key Trends
                if hasattr(sa, 'key_trends') and sa.key_trends:
                    md_content += "### Key Trends\n\n"
                    for t in sa.key_trends: md_content += f"- {t}\n"
                    md_content += "\n"

                # Market Dynamics
                if hasattr(sa, 'market_dynamics') and sa.market_dynamics:
                    md_content += f"### Market Dynamics\n\n{sa.market_dynamics}\n\n"

            # === Competitor Analysis ===
            if hasattr(mrd, 'competitors'):
                md_content += "## Competitor Analysis\n\n"
                for comp in mrd.competitors:
                    md_content += f"### {comp.name}\n"
                    md_content += f"**Website:** {comp.website}\n\n"
                    md_content += f"{comp.description}\n\n"
                    if hasattr(comp, 'target_audience') and comp.target_audience:
                        md_content += f"**Target Audience:** {comp.target_audience}\n\n"
                    if hasattr(comp, 'app_metrics') and comp.app_metrics:
                        am = comp.app_metrics
                        if am.app_store_rating: md_content += f"**App Store Rating:** {am.app_store_rating}/5\n"
                        if am.downloads_estimate: md_content += f"**Downloads:** {am.downloads_estimate}\n"
                        md_content += "\n"
                    if hasattr(comp, 'financials') and comp.financials:
                        fin = comp.financials
                        if fin.revenue_annual: md_content += f"**Annual Revenue:** ${fin.revenue_annual:,.0f}\n"
                        if fin.funding_total: md_content += f"**Total Funding:** ${fin.funding_total}M\n"
                        if fin.revenue_growth_yoy: md_content += f"**YoY Growth:** {fin.revenue_growth_yoy:.1f}%\n"
                        md_content += "\n"
                    if hasattr(comp, 'key_strengths') and comp.key_strengths:
                        md_content += "**Strengths:**\n"
                        for s in comp.key_strengths: md_content += f"- {s}\n"
                        md_content += "\n"
                    if hasattr(comp, 'key_weaknesses') and comp.key_weaknesses:
                        md_content += "**Weaknesses:**\n"
                        for w in comp.key_weaknesses: md_content += f"- {w}\n"
                        md_content += "\n"
                    if hasattr(comp, 'games_offered') and comp.games_offered:
                        md_content += f"**Games Offered:** {', '.join(comp.games_offered)}\n\n"

            # === SWOT Analysis ===
            if hasattr(mrd, 'swot') and mrd.swot:
                sw = mrd.swot
                md_content += "## SWOT Analysis\n\n"
                if sw.strengths:
                    md_content += "### Strengths\n"
                    for item in sw.strengths: md_content += f"- **[{item.impact.upper()}]** {item.statement}\n"
                    md_content += "\n"
                if sw.weaknesses:
                    md_content += "### Weaknesses\n"
                    for item in sw.weaknesses: md_content += f"- **[{item.impact.upper()}]** {item.statement}\n"
                    md_content += "\n"
                if sw.opportunities:
                    md_content += "### Opportunities\n"
                    for item in sw.opportunities: md_content += f"- **[{item.impact.upper()}]** {item.statement}\n"
                    md_content += "\n"
                if sw.threats:
                    md_content += "### Threats\n"
                    for item in sw.threats: md_content += f"- **[{item.impact.upper()}]** {item.statement}\n"
                    md_content += "\n"

            # === Feature Recommendations ===
            if hasattr(mrd, 'feature_recommendations'):
                md_content += "## Feature Recommendations\n\n"
                for feat in mrd.feature_recommendations:
                    md_content += f"### {feat.name} ({feat.priority.upper()})\n"
                    md_content += f"{feat.description}\n\n"
                    md_content += f"**Rationale:** {feat.rationale}\n\n"
                    md_content += f"**Effort:** {feat.effort_estimate}\n"
                    if feat.competitor_reference:
                        md_content += f"**Reference:** {feat.competitor_reference}\n"
                    md_content += "\n"

            # === Gap Analysis ===
            if hasattr(mrd, 'gap_analysis') and mrd.gap_analysis:
                md_content += "## Gap Analysis\n\n"
                md_content += "Games and features not currently offered by key competitors:\n\n"
                for gap in mrd.gap_analysis:
                    md_content += f"- {gap}\n"
                md_content += "\n"

            # === Regulatory Compliance ===
            if hasattr(mrd, 'regulatory'):
                reg = mrd.regulatory
                md_content += "## Regulatory Compliance\n\n"
                md_content += f"**Overall Risk Level:** {reg.overall_risk_level.upper()}\n\n"
                if reg.recommended_launch_markets:
                    md_content += f"**Recommended Launch Markets:** {', '.join(reg.recommended_launch_markets)}\n\n"
                if reg.markets_to_avoid:
                    md_content += f"**Markets to Avoid:** {', '.join(reg.markets_to_avoid)}\n\n"
                
                md_content += "### Jurisdiction Details\n\n"
                for jur in reg.jurisdictions:
                    md_content += f"#### {jur.jurisdiction.upper()}\n"
                    md_content += f"**Status:** {jur.status.value.replace('_', ' ').title()}\n\n"
                    if jur.licensing_authority:
                        md_content += f"**Licensing Authority:** {jur.licensing_authority}\n\n"
                    if jur.key_regulations:
                        md_content += "**Key Regulations:**\n"
                        for r in jur.key_regulations: md_content += f"- {r}\n"
                        md_content += "\n"
                    if jur.notes:
                        md_content += f"**Notes:** {jur.notes}\n\n"

            # === References ===
            if hasattr(mrd, 'references') and mrd.references:
                md_content += "## References\n\n"
                for i, ref in enumerate(mrd.references, 1):
                    md_content += f"{i}. {ref}\n"
                md_content += "\n"


            # Save MD
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md_content)
            print(f"Markdown saved to: {md_path}")
            
            # ------------------------------------------------------------------
            # Generate Professional PDF
            # ------------------------------------------------------------------
            pdf_path = os.path.join(output_dir, f"mrd_{timestamp}.pdf")
            try:
                from src.output.pdf_generator import generate_professional_pdf, PDFConfig
                
                # Configure PDF
                pdf_config = PDFConfig(
                    title="Market Requirements Document",
                    subtitle="Triumph vs Skillz Competitive Analysis",
                    author="MRD Agent v2.0",
                    show_cover_page=True,
                    show_toc=False,  # TOC can be added later
                )
                
                # Generate professional PDF
                generate_professional_pdf(
                    mrd_data=output_data,
                    output_path=pdf_path,
                    config=pdf_config
                )
                
                print(f"Professional PDF saved to: {pdf_path}")
                    
            except ImportError as ie:
                print(f"Skipping PDF generation (libraries not found): {ie}")
                # Fallback to basic xhtml2pdf if available
                try:
                    import markdown
                    from xhtml2pdf import pisa
                    
                    html_text = markdown.markdown(md_content)
                    html_content = f"""
                    <html>
                    <head>
                        <style>
                            body {{ font-family: Helvetica, sans-serif; font-size: 12px; }}
                            h1 {{ color: #2c3e50; }}
                            h2 {{ color: #34495e; margin-top: 20px; }}
                            h3 {{ color: #7f8c8d; }}
                        </style>
                    </head>
                    <body>
                        {html_text}
                    </body>
                    </html>
                    """
                    
                    with open(pdf_path, "wb") as pdf_file:
                        pisa_status = pisa.CreatePDF(html_content, dest=pdf_file)
                    
                    if not pisa_status.err:
                        print(f"Fallback PDF saved to: {pdf_path}")
                except Exception:
                    pass
            except Exception as pe:
                 print(f"PDF generation failed: {pe}")

        else:
            print("MRD generation failed or was cancelled.")
            
    except KeyboardInterrupt:
        print("\nCancelled by user.")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


def run_api():
    """
    Start the FastAPI server for web-based access.
    
    The API provides:
    - POST /generate - Start MRD generation
    - GET /jobs/{id} - Check job status
    - GET /health - Health check
    """
    import uvicorn
    
    print("=" * 60)
    print("  MRD Agent v2.0 - API Server")
    print("=" * 60)
    print()
    print("Starting FastAPI server...")
    print("API will be available at: http://localhost:8000")
    print("API docs at: http://localhost:8000/docs")
    print()
    print("Press Ctrl+C to stop")
    print("-" * 60)
    
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


def run_tests():
    """Run system tests."""
    print("=" * 60)
    print("  MRD Agent v2.0 - Running Tests")
    print("=" * 60)
    print()
    
    # Import and run test module
    from test_system import main as test_main
    success = test_main()
    
    return 0 if success else 1


def check_environment():
    """Check that required environment variables are set."""
    from dotenv import load_dotenv
    load_dotenv()
    
    required = ["OPENAI_API_KEY"]
    recommended = ["PERPLEXITY_API_KEY", "FIRECRAWL_API_KEY"]
    
    missing_required = []
    missing_recommended = []
    
    for var in required:
        if not os.getenv(var):
            missing_required.append(var)
    
    for var in recommended:
        if not os.getenv(var):
            missing_recommended.append(var)
    
    if missing_required:
        print("ERROR: Missing required environment variables:")
        for var in missing_required:
            print(f"  - {var}")
        print()
        print("Please set these in your .env file.")
        return False
    
    if missing_recommended:
        print("WARNING: Missing recommended environment variables:")
        for var in missing_recommended:
            print(f"  - {var}")
        print("Some features may not work without these.")
        print()
    
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="MRD Agent - AI-powered Market Requirements Document generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py              Run in interactive CLI mode
  python main.py --api        Start the API server
  python main.py --test       Run system tests
  python main.py --check      Check environment setup
        """
    )
    
    parser.add_argument(
        "--api",
        action="store_true",
        help="Start the FastAPI server"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run system tests"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check environment setup"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="MRD Agent v2.0.0"
    )
    
    args = parser.parse_args()
    
    # Check environment first (unless just checking or testing)
    if not args.test and not args.check:
        if not check_environment():
            return 1
    
    # Execute requested mode
    if args.check:
        print("Checking environment...")
        if check_environment():
            print("Environment OK!")
            return 0
        return 1
    
    if args.test:
        return run_tests()
    
    if args.api:
        run_api()
        return 0
    
    # Default: CLI mode
    run_cli()
    return 0


if __name__ == "__main__":
    sys.exit(main())
