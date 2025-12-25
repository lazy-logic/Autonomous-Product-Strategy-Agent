"""
============================================================
Professional PDF Report Generator v2
============================================================
PURPOSE: Generate beautifully designed, formal PDF reports.

DESIGN PRINCIPLES:
- Clean, corporate typography
- No markdown symbols (##, -, etc.)
- Proper spacing and hierarchy
- Professional color scheme
- Executive-ready formatting

100% PYDANTIC COMPLIANT
============================================================
"""

import os
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from fpdf import FPDF
from fpdf.enums import XPos, YPos

import logging
logger = logging.getLogger(__name__)


# ============================================================
# Configuration Models (100% Pydantic)
# ============================================================

class PDFColors(BaseModel):
    """Professional color scheme."""
    primary: tuple[int, int, int] = Field(default=(0, 51, 102), description="Navy blue")
    secondary: tuple[int, int, int] = Field(default=(51, 51, 51), description="Dark gray")
    accent: tuple[int, int, int] = Field(default=(0, 102, 153), description="Corporate blue")
    success: tuple[int, int, int] = Field(default=(0, 128, 64), description="Forest green")
    warning: tuple[int, int, int] = Field(default=(204, 102, 0), description="Orange")
    danger: tuple[int, int, int] = Field(default=(153, 0, 0), description="Dark red")
    text_primary: tuple[int, int, int] = Field(default=(33, 33, 33), description="Near black")
    text_secondary: tuple[int, int, int] = Field(default=(102, 102, 102), description="Gray")
    border: tuple[int, int, int] = Field(default=(200, 200, 200), description="Light gray")
    background: tuple[int, int, int] = Field(default=(248, 249, 250), description="Off-white")
    
    model_config = {"validate_assignment": True}


class PDFConfig(BaseModel):
    """PDF configuration."""
    title: str = Field(default="Market Requirements Document", description="Document title")
    subtitle: str = Field(default="Strategic Analysis Report", description="Subtitle")
    company: str = Field(default="", description="Company name")
    author: str = Field(default="MRD Agent", description="Author")
    confidential: bool = Field(default=True, description="Mark as confidential")
    colors: PDFColors = Field(default_factory=PDFColors, description="Color scheme")
    margin: int = Field(default=25, ge=15, le=40, description="Page margin mm")
    
    model_config = {"validate_assignment": True}


# ============================================================
# Professional PDF Class
# ============================================================

class FormalMRDReport(FPDF):
    """Professional formal MRD report generator."""
    
    def __init__(self, config: PDFConfig):
        super().__init__()
        self.config = config
        self.section_number = 0
        self.subsection_number = 0
        
        # Document setup
        self.set_title(config.title)
        self.set_author(config.author)
        self.set_creator("MRD Agent Professional Report Generator")
        self.set_auto_page_break(auto=True, margin=30)
        self.set_margins(config.margin, 20, config.margin)
    
    def header(self):
        """Clean professional header."""
        if self.page_no() == 1:
            return  # No header on cover
        
        # Header line
        self.set_y(10)
        self.set_draw_color(*self.config.colors.border)
        self.set_line_width(0.3)
        self.line(self.config.margin, 15, self.w - self.config.margin, 15)
        
        # Header text
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*self.config.colors.text_secondary)
        self.set_y(10)
        self.cell(0, 5, self.config.title, align="L")
        
        if self.config.confidential:
            self.cell(0, 5, "CONFIDENTIAL", align="R")
        
        self.set_y(20)
    
    def footer(self):
        """Professional footer with page numbers."""
        self.set_y(-20)
        
        # Footer line
        self.set_draw_color(*self.config.colors.border)
        self.set_line_width(0.3)
        self.line(self.config.margin, self.h - 18, self.w - self.config.margin, self.h - 18)
        
        # Page number
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*self.config.colors.text_secondary)
        self.set_y(-15)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")
    
    def add_cover_page(self, mrd_data: dict):
        """Professional cover page."""
        self.add_page()
        
        # Top accent bar
        self.set_fill_color(*self.config.colors.primary)
        self.rect(0, 0, self.w, 8, "F")
        
        # Title section
        self.set_y(60)
        self.set_font("Helvetica", "B", 28)
        self.set_text_color(*self.config.colors.primary)
        self.cell(0, 15, self.config.title, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        # Subtitle
        self.set_font("Helvetica", "", 14)
        self.set_text_color(*self.config.colors.text_secondary)
        self.cell(0, 10, self.config.subtitle, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        # Divider line
        self.ln(10)
        self.set_draw_color(*self.config.colors.primary)
        self.set_line_width(1)
        center = self.w / 2
        self.line(center - 30, self.get_y(), center + 30, self.get_y())
        
        # Metadata section
        self.ln(30)
        metadata = mrd_data.get("metadata", {})
        
        # Info box
        box_y = self.get_y()
        box_width = 120
        box_x = (self.w - box_width) / 2
        
        self.set_fill_color(*self.config.colors.background)
        self.set_draw_color(*self.config.colors.border)
        self.rect(box_x, box_y, box_width, 50, "FD")
        
        self.set_xy(box_x + 10, box_y + 8)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*self.config.colors.text_primary)
        
        # Document info
        info_items = [
            ("Date", self._format_date(metadata.get("generated_at"))),
            ("Domain", metadata.get("domain", "Market Analysis").title()),
            ("Confidence", f"{metadata.get('confidence_score', 0):.0%}" if isinstance(metadata.get('confidence_score'), (int, float)) else "N/A"),
        ]
        
        for label, value in info_items:
            self.set_x(box_x + 10)
            self.set_font("Helvetica", "B", 10)
            self.cell(35, 8, f"{label}:", align="L")
            self.set_font("Helvetica", "", 10)
            self.cell(70, 8, str(value), align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        # Bottom section
        self.set_y(220)
        if self.config.confidential:
            self.set_font("Helvetica", "B", 10)
            self.set_text_color(*self.config.colors.danger)
            self.cell(0, 8, "CONFIDENTIAL - FOR INTERNAL USE ONLY", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(*self.config.colors.text_secondary)
        self.cell(0, 8, f"Generated by {self.config.author}", align="C")
        
        # Bottom accent bar
        self.set_fill_color(*self.config.colors.primary)
        self.rect(0, self.h - 8, self.w, 8, "F")
    
    def _format_date(self, date_val) -> str:
        """Format date value safely."""
        if isinstance(date_val, datetime):
            return date_val.strftime("%B %d, %Y")
        elif isinstance(date_val, str):
            try:
                dt = datetime.fromisoformat(date_val.replace("Z", "+00:00"))
                return dt.strftime("%B %d, %Y")
            except:
                return date_val[:10] if len(str(date_val)) >= 10 else str(date_val)
        return datetime.now().strftime("%B %d, %Y")
    
    def add_section(self, title: str):
        """Add a numbered section header."""
        self.section_number += 1
        self.subsection_number = 0
        
        # Space before section
        if self.get_y() > 40:
            self.ln(8)
        
        # Section header
        self.set_x(self.config.margin)
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(*self.config.colors.primary)
        
        section_title = f"{self.section_number}. {title}"
        text_width = self.w - 2 * self.config.margin
        self.multi_cell(text_width, 10, section_title, align="L")
        
        # Underline
        self.set_draw_color(*self.config.colors.primary)
        self.set_line_width(0.8)
        self.line(self.config.margin, self.get_y() + 1, self.config.margin + 40, self.get_y() + 1)
        self.ln(8)
    
    def add_subsection(self, title: str):
        """Add a subsection header."""
        self.subsection_number += 1
        
        self.ln(4)
        self.set_x(self.config.margin)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*self.config.colors.secondary)
        
        sub_title = f"{self.section_number}.{self.subsection_number} {title}"
        text_width = self.w - 2 * self.config.margin
        self.multi_cell(text_width, 8, sub_title, align="L")
        self.ln(2)
    
    def add_paragraph(self, text: str):
        """Add a paragraph of text."""
        if not text:
            return
        
        self.set_x(self.config.margin)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*self.config.colors.text_primary)
        
        clean_text = self._clean_text(text)
        text_width = self.w - 2 * self.config.margin
        self.multi_cell(text_width, 6, clean_text, align="J")  # Justified
        self.ln(3)
    
    def add_field(self, label: str, value: str):
        """Add a labeled field (Key: Value)."""
        if not value:
            return
        
        self.set_x(self.config.margin)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*self.config.colors.text_primary)
        
        clean_value = self._clean_text(str(value))
        text_width = self.w - 2 * self.config.margin
        self.multi_cell(text_width, 6, f"{label}:  {clean_value}", align="L")
    
    def add_list(self, items: list, ordered: bool = False):
        """Add a formatted list."""
        if not items:
            return
        
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*self.config.colors.text_primary)
        text_width = self.w - 2 * self.config.margin - 10
        
        for i, item in enumerate(items, 1):
            if not item:
                continue
            
            self.set_x(self.config.margin + 5)
            
            if ordered:
                prefix = f"{i}."
            else:
                prefix = "-"  # Simple dash (ASCII safe)
            
            clean_item = self._clean_text(str(item))
            self.multi_cell(text_width, 6, f"  {prefix}  {clean_item}", align="L")
    
    def add_table(self, headers: list, rows: list):
        """Add a professional table."""
        if not rows:
            return
        
        self.ln(5)
        
        # Calculate column widths
        num_cols = len(headers)
        available_width = self.w - 2 * self.config.margin
        col_width = available_width / num_cols
        
        # Header row
        self.set_fill_color(*self.config.colors.primary)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 9)
        self.set_x(self.config.margin)
        
        for header in headers:
            self.cell(col_width, 8, str(header)[:15], border=1, fill=True, align="C")
        self.ln()
        
        # Data rows
        self.set_text_color(*self.config.colors.text_primary)
        self.set_font("Helvetica", "", 9)
        
        for i, row in enumerate(rows):
            # Alternate row colors
            if i % 2 == 0:
                self.set_fill_color(*self.config.colors.background)
            else:
                self.set_fill_color(255, 255, 255)
            
            self.set_x(self.config.margin)
            for cell in row:
                self.cell(col_width, 7, str(cell)[:15], border=1, fill=True, align="C")
            self.ln()
        
        self.ln(5)
    
    def add_info_box(self, title: str, content: str, box_type: str = "info"):
        """Add an information callout box."""
        if not content:
            return
        
        colors = {
            "info": self.config.colors.accent,
            "success": self.config.colors.success,
            "warning": self.config.colors.warning,
            "danger": self.config.colors.danger,
        }
        color = colors.get(box_type, self.config.colors.accent)
        
        self.ln(3)
        start_y = self.get_y()
        box_width = self.w - 2 * self.config.margin
        
        # Left accent bar
        self.set_fill_color(*color)
        self.rect(self.config.margin, start_y, 4, 25, "F")
        
        # Box background
        self.set_fill_color(color[0] + 60 if color[0] < 195 else 255,
                           color[1] + 60 if color[1] < 195 else 255,
                           color[2] + 60 if color[2] < 195 else 255)
        self.rect(self.config.margin + 4, start_y, box_width - 4, 25, "F")
        
        # Title
        self.set_xy(self.config.margin + 10, start_y + 3)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*color)
        self.cell(box_width - 15, 6, title, align="L")
        
        # Content
        self.set_xy(self.config.margin + 10, start_y + 11)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*self.config.colors.text_primary)
        clean_content = self._clean_text(content)[:120]
        self.multi_cell(box_width - 15, 5, clean_content, align="L")
        
        self.set_y(start_y + 30)
    
    def add_swot_table(self, swot: dict):
        """Add a professional SWOT analysis table."""
        if not swot:
            return
        
        self.ln(5)
        
        cell_width = (self.w - 2 * self.config.margin) / 2
        cell_height = 90  # Increased height for more content
        
        quadrants = [
            ("STRENGTHS", self.config.colors.success, swot.get("strengths", [])),
            ("WEAKNESSES", self.config.colors.danger, swot.get("weaknesses", [])),
            ("OPPORTUNITIES", self.config.colors.accent, swot.get("opportunities", [])),
            ("THREATS", self.config.colors.warning, swot.get("threats", [])),
        ]
        
        start_y = self.get_y()
        
        for i, (label, color, items) in enumerate(quadrants):
            row = i // 2
            col = i % 2
            
            x = self.config.margin + (col * cell_width)
            y = start_y + (row * cell_height)
            
            # Header
            self.set_xy(x, y)
            self.set_fill_color(*color)
            self.set_text_color(255, 255, 255)
            self.set_font("Helvetica", "B", 9)
            self.cell(cell_width, 7, label, border=1, fill=True, align="C")
            
            # Content
            self.set_xy(x, y + 7)
            self.set_fill_color(255, 255, 255)
            self.set_text_color(*self.config.colors.text_primary)
            self.set_font("Helvetica", "", 7)  # Smaller font to fit more
            
            content_lines = []
            for item in items[:6]:  # Increased to 6 items
                if isinstance(item, dict):
                    text = item.get("statement", item.get("text", ""))
                else:
                    text = str(item)
                if text:
                    content_lines.append(f"- {text}")  # Removed truncation
            
            content = "\n".join(content_lines) if content_lines else "N/A"
            content = self._clean_text(content)
            
            self.rect(x, y + 7, cell_width, cell_height - 7)
            
            # Save X/Y to use multi_cell properly inside the box
            self.set_xy(x + 1, y + 8)
            self.multi_cell(cell_width - 2, 4, content, align="L")
        
        self.set_y(start_y + (2 * cell_height) + 5)
    
    def _clean_text(self, text: str) -> str:
        """
        Clean text for PDF output - removes all markdown formatting.
        """
        import re
        
        if not text:
            return ""
        
        text = str(text)
        
        # Remove markdown headers (# ## ### etc.)
        text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
        
        # Remove bold (**text** or __text__)
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'__(.+?)__', r'\1', text)
        
        # Remove italic (*text* or _text_)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        text = re.sub(r'(?<!\w)_([^_]+)_(?!\w)', r'\1', text)
        
        # Remove inline code (`code`)
        text = re.sub(r'`([^`]+)`', r'\1', text)
        
        # Remove markdown links [text](url) -> text
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        
        # Remove bullet points at start of lines
        text = re.sub(r'^[\*\-\+]\s+', '', text, flags=re.MULTILINE)
        
        # Remove numbered lists at start of lines
        text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)
        
        # Remove extra whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        # Handle encoding for PDF
        return text.encode('latin-1', errors='replace').decode('latin-1')


def generate_professional_pdf(
    mrd_data: dict,
    output_path: str,
    config: Optional[PDFConfig] = None
) -> str:
    """
    Generate a professional PDF report with optimized layout.
    """
    if config is None:
        config = PDFConfig()
    
    pdf = FormalMRDReport(config)
    
    # Cover page
    pdf.add_cover_page(mrd_data)
    
    # Start content pages
    pdf.add_page()
    
    # Section 1: Executive Summary
    pdf.add_section("Executive Summary")
    
    strategic = mrd_data.get("strategic_analysis", {})
    summary = strategic.get("executive_summary", "Executive summary pending analysis completion.")
    pdf.add_paragraph(summary)
    
    # Market Size (inline, no new page)
    market = strategic.get("market_size", {})
    if market:
        pdf.add_subsection("Market Overview")
        if market.get("tam"):
            pdf.add_field("Total Addressable Market (TAM)", f"${market['tam']:,.0f} Million")
        if market.get("sam"):
            pdf.add_field("Serviceable Addressable Market (SAM)", f"${market['sam']:,.0f} Million")
        if market.get("cagr"):
            pdf.add_field("Compound Annual Growth Rate", f"{market['cagr']:.1f}%")
        if market.get("year"):
            pdf.add_field("Projection Year", str(market['year']))
    
    # Target Audience
    target = strategic.get("target_audience", {})
    if target:
        pdf.add_subsection("Target Audience")
        if isinstance(target, dict):
            if target.get("demographic"):
                pdf.add_field("Demographics", target["demographic"])
            if target.get("behaviors"):
                pdf.add_field("Key Behaviors", ", ".join(target["behaviors"][:4]))
            if target.get("channels"):
                pdf.add_field("Marketing Channels", ", ".join(target["channels"][:4]))
            if target.get("pain_points"):
                pdf.add_field("Pain Points", ", ".join(target["pain_points"][:4]))
            if target.get("influencer_strategy"):
                pdf.add_info_box("Influencer Strategy", target["influencer_strategy"], "info")
        else:
            pdf.add_paragraph(str(target))
    
    # Key Trends
    if strategic.get("key_trends"):
        pdf.add_subsection("Key Market Trends")
        pdf.add_list(strategic["key_trends"][:6])  # Show more trends
    
    # Market Dynamics
    if strategic.get("market_dynamics"):
        pdf.add_subsection("Market Dynamics")
        pdf.add_paragraph(strategic["market_dynamics"])
    
    # Section 2: Competitor Analysis (only new page if needed)
    competitors = mrd_data.get("competitors", [])
    if competitors:
        # Check if we need a new page
        if pdf.get_y() > 200:
            pdf.add_page()
        
        pdf.add_section("Competitor Analysis")
        
        # Comparison table with more metrics
        headers = ["Metric"] + [c.get("name", "Unknown")[:12] for c in competitors[:2]]
        rows = [
            ["App Rating"] + [str(c.get("app_metrics", {}).get("app_store_rating", "N/A"))[:6] for c in competitors[:2]],
            ["Position"] + [str(c.get("position", "N/A"))[:12] for c in competitors[:2]],
            ["Revenue"] + [f"${c.get('financials', {}).get('revenue_annual', 0) or 0:,.0f}"[:12] for c in competitors[:2]],
            ["Downloads"] + [str(c.get("app_metrics", {}).get("downloads_estimate", "N/A"))[:12] for c in competitors[:2]],
        ]
        pdf.add_table(headers, rows)
        
        # Individual profiles with more detail
        for comp in competitors:
            pdf.add_subsection(comp.get("name", "Unknown Competitor"))
            pdf.add_paragraph(comp.get("description", ""))
            
            # Target audience
            if comp.get("target_audience"):
                pdf.add_field("Target Audience", comp["target_audience"])
            
            # App metrics
            app_metrics = comp.get("app_metrics", {})
            if app_metrics.get("monthly_active_users"):
                pdf.add_field("Monthly Active Users", f"{app_metrics['monthly_active_users']:,.0f}")
            
            # Financials
            financials = comp.get("financials", {})
            if financials.get("funding_total"):
                pdf.add_field("Total Funding", f"${financials['funding_total']:,.0f}")
            if financials.get("revenue_growth_yoy"):
                pdf.add_field("YoY Revenue Growth", f"{financials['revenue_growth_yoy']:.1f}%")
            
            strengths = comp.get("key_strengths", [])
            if strengths:
                pdf.add_field("Key Strengths", ", ".join(str(s) for s in strengths[:4]))
            
            weaknesses = comp.get("key_weaknesses", [])
            if weaknesses:
                pdf.add_field("Key Weaknesses", ", ".join(str(w) for w in weaknesses[:4]))
            
            games = comp.get("games_offered", [])
            if games:
                pdf.add_field("Games Offered", ", ".join(str(g) for g in games[:5]))
            
            # Sample Reviews
            app_metrics = comp.get("app_metrics", {})
            sample_reviews = app_metrics.get("sample_reviews", []) if app_metrics else []
            if sample_reviews:
                pdf.ln(3)
                pdf.set_font("Helvetica", "B", 9)
                pdf.set_text_color(*pdf.config.colors.secondary)
                pdf.cell(0, 6, "Sample User Reviews:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.set_font("Helvetica", "I", 8)
                pdf.set_text_color(*pdf.config.colors.text_primary)
                
                for review in sample_reviews[:2]:  # Show up to 2 reviews
                    rating = review.get("rating", 0)
                    stars = "*" * rating
                    content = review.get("content", "")[:150]  # Truncate to 150 chars
                    source = review.get("source", "app_store").replace("_", " ").title()
                    
                    review_text = f'[{stars}] "{content}..." - {source}'
                    pdf.set_x(pdf.config.margin + 5)
                    text_width = pdf.w - 2 * pdf.config.margin - 10
                    pdf.multi_cell(text_width, 4, pdf._clean_text(review_text), align="L")
                    pdf.ln(2)
    
    # Section 3: SWOT Analysis
    swot = mrd_data.get("swot", {})
    if swot:
        if pdf.get_y() > 180:
            pdf.add_page()
        pdf.add_section("SWOT Analysis")
        pdf.add_swot_table(swot)
    
    # Section 4: Feature Recommendations
    features = mrd_data.get("feature_recommendations", [])
    if features:
        if pdf.get_y() > 180:
            pdf.add_page()
        pdf.add_section("Feature Recommendations")
        
        for feat in features:
            priority = str(feat.get("priority", "medium")).upper()
            name = feat.get("name", "Feature")
            
            box_type = "danger" if priority in ["HIGH", "MUST_HAVE"] else ("warning" if priority in ["MEDIUM", "SHOULD_HAVE"] else "info")
            pdf.add_info_box(f"{priority}: {name}", feat.get("description", ""), box_type)
            
            if feat.get("rationale"):
                pdf.add_field("Rationale", feat["rationale"])
            if feat.get("effort_estimate"):
                pdf.add_field("Effort Estimate", feat["effort_estimate"])
            if feat.get("competitor_reference"):
                pdf.add_field("Competitor Reference", feat["competitor_reference"])
    
    # Section 5: Regulatory Assessment
    regulatory = mrd_data.get("regulatory", {})
    if regulatory:
        if pdf.get_y() > 180:
            pdf.add_page()
        pdf.add_section("Regulatory Assessment")
        
        risk_level = regulatory.get("overall_risk_level", "unknown").upper()
        pdf.add_field("Overall Risk Level", risk_level)
        
        if regulatory.get("recommended_launch_markets"):
            pdf.add_field("Recommended Launch Markets", ", ".join(regulatory["recommended_launch_markets"]))
        
        if regulatory.get("markets_to_avoid"):
            pdf.add_field("Markets to Avoid", ", ".join(regulatory["markets_to_avoid"]))
        
        if regulatory.get("compliance_requirements"):
            pdf.add_subsection("Compliance Requirements")
            pdf.add_list(regulatory["compliance_requirements"][:5])
        
        for jur in regulatory.get("jurisdictions", []):
            pdf.add_subsection(jur.get("jurisdiction", "Unknown").upper())
            
            status = jur.get("status", "Unknown")
            if isinstance(status, dict):
                status = status.get("value", str(status))
            pdf.add_field("Status", str(status))
            
            if jur.get("licensing_authority"):
                pdf.add_field("Licensing Authority", jur["licensing_authority"])
            if jur.get("key_regulations"):
                pdf.add_field("Key Regulations", ", ".join(jur["key_regulations"][:3]))
            if jur.get("summary"):
                pdf.add_paragraph(jur["summary"])
            if jur.get("notes"):
                pdf.add_field("Notes", jur["notes"])
    
    # Gap Analysis (if available)
    gap_analysis = mrd_data.get("gap_analysis", [])
    if gap_analysis:
        if pdf.get_y() > 200:
            pdf.add_page()
        pdf.add_section("Gap Analysis")
        pdf.add_paragraph("Opportunities identified from competitive analysis:")
        pdf.add_list(gap_analysis[:8])
    
    # Section 7: References (Task 4 requirement)
    references = mrd_data.get("references", [])
    if references:
        if pdf.get_y() > 200:
            pdf.add_page()
        pdf.add_section("References")
        
        # Format references as numbered list with simplified text
        formatted_refs = []
        for ref in references:
            # Truncate very long URLs for PDF cleanliness
            display_text = ref
            if len(ref) > 80:
                display_text = ref[:77] + "..."
            formatted_refs.append(display_text)
            
        pdf.add_list(formatted_refs, ordered=True)
    
    # Save
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    pdf.output(output_path)
    
    logger.info(f"Professional PDF generated: {output_path}")
    return output_path
