#!/usr/bin/env python
"""LandingAI Agentic Document Extraction (ADE) Parse, v2 API, DPT-3 Pro pinned to snapshot dpt-3-pro-20260710, one
page image per request, default options (Markdown with tables as HTML, merged cells kept). Run as Parse Jobs on the
`standard` service tier: the same model and output as the synchronous endpoint, at half the credits (docs.landing.ai,
dpt3/credit-consumption, read 3 Oct 2026). All jobs are created first and their ids saved to _jobs.json, then polled; a
re-run polls the saved jobs instead of creating new ones, so no page is parsed or billed twice.
Same output layout as the other runners: <out>/<page>.md, _timing.jsonl, _meta.json, _raw/<page>.json.
Usage: PAGES_DIR=pages32/plain python run_landingai_ade.py --out results32/landingai_ade_plain [--only a,b]
       [--secrets FILE]   Key: VISION_AGENT_API_KEY from the environment or from the secrets file (default .secrets.env
       next to this script)."""
import argparse, json, os, time
from pathlib import Path
import requests

BASE = Path(__file__).resolve().parent
API = "https://api.ade.landing.ai/v2/parse/jobs"
MODEL = "dpt-3-pro-20260710"
TIER = "standard"


def api_key(secrets):
    if os.environ.get("VISION_AGENT_API_KEY"):
        return os.environ["VISION_AGENT_API_KEY"]
    f = Path(secrets)
    if f.exists():
        for line in f.read_text().splitlines():
            if line.strip().startswith("VISION_AGENT_API_KEY="):
                return line.split("=", 1)[1].strip()
    raise SystemExit(f"VISION_AGENT_API_KEY not set and not found in {f}")


def create(png, key):
    for attempt in range(8):
        with png.open("rb") as fh:
            r = requests.post(API, headers={"Authorization": f"Bearer {key}"}, timeout=300,
                              files={"document": (png.name, fh, "image/png")},
                              data={"model": MODEL, "service_tier": TIER})
        if r.status_code in (200, 202):
            return r.json()["job_id"]
        if r.status_code in (429, 500, 502, 503, 504) and attempt < 7:
            time.sleep(min(300, 10 * 2 ** attempt)); continue
        raise RuntimeError(f"create HTTP {r.status_code}: {r.text[:300]}")


def get(job_id, key):
    for attempt in range(6):
        r = requests.get(f"{API}/{job_id}", headers={"Authorization": f"Bearer {key}"}, timeout=120)
        if r.status_code == 200:
            return r.json()
        if r.status_code in (429, 500, 502, 503, 504) and attempt < 5:
            time.sleep(10 * 2 ** attempt); continue
        raise RuntimeError(f"get HTTP {r.status_code}: {r.text[:300]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True); ap.add_argument("--only", default="")
    ap.add_argument("--secrets", default=str(BASE / ".secrets.env")); ap.add_argument("--poll", type=int, default=20)
    a = ap.parse_args()
    key = api_key(a.secrets)
    out = Path(a.out); (out / "_raw").mkdir(parents=True, exist_ok=True)
    pages = sorted(Path(os.environ.get("PAGES_DIR", BASE / "pages")).glob("*.png"))
    if a.only:
        keep = set(a.only.split(",")); pages = [p for p in pages if p.stem in keep]
    (out / "_meta.json").write_text(json.dumps({"model": "landingai_ade", "backend": f"landingai-ade /v2/parse/jobs:{MODEL}",
                                                 "service_tier": TIER, "output_format": "markdown, tables as html (default options)",
                                                 "date": time.strftime("%F")}, indent=1))
    jobs_f = out / "_jobs.json"
    jobs = json.loads(jobs_f.read_text()) if jobs_f.exists() else {}
    done = lambda p: (out / f"{p.stem}.md").exists() and (out / f"{p.stem}.md").stat().st_size > 0
    todo = [p for p in pages if not done(p)]
    print(f"[landingai_ade] {len(pages)} pages, {len(todo)} to run ({sum(p.stem in jobs for p in todo)} already submitted)", flush=True)
    for p in todo:                                      # 1. create every job not yet created, saving ids as we go
        if p.stem in jobs:
            continue
        try:
            jobs[p.stem] = {"job_id": create(p, key), "submitted": time.time()}
        except Exception as e:
            (out / "_errors.log").open("a").write(f"\n===== {p.name} (create)\n{e}\n")
            print(f"[landingai_ade] {p.name}: create failed: {e}", flush=True)
            continue
        jobs_f.write_text(json.dumps(jobs, indent=1))
        print(f"[landingai_ade] {p.name}: job {jobs[p.stem]['job_id']}", flush=True)
    pending = {p.stem for p in todo if p.stem in jobs}
    t0 = time.time()
    while pending:                                      # 2. poll until every job is completed or failed
        for stem in sorted(pending):
            info = jobs[stem]
            try:
                j = get(info["job_id"], key)
            except Exception as e:
                print(f"[landingai_ade] {stem}: poll error {e}", flush=True); continue
            if j.get("status") not in ("completed", "failed"):
                continue
            pending.discard(stem)
            res = j.get("result") or {}
            md, meta = res.get("markdown") or "", res.get("metadata") or {}
            (out / "_raw" / f"{stem}.json").write_text(json.dumps(j, ensure_ascii=False))
            if j["status"] == "failed":
                (out / "_errors.log").open("a").write(f"\n===== {stem} (job failed)\n{json.dumps(j.get('error'))}\n")
            (out / f"{stem}.md").write_text(md, encoding="utf-8")
            rec = {"page": stem, "job_id": info["job_id"], "status": j["status"], "chars": len(md),
                   "secs_to_complete": round(time.time() - info["submitted"], 1), "model_version": meta.get("model_version"),
                   "output_markdown_chars": meta.get("output_markdown_chars"), "billing": meta.get("billing"),
                   "duration_ms": meta.get("duration_ms"), "failed_pages": meta.get("failed_pages"), "error": j.get("error")}
            with (out / "_timing.jsonl").open("a") as f:
                f.write(json.dumps(rec) + "\n")
            print(f"[landingai_ade] {stem}: {j['status']}, {len(md)} chars, {(meta.get('billing') or {}).get('total_credits')} credits, "
                  f"{meta.get('model_version')}", flush=True)
        if pending:
            time.sleep(a.poll)
    print(f"[landingai_ade] DONE, polled for {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
