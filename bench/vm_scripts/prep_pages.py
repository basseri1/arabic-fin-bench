"""Render the ground-truth pages (the 5 main statements per company) to PNG.

GT page mapping (PDF 1-based page indices, verified visually):
  aramco: PDF p12-16  -> income, comprehensive income, financial position, equity, cash flows
  maaden: PDF p11-16  -> printed page numbers 10-15; p15+p16 = cash flow (2 pages, incl. non-cash annex)
"""
import fitz
from pathlib import Path

BASE = Path(__file__).resolve().parent
PDFS = {
    "aramco": ("/path/to/DocProcess/Example_files/ارامكو.pdf", range(12, 17)),
    "maaden": ("/path/to/DocProcess/Example_files/معادن.pdf", range(11, 17)),
}
OUT = BASE / "pages"
OUT.mkdir(exist_ok=True)
DPI = 200

for name, (path, pages) in PDFS.items():
    doc = fitz.open(path)
    for pno in pages:
        page = doc[pno - 1]
        pix = page.get_pixmap(dpi=DPI, alpha=False)
        out = OUT / f"{name}_p{pno:02d}.png"
        pix.save(out)
        print(f"{out.name:>16}  {pix.width}x{pix.height}  textlayer={len(page.get_text().strip())>50}")
print("done ->", OUT)
