#!/usr/bin/env python
"""Hosted VLM via OpenRouter chat completions (image_url = base64 PNG at full page resolution).
Same instruction prompt as the local general-purpose VLMs; temperature 0; max_tokens 4096.
Usage: python run_openrouter_vlm.py --model qwen/qwen3.8-27b --name qwen38_27b [--only p1,p2] [--out DIR]
Key: OPENROUTER_API_KEY from .secrets.env. Records token usage + cost per page in _timing.jsonl."""
import argparse, base64, json, os, time
from pathlib import Path
import requests

BASE = Path(__file__).resolve().parent
for line in (BASE / ".secrets.env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip())
KEY = os.environ["OPENROUTER_API_KEY"]
URL = "https://openrouter.ai/api/v1/chat/completions"
PROMPT = ("Extract all text and tables from this Arabic document page. "
          "Preserve the table structure using Markdown. Output only the extracted content.")

def ask(model, png, max_tokens, no_think=False):
    b64 = base64.b64encode(png.read_bytes()).decode()
    body = {"model": model, "temperature": 0, "max_tokens": max_tokens, "usage": {"include": True},
            **({"reasoning": {"enabled": False}} if no_think else {}),
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}]}]}
    r = requests.post(URL, headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
                                    "HTTP-Referer": "https://localhost/ocr-benchmark", "X-Title": "arabic-ocr-benchmark"},
                      json=body, timeout=600)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
    j = r.json()
    ch = j["choices"][0]
    return ch["message"].get("content") or "", ch.get("finish_reason"), j.get("usage", {}), j

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True); ap.add_argument("--name", required=True)
    ap.add_argument("--only", default=""); ap.add_argument("--out", default=""); ap.add_argument("--max-tokens", type=int, default=4096); ap.add_argument("--no-think", action="store_true")
    a = ap.parse_args()
    out_dir = Path(a.out) if a.out else BASE / "results" / a.name
    (out_dir / "_raw").mkdir(parents=True, exist_ok=True)
    pages = sorted(Path(os.environ.get("PAGES_DIR", BASE / "pages")).glob("*.png"))
    if a.only:
        keep = set(a.only.split(",")); pages = [p for p in pages if p.stem in keep]
    (out_dir / "_meta.json").write_text(json.dumps({"model": a.name, "backend": f"openrouter:{a.model}", "prompt": PROMPT,
                                                     "temperature": 0, "max_tokens": a.max_tokens, "reasoning_disabled": a.no_think, "date": time.strftime("%F")}, indent=1))
    for p in pages:
        out = out_dir / f"{p.stem}.md"
        if out.exists() and out.stat().st_size > 0:
            print(f"[{a.name}] {p.name}: cached, skipping", flush=True); continue
        t0 = time.time(); err = None; text = ""; fin = None; usage = {}
        try:
            text, fin, usage, raw = ask(a.model, p, a.max_tokens, a.no_think)
            (out_dir / "_raw" / f"{p.stem}.json").write_text(json.dumps(raw, ensure_ascii=False))
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            (out_dir / "_errors.log").open("a").write(f"\n===== {p.name}\n{err}\n")
        secs = time.time() - t0
        out.write_text(text, encoding="utf-8")
        rec = {"page": p.stem, "secs": round(secs, 1), "chars": len(text), "error": bool(err), "backend": f"openrouter:{a.model}",
               "prompt_tokens": usage.get("prompt_tokens"), "gen_tokens": usage.get("completion_tokens"),
               "cost_usd": usage.get("cost"), "finish": fin,
               "reasoning_tokens": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens")}
        with (out_dir / "_timing.jsonl").open("a") as f:
            f.write(json.dumps(rec) + "\n")
        print(f"[{a.name}] {p.name}: {secs:.1f}s, {len(text)} chars, {usage.get('completion_tokens','?')} tok, finish={fin}, ${usage.get('cost', 0) or 0:.4f}{'  ERROR ' + err if err else ''}", flush=True)
    print(f"[{a.name}] DONE", flush=True)

if __name__ == "__main__":
    main()
