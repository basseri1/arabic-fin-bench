"""Render the statement pages of every filing for the model runs (same recipes as the pilot benchmark).

Outputs <out>/<prep>/<filing_id>_pNN.png for prep in:
  plain        200 dpi, grayscale                       (dots.mocr out of the box)
  clahe        200 dpi, grayscale + CLAHE 2.0/8         (adopted dots.mocr pipeline)
  chandra_cap  grayscale at Chandra's pixel cap (3072x2048 on a 28-px grid, i.e. ~6.3 MP)
Pages printed sideways are turned upright first (ROTATE), as a pipeline's orientation step would; this is applied
identically for every model. Also writes <out>/manifest.json: filing -> pages.
usage: python render_pages.py --out DIR
"""
import argparse, json, sys
from pathlib import Path
import cv2, fitz, numpy as np
from PIL import Image
PAPER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PAPER / "tools"))
import gtlib  # noqa: E402

ROTATE = {("buruj_FY2024", 11), ("al_khodari_FY2018", 10), ("bishah_FY2016", 7), ("snb_FY2024", 15),
          ("bank_aljazira_FY2024", 10)}          # content printed sideways on an upright page -> rotate 90° clockwise


def statement_pages():
    out = {}
    for d in ("gt", "drafts"):
        for f in sorted((PAPER / d).glob("*.json")):
            gt = gtlib.load(f)
            out.setdefault(gt["filing_id"], sorted({p for st in gt["statements"] for p in st["pages"]}))
    return out


def render(doc, pno, dpi):
    pix = doc[pno - 1].get_pixmap(dpi=dpi)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def scale_to_fit(im, maxp=3072 * 2048, minp=1792 * 28, g=28):          # chandra/model/util.py, as in bench.py
    w, h = im.size; ar = w / h; cur = w * h
    s = (maxp / cur) ** 0.5 if cur > maxp else (minp / cur) ** 0.5 if cur < minp else 1.0
    wb, hb = max(1, round(w * s / g)), max(1, round(h * s / g))
    while wb * hb * g * g > maxp and not (wb == 1 and hb == 1):
        if wb == 1: hb -= 1; continue
        if hb == 1: wb -= 1; continue
        if abs((wb - 1) / hb - ar) < abs(wb / (hb - 1) - ar): wb -= 1
        else: hb -= 1
    return im.resize((wb * g, hb * g), Image.Resampling.LANCZOS)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); a = ap.parse_args()
    out = Path(a.out)
    for prep in ("plain", "clahe", "chandra_cap"):
        (out / prep).mkdir(parents=True, exist_ok=True)
    pages = statement_pages()
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    n = 0
    for fid, pnos in pages.items():
        doc = fitz.open(PAPER / "filings" / f"{fid}.pdf")
        for p in pnos:
            name = f"{fid}_p{p:02d}.png"
            if all((out / prep / name).exists() for prep in ("plain", "clahe", "chandra_cap")):
                n += 1; continue
            im200, im300 = render(doc, p, 200), render(doc, p, 300)
            if (fid, p) in ROTATE:
                im200, im300 = im200.rotate(-90, expand=True), im300.rotate(-90, expand=True)
            g = np.array(im200.convert("L"))
            cv2.imwrite(str(out / "plain" / name), g)
            cv2.imwrite(str(out / "clahe" / name), clahe.apply(g))
            scale_to_fit(im300.convert("L")).save(out / "chandra_cap" / name)
            n += 1
    (out / "manifest.json").write_text(json.dumps(pages, indent=1))
    print(f"{len(pages)} filings, {n} pages rendered into {out}")
