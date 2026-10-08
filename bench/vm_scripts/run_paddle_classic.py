#!/usr/bin/env python
"""Classical PaddleOCR Arabic pipeline (PP-OCRv5 text detection + Arabic recognition; CPU) - the non-VLM
baseline. docscanner-ocr ships ONNX exports of these same PaddleOCR det/rec models. Detected lines are
grouped into table rows by vertical position (one output line per row, right-to-left within a row).
Usage: python run_paddle_classic.py [--only ...]"""
import argparse, os, json, time, statistics
from pathlib import Path
BASE = Path(__file__).resolve().parent

def rows_from_lines(items):
    """items: [(bbox[x1,y1,x2,y2], text)] -> list of row strings (RTL order within a row)."""
    if not items: return []
    hs = [b[3] - b[1] for b, _ in items]; tol = 0.6 * statistics.median(hs)
    items = sorted(items, key=lambda it: (it[0][1] + it[0][3]) / 2)
    rows, cur, cy = [], [], None
    for b, t in items:
        c = (b[1] + b[3]) / 2
        if cy is None or abs(c - cy) <= tol:
            cur.append((b, t)); cy = c if cy is None else (cy + c) / 2
        else:
            rows.append(cur); cur = [(b, t)]; cy = c
    if cur: rows.append(cur)
    return [" | ".join(t for b, t in sorted(r, key=lambda it: -it[0][0])) for r in rows]

def make_fn():
    """page/image path -> row text (used by digit_probe.py)."""
    from paddleocr import PaddleOCR
    ocr = PaddleOCR(lang="ar", use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False)
    def fn(img):
        items = []
        for r in ocr.predict(str(img)):
            d = r.json["res"] if hasattr(r, "json") else r
            for poly, t in zip(d.get("rec_polys") or d.get("dt_polys") or [], d.get("rec_texts") or []):
                xs = [pt[0] for pt in poly]; ys = [pt[1] for pt in poly]
                items.append(([min(xs), min(ys), max(xs), max(ys)], t))
        return "\n".join(rows_from_lines(items))
    return fn


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--only", default=""); ap.add_argument("--out", default=str(BASE / "results" / "paddle_ar"))
    a = ap.parse_args()
    from paddleocr import PaddleOCR
    ocr = PaddleOCR(lang="ar", use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False)
    out_dir = Path(a.out); out_dir.mkdir(parents=True, exist_ok=True)
    pages = sorted(Path(os.environ.get("PAGES_DIR", BASE / "pages")).glob("*.png"))
    if a.only:
        keep = set(a.only.split(",")); pages = [p for p in pages if p.stem in keep]
    (out_dir / "_meta.json").write_text(json.dumps({"model": "paddle_ar", "backend": "paddleocr 3.x PaddleOCR(lang='ar') CPU: PP-OCRv5 det + arabic rec",
                                                     "postproc": "lines -> rows by y-center clustering (0.6 x median line height), RTL order", "date": time.strftime("%F")}, indent=1))
    for p in pages:
        out = out_dir / f"{p.stem}.md"
        if out.exists() and out.stat().st_size > 0:
            print(f"[paddle_ar] {p.name}: cached, skipping", flush=True); continue
        t0 = time.time(); err = None; text = ""; n = 0
        try:
            res = ocr.predict(str(p))
            items = []
            for r in res:
                d = r.json["res"] if hasattr(r, "json") else r
                polys = d.get("rec_polys") or d.get("dt_polys") or []
                texts = d.get("rec_texts") or []
                for poly, t in zip(polys, texts):
                    xs = [pt[0] for pt in poly]; ys = [pt[1] for pt in poly]
                    items.append(([min(xs), min(ys), max(xs), max(ys)], t))
            n = len(items)
            text = "\n".join(rows_from_lines(items))
            (out_dir / f"{p.stem}.json").write_text(json.dumps([{"bbox": b, "text": t} for b, t in items], ensure_ascii=False))
        except Exception:
            import traceback; err = traceback.format_exc()
            (out_dir / "_errors.log").open("a").write(f"\n===== {p.name}\n{err}\n")
        secs = time.time() - t0
        out.write_text(text, encoding="utf-8")
        with (out_dir / "_timing.jsonl").open("a") as f:
            f.write(json.dumps({"page": p.stem, "secs": round(secs, 1), "chars": len(text), "lines": n, "error": bool(err), "backend": "paddleocr-cpu"}) + "\n")
        print(f"[paddle_ar] {p.name}: {secs:.1f}s, {n} lines, {len(text)} chars{'  ERROR' if err else ''}", flush=True)
    print("[paddle_ar] DONE", flush=True)

if __name__ == "__main__":
    main()
