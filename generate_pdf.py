"""Generate PDF from existing Markdown using fpdf2."""
from fpdf import FPDF
from fpdf.enums import XPos, YPos
import re

md_path = "outputs/mrd_20251222_221100.md"
pdf_path = "outputs/mrd_20251222_221100.pdf"

# Read markdown
with open(md_path, "r", encoding="utf-8") as f:
    md_content = f.read()

print(f"Processing {len(md_content)} characters...")

# Create PDF
class PDF(FPDF):
    def header(self):
        # Optional: Add logo or header text here
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

pdf = PDF()
pdf.add_page()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.set_margin(15)

# Process markdown line by line
lines = md_content.split('\n')

for line in lines:
    line = line.strip()
    if not line:
        pdf.ln(5)
        continue
    
    # H1
    if line.startswith('# '):
        pdf.set_font('Helvetica', 'B', 20)
        pdf.set_text_color(44, 62, 80)
        # new_x=XPos.LMARGIN, new_y=YPos.NEXT replaces ln=True
        pdf.cell(0, 10, line[2:], new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        pdf.ln(5)
    # H2
    elif line.startswith('## '):
        pdf.set_font('Helvetica', 'B', 16)
        pdf.set_text_color(52, 73, 94)
        pdf.cell(0, 10, line[3:], new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        pdf.ln(3)
    # H3
    elif line.startswith('### '):
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_text_color(127, 140, 141)
        pdf.cell(0, 8, line[4:], new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
    # Bold text (Key: Value)
    elif line.startswith('**') and ':**' in line:
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(0, 0, 0)
        clean = re.sub(r'\*\*', '', line)
        pdf.multi_cell(0, 6, clean, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
    # List item
    elif line.startswith('- '):
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(0, 0, 0)
        clean = re.sub(r'\*\*', '', line)
        
        # Manually save current X (margin)
        start_x = pdf.get_x()
        
        # Indent
        pdf.set_x(start_x + 5)
        pdf.multi_cell(0, 6, clean, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
    # Normal text
    else:
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(0, 6, line, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')

# Save
try:
    pdf.output(pdf_path)
    print(f"PDF created successfully: {pdf_path}")
except Exception as e:
    print(f"Error saving PDF: {e}")
