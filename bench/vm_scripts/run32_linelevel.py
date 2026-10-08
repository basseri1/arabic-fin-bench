"""Persian-Arabic line OCR (mohajesmaeili/Qwen3-VL-2B-Persian-Arabic-Ocr-v1.0) served by vLLM on this VM.
Text-line boxes come from the classical PaddleOCR detector (results32/paddle_ar_plain/<page>.json); each crop
(4 px margin, as in the pilot) is recognised with the pilot prompt; lines are regrouped into rows with the same
rule as the classical baseline. usage: python run32_linelevel.py --out results32/persar2b_plain [--conc 32]"""
import argparse, base64, io, json, os, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests
from PIL import Image
sys.path.insert(0, ".")
from run_paddle_classic import rows_from_lines
PROMPT = "Read the text in this image."
def rec(url, crop):
    buf = io.BytesIO(); crop.save(buf, format="PNG")
    body = {"model": "model", "temperature": 0.0, "max_tokens": 128,
            "messages": [{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()}},
                {"type": "text", "text": PROMPT}]}]}
    r = requests.post(url + "/chat/completions", json=body, timeout=300); r.raise_for_status()
    return (r.json()["choices"][0]["message"].get("content") or "").strip()
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("--url", default="http://localhost:8010/v1")
    ap.add_argument("--boxes", default="results32/paddle_ar_plain"); ap.add_argument("--pages", default="pages32/plain"); ap.add_argument("--conc", type=int, default=32)
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    (out / "_meta.json").write_text(json.dumps({"model": "persar2b", "backend": "vllm (line recognizer) + PaddleOCR det boxes",
        "prompt": PROMPT, "postproc": "rows by y-center clustering, RTL", "date": time.strftime("%F")}, indent=1))
    pool = ThreadPoolExecutor(max_workers=a.conc)
    for p in sorted(Path(a.pages).glob("*.png")):
        f = out / f"{p.stem}.md"
        if f.exists() and f.stat().st_size > 0: continue
        t0 = time.time(); err = None; text = ""; n = 0
        try:
            boxes = [tuple(d["bbox"]) for d in json.loads((Path(a.boxes) / f"{p.stem}.json").read_text())]
            im = Image.open(p).convert("RGB")
            crops = [im.crop((max(0, b[0]-4), max(0, b[1]-4), min(im.width, b[2]+4), min(im.height, b[3]+4))) for b in boxes]
            texts = list(pool.map(lambda c: rec(a.url, c), crops))
            items = [(list(b), t) for b, t in zip(boxes, texts)]; n = len(items)
            text = "\n".join(rows_from_lines(items))
            (out / f"{p.stem}.json").write_text(json.dumps([{"bbox": b, "text": t} for b, t in items], ensure_ascii=False))
        except Exception:
            import traceback; err = traceback.format_exc()
            (out / "_errors.log").open("a").write(f"\n===== {p.name}\n{err}\n")
        f.write_text(text, encoding="utf-8")
        with (out / "_timing.jsonl").open("a") as t: t.write(json.dumps({"page": p.stem, "secs": round(time.time() - t0, 1), "lines": n, "chars": len(text), "error": bool(err)}) + "\n")
        print(f"[persar2b] {p.name}: {time.time()-t0:.1f}s, {n} lines{'  ERROR' if err else ''}", flush=True)
    print("[persar2b] DONE", flush=True)
