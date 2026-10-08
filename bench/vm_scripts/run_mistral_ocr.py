#!/usr/bin/env python
"""Mistral OCR (latest) via OpenRouter's file-parser plugin (engine=mistral-ocr).

Each benchmark page PNG is wrapped unchanged into a one-page PDF (so Mistral OCR sees exactly the
same pixels as every other model), sent with plugins=[{file-parser, pdf.engine=mistral-ocr}], and
the OCR text is taken from the response's `annotations[].file.content` (the raw parser output),
NOT from the chat model's reply. A tiny max_tokens keeps the chat-model cost ~0.
Key: OPENROUTER_API_KEY (loaded from .secrets.env). Usage: python run_mistral_ocr.py [--only p1,p2] [--out DIR]
"""
import argparse, base64, json, os, sys, time
from pathlib import Path
import fitz, requests

BASE = Path(__file__).resolve().parent
for line in (BASE / ".secrets.env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip())
KEY = os.environ["OPENROUTER_API_KEY"]
URL = "https://openrouter.ai/api/v1/chat/completions"
CHAT_MODEL = os.environ.get("OR_CHAT_MODEL", "mistralai/ministral-3b-2512")   # irrelevant: we read annotations

def png_to_pdf_bytes(png):
    pix = fitz.Pixmap(str(png))
    doc = fitz.open(); page = doc.new_page(width=pix.width, height=pix.height)
    page.insert_image(page.rect, pixmap=pix)
    return doc.tobytes()

def ocr_page(png):
    pdf_b64 = base64.b64encode(png_to_pdf_bytes(png)).decode()
    body = {
        "model": CHAT_MODEL, "max_tokens": 8,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": "Reply with OK."},
            {"type": "file", "file": {"filename": f"{png.stem}.pdf", "file_data": f"data:application/pdf;base64,{pdf_b64}"}}]}],
        "plugins": [{"id": "file-parser", "pdf": {"engine": "mistral-ocr"}}],
    }
    r = requests.post(URL, headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
                                    "HTTP-Referer": "https://localhost/ocr-benchmark", "X-Title": "arabic-ocr-benchmark"},
                      json=body, timeout=300)
    r.raise_for_status()
    j = r.json()
    ann = j["choices"][0]["message"].get("annotations") or []
    texts = []
    for a in ann:
        if a.get("type") == "file":
            for c in a.get("file", {}).get("content", []):
                if c.get("type") == "text":
                    texts.append(c.get("text", ""))
    return "\n".join(texts), j

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--only", default=""); ap.add_argument("--out", default=str(BASE / "results" / "mistral_ocr"))
    a = ap.parse_args()
    out_dir = Path(a.out); (out_dir / "_raw").mkdir(parents=True, exist_ok=True)
    pages = sorted((BASE / "pages").glob("*.png"))
    if a.only:
        keep = set(a.only.split(",")); pages = [p for p in pages if p.stem in keep]
    (out_dir / "_meta.json").write_text(json.dumps({"model": "mistral_ocr", "backend": "openrouter file-parser engine=mistral-ocr",
                                                     "chat_model_for_transport": CHAT_MODEL, "date": time.strftime("%F")}, indent=1))
    for p in pages:
        out = out_dir / f"{p.stem}.md"
        if out.exists() and out.stat().st_size > 0:
            print(f"[mistral_ocr] {p.name}: cached, skipping", flush=True); continue
        t0 = time.time(); err = None; text = ""
        try:
            text, raw = ocr_page(p)
            (out_dir / "_raw" / f"{p.stem}.json").write_text(json.dumps(raw, ensure_ascii=False))
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            (out_dir / "_errors.log").open("a").write(f"\n===== {p.name}\n{err}\n")
        secs = time.time() - t0
        out.write_text(text, encoding="utf-8")
        with (out_dir / "_timing.jsonl").open("a") as f:
            f.write(json.dumps({"page": p.stem, "secs": round(secs, 1), "chars": len(text), "error": bool(err), "backend": "openrouter:mistral-ocr"}) + "\n")
        print(f"[mistral_ocr] {p.name}: {secs:.1f}s, {len(text)} chars{'  ERROR ' + err if err else ''}", flush=True)
    print("[mistral_ocr] DONE", flush=True)

if __name__ == "__main__":
    main()
