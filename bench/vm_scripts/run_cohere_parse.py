#!/usr/bin/env python
"""Cohere Parse (parse-v5.0) via POST /v2/parse with a base64 PNG data URI; markdown output (tables as HTML).
Same output layout as the other runners: <out>/<page>.md, _timing.jsonl, _meta.json, _raw/<page>.json.
Usage: PAGES_DIR=pages32/plain python run_cohere_parse.py --out results32/cohere_parse_plain [--workers 4] [--only ...]
Key: COHERE_API_KEY from .secrets.env."""
import argparse, base64, json, os, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests

BASE = Path(__file__).resolve().parent
for line in (BASE / ".secrets.env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip())
KEY = os.environ["COHERE_API_KEY"]
URL = "https://api.cohere.com/v2/parse"
MODEL = "parse-v5.0"

def parse(png):
    b64 = base64.b64encode(png.read_bytes()).decode()
    body = {"model": MODEL, "document": {"type": "image_url", "image_url": f"data:image/png;base64,{b64}"},
            "output_format": "markdown"}
    for attempt in range(6):
        r = requests.post(URL, headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
                                        "Accept": "application/json"}, json=body, timeout=600)
        if r.status_code == 200:
            j = r.json()
            text = "\n\n".join((pg.get("markdown") or {}).get("content", "") for pg in j.get("pages", []))
            return text, j.get("finish_reason"), j.get("meta", {}), j
        if r.status_code in (429, 500, 502, 503, 504) and attempt < 5:
            time.sleep(10 * 2 ** attempt); continue
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True); ap.add_argument("--only", default=""); ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    out_dir = Path(a.out); (out_dir / "_raw").mkdir(parents=True, exist_ok=True)
    pages = sorted(Path(os.environ.get("PAGES_DIR", BASE / "pages")).glob("*.png"))
    if a.only:
        keep = set(a.only.split(",")); pages = [p for p in pages if p.stem in keep]
    (out_dir / "_meta.json").write_text(json.dumps({"model": "cohere_parse", "backend": f"cohere-api /v2/parse:{MODEL}",
                                                     "output_format": "markdown", "date": time.strftime("%F")}, indent=1))
    todo = [p for p in pages if not ((out_dir / f"{p.stem}.md").exists() and (out_dir / f"{p.stem}.md").stat().st_size > 0)]
    print(f"[cohere_parse] {len(pages)} pages ({len(todo)} to run), {a.workers} in flight", flush=True)
    def work(p):
        t0 = time.time(); err = None; text = ""; fin = None; meta = {}
        try:
            text, fin, meta, raw = parse(p)
            (out_dir / "_raw" / f"{p.stem}.json").write_text(json.dumps(raw, ensure_ascii=False))
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            (out_dir / "_errors.log").open("a").write(f"\n===== {p.name}\n{err}\n")
        secs = time.time() - t0
        (out_dir / f"{p.stem}.md").write_text(text, encoding="utf-8")
        rec = {"page": p.stem, "secs": round(secs, 1), "chars": len(text), "error": bool(err),
               "backend": f"cohere-api:{MODEL}", "finish": fin, "billed": (meta or {}).get("billed_units")}
        with (out_dir / "_timing.jsonl").open("a") as f:
            f.write(json.dumps(rec) + "\n")
        print(f"[cohere_parse] {p.name}: {secs:.1f}s, {len(text)} chars, finish={fin}{'  ERROR ' + err if err else ''}", flush=True)
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        list(ex.map(work, todo))
    print(f"[cohere_parse] DONE in {time.time() - t0:.0f}s", flush=True)

if __name__ == "__main__":
    main()
