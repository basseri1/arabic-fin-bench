"""Render filing pages to PNG for visual transcription (scratch output, never part of the dataset).

usage: python render.py FILING_ID --sheet 1-20 --out DIR          contact sheet of page thumbnails, to find the statements
       python render.py FILING_ID --pages 8,9 --parts 2 --out DIR  statement pages, margins trimmed, split top/bottom
"""
import argparse
import re
import sys
from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gtlib  # noqa: E402


def pdf(fid):
    return fitz.open(gtlib.PAPER / "filings" / f"{fid}.pdf")


def ink_box(img, pad=12):
    """Bounding box of non-white content (ignores faint scan noise)."""
    g = ImageOps.invert(img.convert("L")).point(lambda v: 255 if v > 40 else 0)
    box = g.getbbox()
    if not box:
        return (0, 0) + img.size
    x0, y0, x1, y1 = box
    return max(0, x0 - pad), max(0, y0 - pad), min(img.width, x1 + pad), min(img.height, y1 + pad)


def page_image(doc, pno, dpi):
    pix = doc[pno - 1].get_pixmap(dpi=dpi)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def table_bottom(page):
    """y (points) just below the last text line holding a figure (3+ digits); None for pages without text."""
    h = page.rect.height
    ys = [w[3] for w in page.get_text("words")
          if sum(ch.isdigit() for ch in w[4]) >= 3 and w[3] < 0.93 * h                  # skip page footers
          and not re.fullmatch(r"(19|20)\d\d", w[4].translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")))]
    return max(ys) + 22 if ys else None


def render(fid, pages, out, dpi=200, parts=1, overlap=0.06):
    doc, files = pdf(fid), []
    out.mkdir(parents=True, exist_ok=True)
    for p in pages:
        img = page_image(doc, p, dpi)
        bottom = table_bottom(doc[p - 1])
        if bottom:
            img = img.crop((0, 0, img.width, min(img.height, int(bottom * dpi / 72))))
        img = img.crop(ink_box(img))
        h = img.height
        n = parts or max(1, round(img.width * h / 1.4e6))                        # 0 = choose by size
        for k in range(n):
            a = max(0, int(h * (k / n - (overlap if k else 0))))
            b = min(h, int(h * ((k + 1) / n + (overlap if k < n - 1 else 0))))
            f = out / (f"{fid}_p{p:03d}" + (f"_{k + 1}of{n}" if n > 1 else "") + ".png")
            img.crop((0, a, img.width, b)).save(f)
            files.append(f)
    return files


def grid(fid, page, out, cols, rows, dpi=300, overlap=0.04):
    """Split one dense page into cols x rows tiles (right-to-left, top-to-bottom), for wide equity statements."""
    doc = pdf(fid)
    img = page_image(doc, page, dpi)
    bottom = table_bottom(doc[page - 1])
    if bottom:
        img = img.crop((0, 0, img.width, min(img.height, int(bottom * dpi / 72))))
    img = img.crop(ink_box(img))
    w, h = img.size
    out.mkdir(parents=True, exist_ok=True)
    files = []
    for r in range(rows):
        for c in range(cols):
            x1 = int(w * (1 - c / cols + (overlap if c else 0)))
            x0 = int(w * (1 - (c + 1) / cols - (overlap if c < cols - 1 else 0)))
            y0 = int(h * (r / rows - (overlap if r else 0)))
            y1 = int(h * ((r + 1) / rows + (overlap if r < rows - 1 else 0)))
            f = out / f"{fid}_p{page:03d}_r{r + 1}c{c + 1}.png"
            img.crop((max(0, x0), max(0, y0), min(w, x1), min(h, y1))).save(f)
            files.append(f)
    return files


def title_strips(fid, first, last, out, frac=0.2, width=900):
    """Top part of each page stacked vertically (page titles), to locate the statements in image-only filings."""
    doc = pdf(fid)
    last = min(last, len(doc))
    strips = []
    for p in range(first, last + 1):
        im = page_image(doc, p, 110)
        im = im.crop(ink_box(im))
        im = im.crop((0, 0, im.width, int(im.height * frac)))
        im = im.resize((width, max(1, int(im.height * width / im.width))))
        strips.append((p, im))
    h = sum(im.height + 34 for _, im in strips)
    sheet = Image.new("RGB", (width, h), "white")
    d = ImageDraw.Draw(sheet)
    y = 0
    for p, im in strips:
        d.rectangle((0, y, width, y + 30), fill=(230, 230, 250))
        d.text((8, y + 8), f"page {p}", fill=(200, 0, 0))
        sheet.paste(im, (0, y + 32))
        y += im.height + 34
    out.mkdir(parents=True, exist_ok=True)
    f = out / f"{fid}_titles_{first}-{last}.png"
    sheet.save(f)
    return f


def contact_sheet(fid, first, last, out, cols=5, thumb=360):
    doc = pdf(fid)
    last = min(last, len(doc))
    ims = []
    for p in range(first, last + 1):
        im = page_image(doc, p, 40)
        im.thumbnail((thumb, thumb * 1.5))
        ims.append((p, im))
    rows = (len(ims) + cols - 1) // cols
    cw, ch = thumb + 10, int(thumb * 1.5) + 30
    sheet = Image.new("RGB", (cols * cw, rows * ch), "white")
    d = ImageDraw.Draw(sheet)
    for i, (p, im) in enumerate(ims):
        x, y = (i % cols) * cw + 5, (i // cols) * ch + 25
        sheet.paste(im, (x, y))
        d.text((x, y - 20), f"p{p}", fill=(200, 0, 0))
    out.mkdir(parents=True, exist_ok=True)
    f = out / f"{fid}_sheet_{first}-{last}.png"
    sheet.save(f)
    return f


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("filing_id")
    ap.add_argument("--pages", default="")
    ap.add_argument("--sheet", default="")
    ap.add_argument("--titles", default="", help="a-b: stacked page tops, to find statement pages")
    ap.add_argument("--parts", type=int, default=0, help="0 = by height")
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--grid", default="", help="CxR tiles for one dense page, e.g. 3x2 (tiles run right to left)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    if a.titles:
        f, l = map(int, a.titles.split("-"))
        print(title_strips(a.filing_id, f, l, out))
    if a.sheet:
        f, l = map(int, a.sheet.split("-"))
        print(contact_sheet(a.filing_id, f, l, out))
    if a.grid:
        c, r = map(int, a.grid.lower().split("x"))
        for f in grid(a.filing_id, int(a.pages), out, c, r, max(a.dpi, 300)):
            print(f)
        sys.exit(0)
    if a.pages:
        pages = []
        for part in a.pages.split(","):
            if "-" in part:
                x, y = map(int, part.split("-"))
                pages += list(range(x, y + 1))
            else:
                pages.append(int(part))
        for f in render(a.filing_id, pages, out, a.dpi, a.parts):
            print(f)
