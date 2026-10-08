"""Layout detection for table-region cropping. Usage: <python> layout_detect.py surya|pp <pages_dir> <out_dir>
Writes <out_dir>/<page>.json = [{"label": table|text|header|footer|picture|other, "raw": ..., "bbox": [x0,y0,x1,y1]}]"""
import sys, json
from pathlib import Path
from PIL import Image
det, pages_dir, out_dir = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]); out_dir.mkdir(parents=True, exist_ok=True)
pages = sorted(pages_dir.glob("*.png"))
def norm(lbl):
    l = lbl.lower()
    if "table" in l: return "table"
    if "header" in l and "section" not in l and "paragraph" not in l: return "header"
    if "footer" in l or l in ("number", "page_number", "pagefooter"): return "footer"
    if any(k in l for k in ("picture", "figure", "image", "seal", "chart", "signature")): return "picture"
    if any(k in l for k in ("text", "title", "section", "caption", "list", "footnote", "formula", "abstract", "content", "reference")): return "text"
    return "other"
if det == "surya":
    from surya.fast_layout import FastLayoutPredictor
    pred = FastLayoutPredictor()
    for p in pages:
        res = pred([Image.open(p).convert("RGB")])[0]
        blocks = [{"label": norm(b.label), "raw": b.label, "bbox": [float(v) for v in b.bbox]} for b in res.bboxes]
        (out_dir / f"{p.stem}.json").write_text(json.dumps(blocks)); print(p.stem, [(b["raw"], [int(v) for v in b["bbox"]]) for b in blocks][:8], flush=True)
elif det == "pp":
    from paddleocr import LayoutDetection
    model = LayoutDetection(model_name="PP-DocLayoutV2")
    for p in pages:
        blocks = []
        for r in model.predict(str(p), batch_size=1):
            d = r.json; d = d.get("res", d)
            for b in d["boxes"]:
                blocks.append({"label": norm(b["label"]), "raw": b["label"], "bbox": [float(v) for v in b["coordinate"]], "score": float(b.get("score", 0))})
        (out_dir / f"{p.stem}.json").write_text(json.dumps(blocks)); print(p.stem, [(b["raw"], [int(v) for v in b["bbox"]]) for b in blocks][:8], flush=True)
print("LAYOUT DONE", det)
