#!/usr/bin/env python
"""Line-level OCR pipeline for single-line recognizers (mohajesmaeili/Qwen3-VL-2B-Persian-Arabic-Ocr-v1.0,
which is trained only on cropped text lines). Text-line boxes come from the classical PaddleOCR detector
(results/paddle_ar/<page>.json); each crop is recognized with the VLM; lines are regrouped into table rows
by vertical position (same rule as the classical baseline). Usage: venv_mlx/bin/python run_linelevel.py"""
import argparse, os, os, json, os, sys, time
from pathlib import Path
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_paddle_classic import rows_from_lines
BASE = Path(__file__).resolve().parent
MODEL = str(BASE / "models" / "PersAr2B-mlx")
PROMPT = "Read the text in this image."          # no prompt documented on the card
SCR = BASE / "_tmp" / "crops"; SCR.mkdir(parents=True, exist_ok=True)

def make_recognizer():
    from mlx_vlm import load, generate
    from mlx_vlm.prompt_utils import apply_chat_template
    from mlx_vlm.utils import load_config
    model, processor = load(MODEL); config = load_config(MODEL)
    def rec(img_path):
        prompt = apply_chat_template(processor, config, PROMPT, num_images=1)
        out = generate(model, processor, prompt, image=[str(img_path)], max_tokens=128, temperature=0.0, verbose=False)
        return (getattr(out, "text", out) or "").strip()
    return rec

def boxes_for(page_stem):
    f = Path(os.environ.get("BOXES_DIR", BASE / "results" / "paddle_ar")) / f"{page_stem}.json"
    if not f.exists():
        return None
    return [tuple(d["bbox"]) for d in json.loads(f.read_text())]

def make_fn():
    """whole image -> text via detect(classical)+recognize(VLM); used by digit_probe.py"""
    from run_paddle_classic import make_fn as paddle_fn   # noqa: F401  (ensures paddle importable)
    from paddleocr import PaddleOCR
    det = PaddleOCR(lang="ar", use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False)
    rec = make_recognizer()
    def fn(img):
        im = Image.open(img).convert("RGB"); items = []
        for r in det.predict(str(img)):
            d = r.json["res"] if hasattr(r, "json") else r
            for poly in (d.get("rec_polys") or d.get("dt_polys") or []):
                xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
                b = [min(xs), min(ys), max(xs), max(ys)]
                crop = im.crop((max(0, b[0]-4), max(0, b[1]-4), min(im.width, b[2]+4), min(im.height, b[3]+4)))
                cp = SCR / "probe_crop.png"; crop.save(cp); items.append((b, rec(cp)))
        return "\n".join(rows_from_lines(items))
    return fn

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--only", default=""); ap.add_argument("--out", default=str(BASE / "results" / "persar2b"))
    a = ap.parse_args()
    rec = make_recognizer()
    out_dir = Path(a.out); out_dir.mkdir(parents=True, exist_ok=True)
    pages = sorted(Path(os.environ.get("PAGES_DIR", BASE / "pages")).glob("*.png"))
    if a.only:
        keep = set(a.only.split(",")); pages = [p for p in pages if p.stem in keep]
    (out_dir / "_meta.json").write_text(json.dumps({"model": "persar2b", "backend": "mlx bf16 (line recognizer) + PaddleOCR det boxes", "prompt": PROMPT,
                                                     "postproc": "rows by y-center clustering, RTL", "date": time.strftime("%F")}, indent=1))
    for p in pages:
        out = out_dir / f"{p.stem}.md"
        if out.exists() and out.stat().st_size > 0:
            print(f"[persar2b] {p.name}: cached, skipping", flush=True); continue
        t0 = time.time(); err = None; text = ""; n = 0
        try:
            boxes = boxes_for(p.stem)
            if boxes is None:
                raise RuntimeError("no paddle_ar boxes for this page (run run_paddle_classic.py first)")
            im = Image.open(p).convert("RGB"); items = []
            for i, b in enumerate(boxes):
                crop = im.crop((max(0, b[0]-4), max(0, b[1]-4), min(im.width, b[2]+4), min(im.height, b[3]+4)))
                cp = SCR / f"{p.stem}_{i:03d}.png"; crop.save(cp)
                items.append((list(b), rec(cp)))
            n = len(items); text = "\n".join(rows_from_lines(items))
            (out_dir / f"{p.stem}.json").write_text(json.dumps([{"bbox": b, "text": t} for b, t in items], ensure_ascii=False))
        except Exception:
            import traceback; err = traceback.format_exc()
            (out_dir / "_errors.log").open("a").write(f"\n===== {p.name}\n{err}\n")
        secs = time.time() - t0
        out.write_text(text, encoding="utf-8")
        with (out_dir / "_timing.jsonl").open("a") as f:
            f.write(json.dumps({"page": p.stem, "secs": round(secs, 1), "chars": len(text), "lines": n, "error": bool(err), "backend": "mlx-linelevel"}) + "\n")
        print(f"[persar2b] {p.name}: {secs:.1f}s, {n} lines, {len(text)} chars{'  ERROR' if err else ''}", flush=True)
    print("[persar2b] DONE", flush=True)

if __name__ == "__main__":
    main()
