#!/usr/bin/env python
"""nace.ai Perception, Parse a document (console.nace.ai, docs read 9 Oct 2026), one page image per job. Flow:
POST /v1/documents/upload-grants -> multipart upload of the PNG to the grant's upload_url -> POST /v1/documents/parse with
the uploaded file as a workspace_file source -> poll GET /v1/documents/jobs/{id} until the job is final. Markdown with
tables as HTML (the service's default), no page markers. Parse costs 1 credit per page (2 in mode "high").
An Idempotency-Key per page and mode means that a re-run returns the same job, so no page is parsed or billed twice.
Same output layout as the other runners: <out>/<page>.md, _timing.jsonl, _meta.json, _raw/<page>.json, _jobs.json.
Usage: PAGES_DIR=pages32/plain python run_nace.py --mode low --out results32/nace_low [--only a,b] [--conc 4]
Key: NACE_API_KEY from the environment or from ~/.config/nace/env (KEY=VALUE lines)."""
import argparse, json, os, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests

BASE = "https://console.nace.ai"
FINAL = {"succeeded", "failed", "cancelled"}


def api_key():
    if os.environ.get("NACE_API_KEY"):
        return os.environ["NACE_API_KEY"]
    f = Path.home() / ".config" / "nace" / "env"
    if f.exists():
        for line in f.read_text().splitlines():
            if line.strip().startswith("NACE_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"')
    raise SystemExit("NACE_API_KEY not set and ~/.config/nace/env not found")


def call(method, url, key, **kw):
    """One HTTP call with retries on rate limits and transient errors; returns the Response."""
    headers = {"Authorization": f"Bearer {key}", **kw.pop("headers", {})}
    for attempt in range(8):
        r = requests.request(method, url, headers=headers, timeout=kw.pop("timeout", 180), **kw)
        if r.status_code < 400:
            return r
        if r.status_code in (429, 500, 502, 503, 504, 529) and attempt < 7:
            wait = float(r.headers.get("retry-after") or min(120, 5 * 2 ** attempt))
            time.sleep(wait); continue
        raise RuntimeError(f"{method} {url.split('?')[0]} -> HTTP {r.status_code}: {r.text[:300]}")
    raise RuntimeError("unreachable")


def upload(png, key, raw_dir):
    """Upload one page image through an upload grant; returns the workspace_file source."""
    path = f"arabic-fin-bench/pages32/plain/{png.name}"
    g = call("POST", f"{BASE}/v1/documents/upload-grants", key, json={"path": path, "ttl_seconds": 3600}).json()
    with png.open("rb") as fh:
        r = requests.post(g["upload_url"], headers={"X-Upload-Token": g["token"]}, timeout=300,
                          files={"file": (png.name, fh, "image/png"),
                                 "metadata": (None, json.dumps({"path": path}), "application/json")})
    if r.status_code >= 400:
        raise RuntimeError(f"upload -> HTTP {r.status_code}: {r.text[:300]}")
    j = r.json()
    (raw_dir / f"{png.stem}.upload.json").write_text(json.dumps(j, ensure_ascii=False))
    f = (j.get("result") or {}).get("file") or j.get("file")
    while not f and j.get("job_id") and j.get("status") not in FINAL:       # an upload reported as a running job
        time.sleep(2)
        j = call("GET", f"{BASE}/v1/documents/jobs/{j['job_id']}", key).json()
        f = (j.get("result") or {}).get("file")
    if not f:
        raise RuntimeError(f"upload response carries no file: {json.dumps(j)[:300]}")
    return {"type": "workspace_file", "workspace_id": f.get("workspace_id") or g.get("workspace_id"), "file_id": f["file_id"]}


def parse(source, mode, stem, key):
    body = {"source": source, "parse_mode": mode,
            "output": {"formats": ["markdown", "blocks"], "table_format": "html", "include_page_markers": False}}
    return call("POST", f"{BASE}/v1/documents/parse", key, params={"wait_seconds": 60},
                headers={"Idempotency-Key": f"arabic-fin-bench-{mode}-{stem}"}, json=body).json()


def wait(job, key, poll=5):
    while job.get("status") not in FINAL:
        time.sleep(poll)
        job = call("GET", f"{BASE}/v1/documents/jobs/{job['job_id']}", key).json()
    return job


def markdown_of(job, key):
    doc = ((job.get("result") or {}).get("document") or {})
    md = doc.get("markdown") or ""
    url = doc.get("content_url")
    if url and (not md or doc.get("markdown_truncated") or doc.get("preview")):
        r = call("GET", url if url.startswith("http") else BASE + url, key)
        md = r.text
    return md, doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True); ap.add_argument("--mode", default="low", choices=["low", "medium", "high"])
    ap.add_argument("--only", default=""); ap.add_argument("--conc", type=int, default=4)
    a = ap.parse_args()
    key = api_key()
    out = Path(a.out); raw = out / "_raw"; raw.mkdir(parents=True, exist_ok=True)
    pages = sorted(Path(os.environ.get("PAGES_DIR", "pages32/plain")).glob("*.png"))
    if a.only:
        keep = set(a.only.split(",")); pages = [p for p in pages if p.stem in keep]
    (out / "_meta.json").write_text(json.dumps({"model": "nace_parse", "backend": "nace.ai Perception /v1/documents/parse",
                                                 "parse_mode": a.mode, "output": "markdown, tables as html (service default)",
                                                 "date": time.strftime("%F")}, indent=1))
    jobs_f = out / "_jobs.json"
    jobs = json.loads(jobs_f.read_text()) if jobs_f.exists() else {}
    done = lambda p: (out / f"{p.stem}.md").exists() and (out / f"{p.stem}.md").stat().st_size > 0
    todo = [p for p in pages if not done(p)]
    print(f"[nace_{a.mode}] {len(pages)} pages, {len(todo)} to run", flush=True)

    def work(p):
        t0 = time.time()
        try:
            src = jobs.get(p.stem, {}).get("source") or upload(p, key, raw)
            jobs[p.stem] = {"source": src}
            job = parse(src, a.mode, p.stem, key)
            jobs[p.stem]["job_id"] = job["job_id"]
            jobs_f.write_text(json.dumps(jobs, indent=1))
            job = wait(job, key)
            md, doc = markdown_of(job, key)
            (raw / f"{p.stem}.json").write_text(json.dumps(job, ensure_ascii=False))
            (out / f"{p.stem}.md").write_text(md, encoding="utf-8")
            err = None if job["status"] == "succeeded" else json.dumps(job.get("error"))
        except Exception as e:
            md, doc, job, err = "", {}, {}, str(e)
            (out / f"{p.stem}.md").write_text("", encoding="utf-8")
        if err:
            (out / "_errors.log").open("a").write(f"\n===== {p.name}\n{err}\n")
        rec = {"page": p.stem, "secs": round(time.time() - t0, 1), "chars": len(md), "error": bool(err),
               "job_id": job.get("job_id"), "status": job.get("status"), "credits": job.get("credits"),
               "usage_final": job.get("usage_final"), "ocr_applied": (job.get("result") or {}).get("ocr_applied"), "lane": (job.get("result") or {}).get("lane"),
               "parse_mode": a.mode}
        with (out / "_timing.jsonl").open("a") as f:
            f.write(json.dumps(rec) + "\n")
        print(f"[nace_{a.mode}] {p.name}: {rec['secs']}s, {len(md)} chars, {rec['credits']} credits, {rec['status']}"
              f"{'  ERROR ' + str(err)[:120] if err else ''}", flush=True)

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=a.conc) as ex:
        list(ex.map(work, todo))
    print(f"[nace_{a.mode}] DONE in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
