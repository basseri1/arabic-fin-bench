import fitz
from pathlib import Path

PDFS = {
    "aramco": ("/path/to/DocProcess/Example_files/ارامكو.pdf", [2, 13, 20]),
    "maaden": ("/path/to/DocProcess/Example_files/معادن.pdf", [5, 6, 7]),
    "hafar": ("/path/to/financial statements/الحفر.pdf", [9, 10, 11]),
}
OUT = Path("/path/to/DocProcess/ocr_benchmark/images")
OUT.mkdir(parents=True, exist_ok=True)

for name, (path, pages) in PDFS.items():
    doc = fitz.open(path)
    for pno in pages:
        page = doc[pno - 1]
        pix = page.get_pixmap(dpi=200)
        out = OUT / f"{name}_p{pno:03d}.png"
        pix.save(out)
        print(f"saved {out.name} ({pix.width}x{pix.height})")
print("done")
