"""NuExtract3 benchmark runner. Same output layout as bench_vllm.py (results/<name>/<page>.md + _timing.jsonl)
so eval2.py can score it against the frozen GT.

Markdown mode:  python3 nuex_bench.py --out results_nuex/nuextract3_md
Template probe: python3 nuex_bench.py --template --only drilling_p08,aramco_p12 --out results_nuex/probe
Env: NUEX_URL (default http://localhost:8004/v1), NUEX_TEMP (default 1.0 md / 0.2 template), PAGES_DIR, NUEX_CONC
"""
import argparse, base64, json, os, time, traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests

BASE = Path(__file__).resolve().parent
MAX_TIME = 600

FIN_TEMPLATE = {
    "statement_title": "verbatim-string",
    "currency": "string",
    "column_headers": ["verbatim-string"],
    "rows": [{
        "label": "verbatim-string",
        "note_ref": "string",
        "values": ["verbatim-string"],
        "is_total": ["yes", "no"],
    }],
}

def run_page(p, url, mode, temp, max_tokens):
    body = {
        "model": "nuextract",
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()}}]}],
        "temperature": temp, "max_tokens": max_tokens,
        "chat_template_kwargs": (
            {"mode": "markdown", "enable_thinking": False} if mode == "markdown"
            else {"template": json.dumps(FIN_TEMPLATE, ensure_ascii=False), "enable_thinking": False}),
    }
    t0 = time.time()
    r = requests.post(url + "/chat/completions", json=body, timeout=(30, MAX_TIME))
    r.raise_for_status()
    j = r.json()
    text = j["choices"][0]["message"]["content"] or ""
    if "</think>" in text: text = text.split("</think>", 1)[1]
    u = j.get("usage") or {}
    return text.strip(), {"gen_tokens": u.get("completion_tokens"), "prompt_tokens": u.get("prompt_tokens"),
                          "finish": j["choices"][0].get("finish_reason"), "secs_api": round(time.time() - t0, 1)}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True); ap.add_argument("--only", default="")
    ap.add_argument("--template", action="store_true"); ap.add_argument("--conc", type=int, default=int(os.environ.get("NUEX_CONC", "4")))
    a = ap.parse_args()
    mode = "template" if a.template else "markdown"
    temp = float(os.environ.get("NUEX_TEMP", "0.2" if a.template else "1.0"))
    max_tokens = 8192 if a.template else 14000
    url = os.environ.get("NUEX_URL", "http://localhost:8004/v1")
    pages_dir = Path(os.environ.get("PAGES_DIR", BASE / "pages_pipe/chandra_cap")); pages = sorted(pages_dir.glob("*.png"))
    if a.only: pages = [p for p in pages if any(k in p.name for k in a.only.split(","))]
    out_dir = Path(a.out); out_dir.mkdir(parents=True, exist_ok=True)
    ext = ".json" if a.template else ".md"
    todo = [p for p in pages if not ((out_dir / (p.stem + ext)).exists() and (out_dir / (p.stem + ext)).stat().st_size > 0)]
    print(f"[nuextract3/{mode} t={temp}] {len(pages)} pages ({len(todo)} to run) -> {out_dir}  {url}", flush=True)
    (out_dir / "_meta.json").write_text(json.dumps({"model": "nuextract3", "mode": mode, "temp": temp, "max_tokens": max_tokens, "url": url, "pages": str(pages_dir)}, indent=1))
    def work(p):
        t0 = time.time()
        try: text, stats = run_page(p, url, mode, temp, max_tokens); err = None
        except Exception: text, stats, err = "", {}, traceback.format_exc()
        if err: (out_dir / "_errors.log").open("a").write(f"\n===== {p.name} {time.ctime()}\n{err}")
        (out_dir / (p.stem + ext)).write_text(text, encoding="utf-8")
        rec = {"page": p.stem, "secs": round(time.time() - t0, 1), "chars": len(text), "error": bool(err), **stats}
        with (out_dir / "_timing.jsonl").open("a") as f: f.write(json.dumps(rec) + "\n")
        print(f"  {p.stem}: {rec['chars']} chars {rec['secs']}s {'ERR' if err else ''}", flush=True)
    with ThreadPoolExecutor(a.conc) as ex: list(ex.map(work, todo))
    print("done", flush=True)
