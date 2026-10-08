#!/usr/bin/env python
"""Surya OCR 2 (datalab-to/surya-ocr-2 via the surya package; llama.cpp backend on Apple Silicon).
Full-page OCR (one VLM call per page) -> blocks with HTML in reading order; we save the HTML blocks
joined by newlines (tables stay <table> HTML). Usage: venv_surya/bin/python run_surya.py [--only ...]"""
import argparse, os, json, os, sys, time
from pathlib import Path
from PIL import Image
BASE = Path(__file__).resolve().parent

def make_fn():
    """image path -> joined HTML blocks (used by digit_probe.py)"""
    from surya.inference import SuryaInferenceManager
    from surya.recognition import RecognitionPredictor
    rec = RecognitionPredictor(SuryaInferenceManager())
    def fn(img):
        res = rec([Image.open(img).convert("RGB")])[0]
        return "\n".join((getattr(b, "html", None) or getattr(b, "text", "") or "") for b in res.blocks)
    return fn


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--only", default=""); ap.add_argument("--out", default=str(BASE / "results" / "surya2"))
    a = ap.parse_args()
    from surya.inference import SuryaInferenceManager
    from surya.recognition import RecognitionPredictor
    manager = SuryaInferenceManager()
    rec = RecognitionPredictor(manager)
    out_dir = Path(a.out); out_dir.mkdir(parents=True, exist_ok=True)
    pages = sorted(Path(os.environ.get("PAGES_DIR", BASE / "pages")).glob("*.png"))
    if a.only:
        keep = set(a.only.split(",")); pages = [p for p in pages if p.stem in keep]
    (out_dir / "_meta.json").write_text(json.dumps({"model": "surya2", "backend": "surya-ocr package, SuryaInferenceManager (inference server set by the surya package environment; vLLM container on the VM)",
                                                     "mode": "full-page recognition -> blocks.html", "date": time.strftime("%F")}, indent=1))
    for p in pages:
        out = out_dir / f"{p.stem}.md"
        if out.exists() and out.stat().st_size > 0:
            print(f"[surya2] {p.name}: cached, skipping", flush=True); continue
        t0 = time.time(); err = None; text = ""
        try:
            res = rec([Image.open(p).convert("RGB")])[0]
            parts = []
            for b in res.blocks:
                h = getattr(b, "html", None) or getattr(b, "text", "") or ""
                parts.append(h)
            text = "\n".join(parts)
            (out_dir / f"{p.stem}.json").write_text(json.dumps([{"label": getattr(b, "label", None), "bbox": getattr(b, "bbox", None), "html": getattr(b, "html", None)} for b in res.blocks], ensure_ascii=False))
        except Exception as e:
            import traceback; err = traceback.format_exc()
            (out_dir / "_errors.log").open("a").write(f"\n===== {p.name}\n{err}\n")
        secs = time.time() - t0
        out.write_text(text, encoding="utf-8")
        with (out_dir / "_timing.jsonl").open("a") as f:
            f.write(json.dumps({"page": p.stem, "secs": round(secs, 1), "chars": len(text), "error": bool(err), "backend": "surya-vllm"}) + "\n")
        print(f"[surya2] {p.name}: {secs:.1f}s, {len(text)} chars{'  ERROR' if err else ''}", flush=True)
    print("[surya2] DONE", flush=True)
    try: manager.close()
    except Exception: pass

if __name__ == "__main__":
    main()
