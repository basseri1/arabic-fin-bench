"""Experiment inputs: (1) Ma'aden portrait pages rendered at native scan resolution (283 dpi);
(2) the landscape equity statement (p14) split into two column-group crops, each carrying the label column."""
import fitz
from pathlib import Path
from PIL import Image
BASE = Path(__file__).resolve().parent
PDF = "/path/to/DocProcess/Example_files/معادن.pdf"
out_native = BASE / "pages_exp" / "native"; out_native.mkdir(parents=True, exist_ok=True)
out_split = BASE / "pages_exp" / "split"; out_split.mkdir(parents=True, exist_ok=True)
doc = fitz.open(PDF)
for pno in (11, 12, 13, 15, 16):
    pix = doc[pno - 1].get_pixmap(dpi=283, alpha=False); p = out_native / f"maaden_p{pno}.png"; pix.save(p); print(p.name, pix.width, pix.height)
# landscape equity page: the render at 200 dpi is native. Split into column groups with the label column on both.
im = Image.open(BASE / "pages" / "maaden_p14.png"); W, H = im.size
A = im.crop((int(W * 0.43), 0, W, H))                         # labels (right) + right-most ~4 numeric columns
left = im.crop((0, 0, int(W * 0.46), H)); labels = im.crop((int(W * 0.745), 0, W, H))
B = Image.new("RGB", (left.width + labels.width + 20, H), "white"); B.paste(left, (0, 0)); B.paste(labels, (left.width + 20, 0))
A.save(out_split / "maaden_p14_A.png"); B.save(out_split / "maaden_p14_B.png"); print("split A", A.size, "B", B.size)
