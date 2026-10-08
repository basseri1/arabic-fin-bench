#!/usr/bin/env python
"""Provider-pinned OpenRouter runs: the same pages, the same request as the hosted Qwen3.8-27B run (same prompt,
temperature 0, max_tokens 8192, reasoning off), sent to ONE named provider with fallbacks disabled.
Usage: PAGES_DIR=pages32/plain python run_provider_pin.py --model qwen/qwen3.8-27b --provider deepinfra --out DIR --only p1,p2
Key: OPENROUTER_API_KEY from .secrets.env."""
import argparse, base64, json, os, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests

BASE = Path(__file__).resolve().parent
for line in (BASE / ".secrets.env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip())
KEY = os.environ["OPENROUTER_API_KEY"]
URL = "https://openrouter.ai/api/v1/chat/completions"
PROMPT = ("Extract all text and tables from this Arabic document page. "
          "Preserve the table structure using Markdown. Output only the extracted content.")   # as run_openrouter_vlm.py

def ask(model, provider, png, max_tokens):
    b64 = base64.b64encode(png.read_bytes()).decode()
    body = {"model": model, "temperature": 0, "max_tokens": max_tokens, "usage": {"include": True},
            "reasoning": {"enabled": False}, "provider": {"order": [provider], "allow_fallbacks": False},
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}]}]}
    for attempt in range(4):
        r = requests.post(URL, headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
                                        "HTTP-Referer": "https://localhost/ocr-benchmark", "X-Title": "arabic-ocr-benchmark"},
                          json=body, timeout=600)
        if r.status_code == 200:
            j = r.json(); ch = j["choices"][0]
            return ch["message"].get("content") or "", ch.get("finish_reason"), j.get("usage", {}), j
        if r.status_code in (429, 500, 502, 503, 504) and attempt < 3:
            time.sleep(15 * (attempt + 1)); continue
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True); ap.add_argument("--provider", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--only", required=True); ap.add_argument("--max-tokens", type=int, default=8192); ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    out_dir = Path(a.out); (out_dir / "_raw").mkdir(parents=True, exist_ok=True)
    keep = set(a.only.split(","))
    pages = [p for p in sorted(Path(os.environ.get("PAGES_DIR", BASE / "pages")).glob("*.png")) if p.stem in keep]
    (out_dir / "_meta.json").write_text(json.dumps({"backend": f"openrouter:{a.model}", "provider_pinned": a.provider,
        "allow_fallbacks": False, "prompt": PROMPT, "temperature": 0, "max_tokens": a.max_tokens, "reasoning_disabled": True,
        "date": time.strftime("%F")}, indent=1))
    def work(p):
        out = out_dir / f"{p.stem}.md"
        if out.exists() and out.stat().st_size > 0: return
        t0 = time.time(); err = None; text = ""; fin = None; usage = {}; prov = None
        try:
            text, fin, usage, raw = ask(a.model, a.provider, p, a.max_tokens); prov = raw.get("provider")
            (out_dir / "_raw" / f"{p.stem}.json").write_text(json.dumps(raw, ensure_ascii=False))
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            (out_dir / "_errors.log").open("a").write(f"\n===== {p.name}\n{err}\n")
        out.write_text(text, encoding="utf-8")
        rec = {"page": p.stem, "secs": round(time.time() - t0, 1), "chars": len(text), "error": bool(err), "provider": prov,
               "prompt_tokens": usage.get("prompt_tokens"), "gen_tokens": usage.get("completion_tokens"), "cost_usd": usage.get("cost"), "finish": fin}
        with (out_dir / "_timing.jsonl").open("a") as f: f.write(json.dumps(rec) + "\n")
        print(f"[{a.provider}] {p.name}: {rec['secs']}s, {len(text)} chars, provider={prov}, finish={fin}{'  ERROR ' + err if err else ''}", flush=True)
    with ThreadPoolExecutor(max_workers=a.workers) as ex: list(ex.map(work, pages))
    print(f"[{a.provider}] DONE", flush=True)

if __name__ == "__main__":
    main()
