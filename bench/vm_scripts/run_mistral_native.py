#!/usr/bin/env python
"""Mistral OCR (mistral-ocr-latest) via Mistral's native /v1/ocr endpoint.
Each benchmark page PNG is sent as a base64 image_url document (same pixels as every other model).
Output = the page markdown returned by the API. Key: MISTRAL_API_KEY from .secrets.env.
Usage: python run_mistral_native.py [--only p1,p2] [--out DIR]
"""
import argparse, base64, json, os, time
from pathlib import Path
import requests

BASE = Path(__file__).resolve().parent
for line in (BASE / ".secrets.env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip())
KEY = os.environ["MISTRAL_API_KEY"]
URL = "https://api.mistral.ai/v1/ocr"
MODEL = os.environ.get("MISTRAL_OCR_MODEL", "mistral-ocr-latest")

def ocr_page(png):
    b64 = base64.b64encode(png.read_bytes()).decode()
    body = {"model": MODEL, "document": {"type": "image_url", "image_url": f"data:image/png;base64,{b64}"},
            "include_image_base64": False}
    r = requests.post(URL, headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}, json=body, timeout=300)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
    j = r.json()
    md = "\n\n".join(p.get("markdown", "") for p in j.get("pages", []))
    return md, j

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--only", default=""); ap.add_argument("--out", default=str(BASE / "results" / "mistral_ocr"))
    a = ap.parse_args()
    out_dir = Path(a.out); (out_dir / "_raw").mkdir(parents=True, exist_ok=True)
    pages = sorted(Path(os.environ.get("PAGES_DIR", BASE / "pages")).glob("*.png"))
    if a.only:
        keep = set(a.only.split(",")); pages = [p for p in pages if p.stem in keep]
    meta = {"model": "mistral_ocr", "backend": "mistral api /v1/ocr", "requested_model": MODEL, "date": time.strftime("%F")}
    for p in pages:
        out = out_dir / f"{p.stem}.md"
        if out.exists() and out.stat().st_size > 0:
            print(f"[mistral_ocr] {p.name}: cached, skipping", flush=True); continue
        t0 = time.time(); err = None; text = ""
        try:
            text, raw = ocr_page(p)
            meta["served_model"] = raw.get("model"); meta["usage_info"] = raw.get("usage_info")
            (out_dir / "_raw" / f"{p.stem}.json").write_text(json.dumps(raw, ensure_ascii=False))
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            (out_dir / "_errors.log").open("a").write(f"\n===== {p.name}\n{err}\n")
        secs = time.time() - t0
        out.write_text(text, encoding="utf-8")
        with (out_dir / "_timing.jsonl").open("a") as f:
            f.write(json.dumps({"page": p.stem, "secs": round(secs, 1), "chars": len(text), "error": bool(err), "backend": "mistral-api"}) + "\n")
        print(f"[mistral_ocr] {p.name}: {secs:.1f}s, {len(text)} chars{'  ERROR ' + err if err else ''}", flush=True)
    (out_dir / "_meta.json").write_text(json.dumps(meta, indent=1))
    print("[mistral_ocr] DONE", flush=True)

if __name__ == "__main__":
    main()
