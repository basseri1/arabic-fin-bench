"""Page-preparation primitives shared by the ablation loops and the end-to-end pipeline."""
import cv2, numpy as np, json
from pathlib import Path
def gray(p): return cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
def clahe(g, clip=2.0, tile=8): return cv2.createCLAHE(clipLimit=clip, tileGridSize=(tile, tile)).apply(g)
def inkfree(p, red=True, blue=True):
    """Remove coloured ink (red annotations, blue signatures) by HSV mask + inpainting; black print is untouched."""
    bgr = cv2.imread(str(p)); hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV); m = np.zeros(hsv.shape[:2], np.uint8)
    if red: m |= cv2.inRange(hsv, (0, 70, 60), (12, 255, 255)) | cv2.inRange(hsv, (165, 70, 60), (180, 255, 255))
    if blue: m |= cv2.inRange(hsv, (95, 60, 40), (135, 255, 255))
    if not m.any(): return cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    return cv2.cvtColor(cv2.inpaint(bgr, cv2.dilate(m, np.ones((3, 3), np.uint8)), 3, cv2.INPAINT_TELEA), cv2.COLOR_BGR2GRAY)
def dots_blocks(md_path):
    raw = Path(md_path).read_text(errors="replace")
    try: bl = json.loads(raw[raw.index("["):raw.rindex("]") + 1])
    except Exception: return []
    out = []
    for b in bl:
        c = b.get("category", ""); l = c.lower()
        lab = ("table" if "table" in l else "header" if "page-header" in l else "footer" if "page-footer" in l else
               "picture" if "picture" in l else "text" if c in ("Text", "Section-header", "Caption", "List-item", "Footnote", "Title") else "other")
        if "bbox" in b: out.append({"label": lab, "raw": c, "bbox": b["bbox"]})
    return out
def crop_box(blocks, W, H, m=30):
    """Vertical crop: from the first table down to the last table/text block above the signature pictures."""
    tables = [b for b in blocks if b["label"] == "table"]
    if not tables: return None
    top = min(b["bbox"][1] for b in tables); cy = lambda b: (b["bbox"][1] + b["bbox"][3]) / 2
    pics = [b for b in blocks if b["label"] == "picture" and cy(b) > H * 0.5]
    cut = min(cy(b) for b in pics) if pics else H * 0.97
    cands = [b for b in blocks if b["label"] in ("table", "text") and cy(b) >= top and cy(b) < cut]
    bottom = max(b["bbox"][3] for b in cands)
    return (int(max(0, top - m)), int(min(H, bottom + m)))
def pad(g, px=60): return cv2.copyMakeBorder(g, px, px, px, px, cv2.BORDER_CONSTANT, value=255)
def det_blocks(det, page_stem):
    f = Path("layouts") / det / f"{page_stem}.json"
    return json.loads(f.read_text()) if f.exists() else []
def prepare(page_png, prep, layout_md=None):
    """prep tokens joined by '_': plain | gray | clahe | inkfree | redfree | pad | crop (dots layout .md) | croppp | cropsurya | cropfixed.
    e.g. 'clahe', 'inkfree_clahe', 'crop_inkfree_clahe', 'croppp_clahe', 'clahe_pad'."""
    toks = prep.split("_")
    if toks == ["plain"]: return gray(page_png)
    base = inkfree(page_png) if "inkfree" in toks else inkfree(page_png, blue=False) if "redfree" in toks else gray(page_png)
    H, W = base.shape; box = None
    if "crop" in toks: box = crop_box(dots_blocks(layout_md), W, H) if layout_md and Path(layout_md).exists() else None
    elif "croppp" in toks: box = crop_box(det_blocks("pp", Path(page_png).stem), W, H)
    elif "cropsurya" in toks: box = crop_box(det_blocks("surya", Path(page_png).stem), W, H)
    elif "cropfixed" in toks: box = (int(H * 0.11), int(H * 0.86))
    if box: base = base[box[0]:box[1], :]
    if "clahe" in toks: base = clahe(base)
    if "pad" in toks: base = pad(base)
    return base
