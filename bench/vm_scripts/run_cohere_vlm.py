#!/usr/bin/env python
"""Cohere hosted VLMs (Aya Vision 32B, Command A Vision) via the v2 Chat API with a base64 image.
Usage: python run_cohere_vlm.py --model c4ai-aya-vision-32b --name aya32b_api [--temperature 0.3] [--only ...]
Key: COHERE_API_KEY from .secrets.env."""
import argparse, base64, json, os, time
from pathlib import Path
import requests

BASE = Path(__file__).resolve().parent
for line in (BASE / ".secrets.env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip())
KEY = os.environ["COHERE_API_KEY"]
URL = "https://api.cohere.com/v2/chat"
PROMPT = ("Extract all text and tables from this Arabic document page. "
          "Preserve the table structure using Markdown. Output only the extracted content.")

def ask(model, png, max_tokens=4096, temperature=0.0):
    b64 = base64.b64encode(png.read_bytes()).decode()
    body = {"model": model, "temperature": temperature, "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}]}]}
    r = requests.post(URL, headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json", "Accept": "application/json"},
                      json=body, timeout=600)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
    j = r.json()
    text = "".join(c.get("text", "") for c in j.get("message", {}).get("content", []) if c.get("type") == "text")
    return text, j.get("finish_reason"), j.get("usage", {}), j

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True); ap.add_argument("--name", required=True)
    ap.add_argument("--temperature", type=float, default=0.0); ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--only", default=""); ap.add_argument("--out", default="")
    a = ap.parse_args()
    out_dir = Path(a.out) if a.out else BASE / "results" / a.name
    (out_dir / "_raw").mkdir(parents=True, exist_ok=True)
    pages = sorted(Path(os.environ.get("PAGES_DIR", BASE / "pages")).glob("*.png"))
    if a.only:
        keep = set(a.only.split(",")); pages = [p for p in pages if p.stem in keep]
    (out_dir / "_meta.json").write_text(json.dumps({"model": a.name, "backend": f"cohere-api:{a.model}", "prompt": PROMPT,
                                                     "temperature": a.temperature, "max_tokens": a.max_tokens, "date": time.strftime("%F")}, indent=1))
    for p in pages:
        out = out_dir / f"{p.stem}.md"
        if out.exists() and out.stat().st_size > 0:
            print(f"[{a.name}] {p.name}: cached, skipping", flush=True); continue
        t0 = time.time(); err = None; text = ""; fin = None; usage = {}
        try:
            text, fin, usage, raw = ask(a.model, p, a.max_tokens, a.temperature)
            (out_dir / "_raw" / f"{p.stem}.json").write_text(json.dumps(raw, ensure_ascii=False))
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            (out_dir / "_errors.log").open("a").write(f"\n===== {p.name}\n{err}\n")
        secs = time.time() - t0
        out.write_text(text, encoding="utf-8")
        toks = (usage.get("tokens") or {})
        rec = {"page": p.stem, "secs": round(secs, 1), "chars": len(text), "error": bool(err), "backend": f"cohere-api:{a.model}",
               "prompt_tokens": toks.get("input_tokens"), "gen_tokens": toks.get("output_tokens"), "finish": fin}
        with (out_dir / "_timing.jsonl").open("a") as f:
            f.write(json.dumps(rec) + "\n")
        print(f"[{a.name}] {p.name}: {secs:.1f}s, {len(text)} chars, {toks.get('output_tokens','?')} tok, finish={fin}{'  ERROR ' + err if err else ''}", flush=True)
    print(f"[{a.name}] DONE", flush=True)

if __name__ == "__main__":
    main()
