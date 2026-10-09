"""vLLM backend for the benchmark/pipeline (NVIDIA): same outputs as bench.py (results/<model>/<page>.md, _timing.jsonl,
_meta.json, <page>.tok.json when BENCH_LOGPROBS=1) but pages are sent concurrently to a vLLM OpenAI-compatible server.
Usage: python bench_vllm.py --model dots_mocr|chandra2 --out <dir> [--url http://localhost:8001/v1] [--conc 8]
Env: PAGES_DIR, BENCH_TEMP, BENCH_SEED, BENCH_MAX_TOKENS, BENCH_PROMPT_FILE, BENCH_LOGPROBS, MAX_TIME"""
import argparse, base64, io, json, math, os, sys, time, traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from bench import DOTS_LAYOUT_ALL, CHANDRA_OCR_LAYOUT, looping, prep_chandra, MAX_TIME, BASE
from PIL import Image
import requests
SPECS = {
 "dots_mocr": dict(prompt=DOTS_LAYOUT_ALL, max_tokens=8192, gen=dict(temperature=0.1, top_p=1.0, seed=0), prep=None, port=8001),
 "dots_ocr":  dict(prompt=DOTS_LAYOUT_ALL, max_tokens=8192, gen=dict(temperature=0.1, top_p=1.0, seed=0), prep=None, port=8001),
 "chandra2":  dict(prompt=CHANDRA_OCR_LAYOUT, max_tokens=8192, gen=dict(temperature=0.0), prep="chandra", port=8002),
}
# --- 32-filing rerun: further open models served on this VM (vendor prompts; greedy decoding) ---
import bench as _bench
GENERIC_PROMPT = ("Extract all text and tables from this Arabic document page. "
                  "Preserve the table structure using Markdown. Output only the extracted content.")   # same as the hosted VLM runs
SPECS.update({
 "qari03":         dict(prompt=("Below is the image of one page of a document, as well as some raw textual content that was previously "
                                 "extracted for it. Just return the plain text representation of this document as if you were reading it "
                                 "naturally. Do not hallucinate."), max_tokens=8192, gen=dict(temperature=0.0), prep=None, port=8010),   # vendor prompt (model card)
 "nanonets":       dict(prompt=_bench.SPECS["nanonets"]["prompt"], max_tokens=8192, gen=dict(temperature=0.0), prep=None, port=8010),
 "qwen3vl_32b":    dict(prompt=GENERIC_PROMPT, max_tokens=8192, gen=dict(temperature=0.0), prep=None, port=8010),
 "nemotron12b_vl": dict(prompt=GENERIC_PROMPT, max_tokens=8192, gen=dict(temperature=0.0), prep=None, port=8010),
 "chandra1":       dict(prompt=CHANDRA_OCR_LAYOUT, max_tokens=8192, gen=dict(temperature=0.0), prep="chandra", port=8011),
 # Qwen3.8-27B self-hosted (official BF16 checkpoint); reasoning off, as in the hosted run
 "qwen38_27b":     dict(prompt=GENERIC_PROMPT, max_tokens=8192, gen=dict(temperature=0.0), prep=None, port=8010,
                        extra=dict(chat_template_kwargs={"enable_thinking": False})),
 # LightOnOCR-3 (added 9 Oct 2026): the vendor's transcription mode is an empty prompt (the image alone); greedy decoding
 # as for the other document models; thinking disabled for the Qwen3.5-based 0.8B and 4B (vendor flag). vLLM 0.30.0.
 "lightonocr3_08b": dict(prompt="", max_tokens=8192, gen=dict(temperature=0.0), prep=None, port=8012,
                         extra=dict(chat_template_kwargs={"enable_thinking": False})),
 "lightonocr3_1b":  dict(prompt="", max_tokens=8192, gen=dict(temperature=0.0), prep=None, port=8012),
 "lightonocr3_4b":  dict(prompt="", max_tokens=8192, gen=dict(temperature=0.0), prep=None, port=8012,
                         extra=dict(chat_template_kwargs={"enable_thinking": False})),
})
def b64_image(path, prep):
    if prep == "chandra":
        im = prep_chandra(path)                      # datalab scale_to_fit, as in the local runs (returns a path)
        if not isinstance(im, Image.Image): im = Image.open(im).convert("RGB")
    else: im = Image.open(path).convert("RGB")
    buf = io.BytesIO(); im.save(buf, format="PNG"); return base64.b64encode(buf.getvalue()).decode()
def run_page(p, spec, url, logprobs):
    gen = dict(spec["gen"])
    if os.environ.get("BENCH_TEMP") is not None: gen["temperature"] = float(os.environ["BENCH_TEMP"])
    if os.environ.get("BENCH_SEED") is not None: gen["seed"] = int(os.environ["BENCH_SEED"])
    prompt = Path(os.environ["BENCH_PROMPT_FILE"]).read_text() if os.environ.get("BENCH_PROMPT_FILE") else spec["prompt"]
    max_tokens = int(os.environ.get("BENCH_MAX_TOKENS", spec["max_tokens"]))
    content = [{"type": "image_url", "image_url": {"url": "data:image/png;base64," + b64_image(p, spec["prep"])}}]
    if prompt:                                      # an empty prompt (LightOnOCR-3 transcription mode) sends the image alone
        content.append({"type": "text", "text": prompt})
    body = {"model": "model", "messages": [{"role": "user", "content": content}],
            "max_tokens": max_tokens, "stream": True, "stream_options": {"include_usage": True}, **gen, **spec.get("extra", {})}
    if logprobs: body["logprobs"] = True; body["top_logprobs"] = 2
    t0 = time.time(); parts = []; toks = []; n = 0; finish = None; usage = None; loop_stop = False; timed_out = False
    with requests.post(url + "/chat/completions", json=body, stream=True, timeout=(30, MAX_TIME + 60)) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line: continue
            line = line.decode() if isinstance(line, bytes) else line
            if not line.startswith("data:"): continue
            data = line[5:].strip()
            if data == "[DONE]": break
            ev = json.loads(data)
            if ev.get("usage"): usage = ev["usage"]
            for ch in ev.get("choices", []):
                d = ch.get("delta", {}) or {}; txt = d.get("content") or ""
                if txt: parts.append(txt); n += 1
                if ch.get("finish_reason"): finish = ch["finish_reason"]
                lp = (ch.get("logprobs") or {}).get("content") or []
                for t in lp:
                    tops = t.get("top_logprobs") or []
                    best = max((x["logprob"] for x in tops), default=t["logprob"])
                    toks.append((t.get("token"), t.get("token"), t["logprob"], best))   # (id-less) token text, text, lp, max lp
            if time.time() - t0 > MAX_TIME: timed_out = True; break
            if n % 32 == 0 and looping("".join(parts)): loop_stop = True; break
    text = "".join(parts); secs = time.time() - t0
    stats = {"gen_tokens": (usage or {}).get("completion_tokens", len(toks) or None), "prompt_tokens": (usage or {}).get("prompt_tokens"),
             "finish": "loop" if loop_stop else "max_time" if timed_out else (finish or "stop")}
    if stats["gen_tokens"]: stats["gen_tps"] = round(stats["gen_tokens"] / max(secs, 1e-6), 1)
    return text, stats, toks
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--model", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--url", default=None); ap.add_argument("--conc", type=int, default=int(os.environ.get("BENCH_CONC", "8"))); ap.add_argument("--only", default="")
    a = ap.parse_args(); spec = SPECS[a.model]; url = a.url or os.environ.get("VLLM_URL") or f"http://localhost:{spec['port']}/v1"
    pages_dir = Path(os.environ.get("PAGES_DIR", BASE / "pages")); pages = sorted(pages_dir.glob("*.png"))
    if a.only: pages = [p for p in pages if any(k in p.name for k in a.only.split(","))]
    out_dir = Path(a.out); out_dir.mkdir(parents=True, exist_ok=True); logprobs = bool(os.environ.get("BENCH_LOGPROBS"))
    todo = [p for p in pages if not ((out_dir / f"{p.stem}.md").exists() and (out_dir / f"{p.stem}.md").stat().st_size > 0)]
    print(f"[{a.model}] {len(pages)} pages ({len(todo)} to run) -> {out_dir}  backend=vllm {url} conc={a.conc}", flush=True)
    (out_dir / "_meta.json").write_text(json.dumps({"model": a.model, "backend": "vllm", "url": url, "prompt": spec["prompt"][:200], "gen": spec["gen"], "max_tokens": spec["max_tokens"], "env": {k: v for k, v in os.environ.items() if k.startswith("BENCH_")}}, indent=1))
    def work(p):
        t0 = time.time()
        try: text, stats, toks = run_page(p, spec, url, logprobs); err = None
        except Exception: text, stats, toks, err = "", {}, [], traceback.format_exc()
        if err: (out_dir / "_errors.log").open("a").write(f"\n===== {p.name} {time.ctime()}\n{err}")
        (out_dir / f"{p.stem}.md").write_text(text, encoding="utf-8")
        if toks: (out_dir / f"{p.stem}.tok.json").write_text(json.dumps(toks, ensure_ascii=False))
        rec = {"page": p.stem, "secs": round(time.time() - t0, 1), "chars": len(text), "error": bool(err), **stats}
        with (out_dir / "_timing.jsonl").open("a") as f: f.write(json.dumps(rec) + "\n")
        print(f"[{a.model}] {p.name}: {rec['secs']}s, {len(text)} chars, {rec.get('gen_tokens','?')} tok, finish={rec.get('finish')}{'  ERROR' if err else ''}", flush=True)
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=a.conc) as ex: list(ex.map(work, todo))
    print(f"[{a.model}] DONE in {time.time()-t0:.0f}s", flush=True)
