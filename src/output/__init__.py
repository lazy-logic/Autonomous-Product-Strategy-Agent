"""
============================================================
MRD Agent - Output Package
============================================================
Output generators for MRD reports.

Formats:
- PDF (professional styled)
- JSON (raw data)
- Markdown (human readable)
============================================================
"""

from src.output.pdf_generator import (
    generate_professional_pdf,
    PDFConfig,
    PDFColors,
    FormalMRDReport,
)

__all__ = [
    "generate_professional_pdf",
    "PDFConfig",
    "PDFColors",
    "FormalMRDReport",
]
