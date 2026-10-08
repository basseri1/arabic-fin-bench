"""Aggregate the 32-filing model runs into the results tables.

Reads bench/results32/<run>/ (outputs copied back from the VM) and bench/logs32/ (runner logs), scores every run with
tools/score.py against the ground truth (gt/ first, then drafts/), and writes bench/RESULTS.md +
bench/results_summary.json:
  1. main comparison, one row per system at its main setting, on the test split, the dev split and all 32 filings
     (mean ± sd over seeds where repeated; 95% bootstrap CI over filings, on seed-averaged statement scores)
  2. ablations: dots.mocr pipeline stages; Chandra input size and arithmetic verification
  3. row recall by statement-page format (all 32 filings)
  4. speed: pages per minute on one H100 with the model alone on the GPU, and median seconds per page
  5. run-to-run repeatability: the same configuration run twice
usage: python bench/analyze.py [--boot 2000]
"""
import argparse
import csv
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PAPER / "tools"))
import score  # noqa: E402

RESULTS = PAPER / "bench" / "results32"
LOGS = PAPER / "bench" / "logs32"
N_PAGES = 158
GPU, API, CPU = "self-hosted, 1×H100", "API", "self-hosted, CPU"
# system -> parameters (from the safetensors headers of the served checkpoints; vendor figure where no weights are public)
SYSTEMS = {
    "dots.mocr": "3.0B", "Chandra OCR 2": "5.3B", "Chandra OCR 1": "8.8B", "Nanonets-OCR2": "3.8B",
    "Qwen3-VL-32B (FP8)": "33.4B", "Nemotron Nano 12B VL": "13.2B", "Surya OCR 2": "0.7B", "Persian–Arabic line OCR": "2.1B",
    "PaddleOCR PP-OCRv5 Arabic": "–", "Mistral OCR": "–", "Qari-OCR v0.3": "2.2B", "PaddleOCR-VL-1.6": "0.96B", "Qwen3.6-27B": "27B",
    "Qwen3.8-27B": "27.8B", "ERNIE 4.5 VL": "424B (47B active)", "Command A Vision": "111.9B", "Cohere Parse": "2.3B",
    "LandingAI ADE": "–",
}
# configuration (run name without the seed) -> (system, how it was run, setting, table)
CONFIGS = {
    "dots_mocr_plain": ("dots.mocr", GPU, "out of the box (200 dpi page)", "main"),
    "dots_mocr_clahe_bm_ver": ("dots.mocr", GPU, "adopted pipeline: CLAHE, structure retry, band-merge, verification", "main"),
    "dots_mocr_plain_bm": ("dots.mocr", GPU, "200 dpi page + band-merge", "ablation"),
    "dots_mocr_clahe_raw": ("dots.mocr", GPU, "CLAHE contrast", "ablation"),
    "dots_mocr_clahe": ("dots.mocr", GPU, "CLAHE + structure retry", "ablation"),
    "dots_mocr_clahe_bm": ("dots.mocr", GPU, "CLAHE + structure retry + band-merge", "ablation"),
    "chandra2_chandra_cap": ("Chandra OCR 2", GPU, "own input size (≤ 6.3 MP)", "main"),
    "chandra2_chandra_cap_ver": ("Chandra OCR 2", GPU, "own input size + verification", "ablation"),
    "chandra2_plain": ("Chandra OCR 2", GPU, "200 dpi page", "ablation"),
    "chandra2_plain_ver": ("Chandra OCR 2", GPU, "200 dpi page + verification", "ablation"),
    "chandra1_chandra_cap": ("Chandra OCR 1", GPU, "own input size (≤ 6.3 MP)", "main"),
    "chandra1_plain": ("Chandra OCR 1", GPU, "200 dpi page", "ablation"),
    "nanonets_plain": ("Nanonets-OCR2", GPU, "200 dpi page, vendor prompt", "main"),
    "qwen3vl_32b_plain": ("Qwen3-VL-32B (FP8)", GPU, "200 dpi page, generic prompt", "main"),
    "qwen38_27b_local_plain": ("Qwen3.8-27B", GPU, "200 dpi page, generic prompt, reasoning off (official BF16 weights)", "main"),
    "nemotron12b_vl_plain": ("Nemotron Nano 12B VL", GPU, "200 dpi page, generic prompt", "main"),
    "qari03_plain": ("Qari-OCR v0.3", GPU, "200 dpi page, vendor prompt", "main"),
    "paddleocr_vl16_plain": ("PaddleOCR-VL-1.6", GPU, "vendor pipeline: layout detection + VLM (vLLM)", "main"),
    "surya2_plain": ("Surya OCR 2", GPU, "200 dpi page, vendor pipeline", "main"),
    "persar2b_plain": ("Persian–Arabic line OCR", GPU, "PaddleOCR line boxes, one crop per line", "main"),
    "paddle_ar_plain": ("PaddleOCR PP-OCRv5 Arabic", CPU, "classical detection + recognition", "main"),
    "mistral_ocr_plain": ("Mistral OCR", API, "200 dpi page", "main"),
    "cohere_parse_plain": ("Cohere Parse", API, "200 dpi page, parse-v5.0, markdown output", "main"),
    "landingai_ade_plain": ("LandingAI ADE", API, "200 dpi page, DPT-3 Pro (dpt-3-pro-20260710), Parse Jobs, standard tier", "main"),
    "qwen36_27b_plain": ("Qwen3.6-27B", API, "200 dpi page, generic prompt, reasoning off", "main"),
    "qwen38_27b_plain": ("Qwen3.8-27B", API, "200 dpi page, generic prompt, reasoning off", "main"),
    "ernie45_vl_plain": ("ERNIE 4.5 VL", API, "200 dpi page, generic prompt", "main"),
    "cmda_vision_plain": ("Command A Vision", API, "200 dpi page, generic prompt", "main"),
}
SAME_WEIGHTS = [("qwen38_27b_plain", "qwen38_27b_local_plain")]      # (API run, self-hosted run) of the same model
ABLATION_ORDER = ["dots_mocr_plain", "dots_mocr_plain_bm", "dots_mocr_clahe_raw", "dots_mocr_clahe", "dots_mocr_clahe_bm",
                  "dots_mocr_clahe_bm_ver", "chandra2_plain", "chandra2_plain_ver", "chandra2_chandra_cap",
                  "chandra2_chandra_cap_ver", "chandra1_plain", "chandra1_chandra_cap"]
# speed: runs where the model had the GPU (or CPU) to itself -> (configuration, requests in flight)
SPEED = [  # (results dir, configuration, requests in flight, key in _solo/_wall.jsonl)
    ("_solo/dots_mocr_plain_s0", "dots_mocr_plain", "16", "dots_mocr_plain"),
    ("_solo/dots_mocr_clahe_s0_bm_ver", "dots_mocr_clahe_bm_ver", "16 (+ retries)", "dots_mocr_clahe_bm_ver"),
    ("_solo/chandra2_chandra_cap", "chandra2_chandra_cap", "16", "chandra2_chandra_cap"),
    ("chandra1_chandra_cap", "chandra1_chandra_cap", "16", "chandra1_chandra_cap"),
    ("nanonets_plain", "nanonets_plain", "16", None), ("qwen3vl_32b_plain", "qwen3vl_32b_plain", "16", None),
    ("nemotron12b_vl_plain", "nemotron12b_vl_plain", "16", None),
    ("qwen38_27b_local_plain", "qwen38_27b_local_plain", "16", "qwen38_27b_local_plain"),
    ("qari03_plain", "qari03_plain", "16", "qari03_plain"),
    ("paddleocr_vl16_plain", "paddleocr_vl16_plain", "pipeline, 16 VLM requests in flight", "paddleocr_vl16_plain"),
    ("surya2_plain", "surya2_plain", "1 page at a time", None),
    ("persar2b_plain", "persar2b_plain", "32 lines at a time (line boxes from the PaddleOCR run, not timed here)", None), ("paddle_ar_plain", "paddle_ar_plain", "4 processes", None)]
REPEAT = [("_solo/dots_mocr_plain_s0", "dots_mocr_plain_s0"), ("_solo/dots_mocr_clahe_s0_bm_ver", "dots_mocr_clahe_s0_bm_ver"),
          ("_solo/chandra2_chandra_cap", "chandra2_chandra_cap")]
FORMAT = [("garbled", "text layer"), ("Images inside digital PDF", "images in a digital PDF"),
          ("Fully scanned", "fully scanned"), ("Text", "text layer")]      # order matters: first match wins


def fmt_of(s):
    for k, v in FORMAT:
        if k.lower() in s.lower():
            return v
    return s


def config_of(run):
    """dots_mocr_clahe_s1_bm_ver -> ('dots_mocr_clahe_bm_ver', 1); chandra2_plain -> ('chandra2_plain', None)."""
    m = re.match(r"(.+?)_s(\d+)(_.*)?$", run)
    return (m.group(1) + (m.group(3) or ""), int(m.group(2))) if m else (run, None)


def complete(d):
    """All 158 pages attempted and no request failed on its last attempt. An empty page is kept: it is what the model
    returned (e.g. an immediate end-of-sequence), and it scores zero."""
    if not d.is_dir() or len(list(d.glob("*.md"))) < N_PAGES:
        return False
    f = d / "_timing.jsonl"
    last = {}
    if f.exists():
        for l in f.read_text().splitlines():
            if l.strip():
                r = json.loads(l); last[r["page"]] = r
    return not any(r.get("error") for r in last.values())


def latencies(d):
    f = d / "_timing.jsonl"
    if not f.exists():
        return []
    recs = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
    # last attempt per page (hosted reruns append); in batched runs a page returns when its whole batch does
    last = {r["page"]: r.get("batch_secs", r["secs"]) for r in recs if isinstance(r.get("secs"), (int, float)) and not r.get("error")}
    return list(last.values())


def wall_secs(run, key=None):
    """Wall-clock seconds for all 158 pages: phase 3's own log (key), else the runner's 'DONE in', else the sum of
    per-page times for runners that send one page at a time, else the span of output times (parallel CPU workers)."""
    solo = RESULTS / "_solo" / "_wall.jsonl"
    if key and solo.exists():
        for l in solo.read_text().splitlines():
            if l.strip() and json.loads(l)["run"] == key:
                return json.loads(l)["secs"]
        return None
    log = LOGS / f"run32_{run}.log"
    if log.exists():
        m = re.findall(r"DONE in (\d+)s", log.read_text(errors="replace"))
        if m:
            return int(m[-1])
    d = RESULTS / run
    if run in ("surya2_plain", "persar2b_plain"):
        return sum(latencies(d)) or None
    ts = [p.stat().st_mtime for p in d.glob("*.md")]
    return max(ts) - min(ts) + statistics.median(latencies(d) or [0]) if ts else None


def page_text(path):
    """The text the scorer sees (layout JSON and HTML reduced to lines), so bounding-box jitter does not count."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    return "\n".join(score.E.lines_of(score.E.extract_text(raw)))


def combine(per_stmts):
    """Seed-average per-statement hits (statements are the same across seeds)."""
    acc = defaultdict(list)
    for ps in per_stmts:
        for s in ps:
            acc[(s["filing"], s["statement"])].append(s)
    return [{"filing": k[0], "rows_hit": statistics.mean(x["rows_hit"] for x in v), "rows_tot": v[0]["rows_tot"]} for k, v in acc.items()]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--boot", type=int, default=2000); a = ap.parse_args()
    inv = {r["filing_id"]: r for r in csv.DictReader(open(PAPER / "dataset_inventory.csv", encoding="utf-8-sig"))}
    gts = {sp: score.load_gt(f"{PAPER / 'gt'},{PAPER / 'drafts'}", sp) for sp in ("test", "dev", None)}
    runs = sorted(p for p in RESULTS.iterdir() if complete(p) and config_of(p.name)[0] in CONFIGS)
    skipped = sorted(p.name for p in RESULTS.iterdir() if p.is_dir() and not p.name.startswith("_") and p not in runs
                     and "_lp" not in p.name)          # token-probability re-runs feed CONFIDENCE.md, not these tables
    per_run = {}
    for rd in runs + [RESULTS / r for r, _ in REPEAT if complete(RESULTS / r) and r.startswith("_solo")]:
        name = str(rd.relative_to(RESULTS))
        rec = {"median_secs_page": statistics.median(latencies(rd)) if latencies(rd) else None}
        for sp, gt in gts.items():
            total, per_stmt, per_filing = score.score_model(rd, gt)
            if total:
                m = score.metrics(total); m["per_stmt"] = per_stmt
                m["per_filing"] = {k: score.metrics(v) | {"rows": v["rows_tot"]} for k, v in per_filing.items()}
                rec[sp or "all"] = m
        per_run[name] = rec
        print(f"scored {name}", flush=True)
    configs = defaultdict(dict)
    for run, rec in per_run.items():
        if not run.startswith("_solo"):
            cfg, seed = config_of(run); configs[cfg][seed] = rec
    pct = lambda x: f"{100 * x:.1f}%"

    def row_for(cfg, split):
        vals = [r[split] for r in configs[cfg].values() if split in r]
        if not vals:
            return None
        rr = [v["row_recall"] for v in vals]
        system, how, setting, table = CONFIGS[cfg]; params = SYSTEMS[system]
        secs = [r["median_secs_page"] for r in configs[cfg].values() if r["median_secs_page"]]
        return dict(config=cfg, system=system, params=params, how=how, setting=setting, table=table, runs=len(rr),
                    row=statistics.mean(rr), sd=statistics.stdev(rr) if len(rr) > 1 else None,
                    ci=score.bootstrap_filings(combine([v["per_stmt"] for v in vals]), a.boot),
                    fig=statistics.mean(v["fig_recall"] for v in vals), sign=statistics.mean(v["fig_sgn"] for v in vals),
                    label=statistics.mean(v["label_recall"] for v in vals), prec=statistics.mean(v["num_prec"] for v in vals),
                    secs=statistics.median(secs) if secs else None)

    def recall_cell(r):
        return pct(r["row"]) + (f" ± {100 * r['sd']:.1f}" if r["sd"] is not None else "")

    out = ["# Results on the 32-filing benchmark", "",
           "Every run was made from the same NVIDIA H100 virtual machine: open models served there with vLLM, or "
           "Transformers where vLLM has no support (one model on the GPU at a time, except the first batch where "
           "dots.mocr and Chandra OCR 2 shared it; their speed comes from solo re-runs), hosted APIs called from it, "
           "PaddleOCR on its CPU. See the notes at the end. Ground truth: all 32 filings in gt/ (transcribed by hand "
           "by the first author from the page images, without OCR or AI tools, the 3 pilot filings first; checked "
           "arithmetically and verified cell by cell by the first author).", "",
           "**Row recall** (primary): share of ground-truth table rows whose every figure appears on one output line. "
           "**Figures**: share of figures found; **Signs**: found with the right sign; **Labels**: rows whose Arabic "
           "label is found; **Precision**: share of output numbers that are in the ground truth. dots.mocr ran with 3 "
           "seeds (temperature 0.1; mean ± sd); every other system ran once with greedy decoding. 95% CI: bootstrap over "
           "filings (all statements of a resampled filing together).", ""]
    summary = {}
    for split, title in (("test", "Test split (22 filings, held out)"), ("dev", "Development split (10 filings)"),
                         ("all", "All 32 filings")):
        rows = [r for r in (row_for(c, split) for c in configs) if r]
        summary[split] = rows
        main_rows = sorted((r for r in rows if r["table"] == "main"), key=lambda r: -r["row"])
        out += [f"## {title}", "",
                "| # | System | Params | Run | Setting | Runs | Row recall | 95% CI | Figures | Signs | Labels | Precision |",
                "|---:|---|---|---|---|---:|---:|---|---:|---:|---:|---:|"]
        for i, r in enumerate(main_rows, 1):
            out.append(f"| {i} | {r['system']} | {r['params']} | {r['how']} | {r['setting']} | {r['runs']} | "
                       f"{recall_cell(r)} | {pct(r['ci'][0])}–{pct(r['ci'][1])} | {pct(r['fig'])} | {pct(r['sign'])} | "
                       f"{pct(r['label'])} | {pct(r['prec'])} |")
        out.append("")
    # ablations
    by_cfg = {r["config"]: r for r in summary["all"]}
    by_cfg_test = {r["config"]: r for r in summary["test"]}
    out += ["## Ablations (all 32 filings; test split in the last column)", "",
            "| System | Setting | Runs | Row recall (32 filings) | 95% CI | Figures | Row recall (test) |",
            "|---|---|---:|---:|---|---:|---:|"]
    for cfg in ABLATION_ORDER:
        if cfg in by_cfg:
            r, t = by_cfg[cfg], by_cfg_test.get(cfg)
            out.append(f"| {r['system']} | {r['setting']} | {r['runs']} | {recall_cell(r)} | "
                       f"{pct(r['ci'][0])}–{pct(r['ci'][1])} | {pct(r['fig'])} | {recall_cell(t) if t else '–'} |")
    out.append("")
    # by statement-page format, main settings, seed-averaged
    strata = sorted({fmt_of(r["statement_pages_format"]) for r in inv.values()}); by_format = {}
    out += ["## Row recall by statement-page format (all 32 filings)", "",
            "| System | Setting | " + " | ".join(strata) + " |", "|---|---|" + "---:|" * len(strata)]
    for r in sorted((r for r in summary["all"] if r["table"] == "main"), key=lambda r: -r["row"]):
        cells = []
        for s in strata:
            hit = tot = 0
            for rec in configs[r["config"]].values():
                pf = rec["all"]["per_filing"]
                for f, m in pf.items():
                    if fmt_of(inv[f]["statement_pages_format"]) == s:
                        hit += m["row_recall"] * m["rows"]; tot += m["rows"]
            cells.append(pct(hit / tot) if tot else "–")
            by_format.setdefault(r["config"], {})[s] = hit / tot if tot else None
        out.append(f"| {r['system']} | {r['setting']} | " + " | ".join(cells) + " |")
    out += ["", "Filings per format: " + ", ".join(
        f"{s} {sum(1 for v in inv.values() if fmt_of(v['statement_pages_format']) == s)}" for s in strata), ""]
    # speed
    out += ["## Speed", "",
            "Self-hosted systems: wall-clock time for all 158 statement pages with the model alone on the H100 "
            "(server start-up excluded). Median seconds per page is the time from sending a page to receiving its "
            "full output, with the stated number of requests in flight; for APIs it depends on the provider's load.", "",
            "| System | Setting | Requests in flight | Wall-clock (158 pages) | Pages per minute | Median s/page |",
            "|---|---|---|---:|---:|---:|"]
    speed = []
    for run, cfg, conc, key in SPEED:
        d = RESULTS / run
        if not complete(d):
            continue
        w = wall_secs(run, key); lat = latencies(d)
        system, _, setting, _ = CONFIGS[cfg]
        speed.append(dict(run=run, system=system, setting=setting, conc=conc, wall=w, ppm=N_PAGES / w * 60 if w else None,
                          median=statistics.median(lat) if lat else None))
        out.append(f"| {system} | {setting} | {conc} | {w / 60:.1f} min | {N_PAGES / w * 60:.1f} | "
                   f"{statistics.median(lat):.1f} |" if w and lat else f"| {system} | {setting} | {conc} | – | – | – |")
    for cfg in [c for c, v in CONFIGS.items() if v[1] == API]:
        d = RESULTS / cfg
        if complete(d) and latencies(d):
            system, _, setting, _ = CONFIGS[cfg]
            out.append(f"| {system} | {setting} | API, one page per request | – | – | {statistics.median(latencies(d)):.1f} |")
    out.append("")
    # repeatability
    rep = []
    for solo, first in REPEAT:
        a_dir, b_dir = RESULTS / solo, RESULTS / first
        if not (complete(a_dir) and complete(b_dir)) or solo not in per_run or first not in per_run:
            continue
        same = sum(1 for p in b_dir.glob("*.md") if (a_dir / p.name).exists() and page_text(a_dir / p.name) == page_text(p))
        ra, rb = per_run[solo]["all"]["row_recall"], per_run[first]["all"]["row_recall"]
        rep.append(dict(config=config_of(first)[0], identical=same, row_first=rb, row_second=ra))
    if rep:
        out += ["## Run-to-run repeatability", "",
                "The same configuration run a second time on the same VM, alone on the GPU and with 16 requests in flight "
                "instead of 6–8 (same seed and temperature).", "",
                "| System | Setting | Pages with identical text | Row recall, first run | Row recall, second run |",
                "|---|---|---:|---:|---:|"]
        for r in rep:
            system, _, setting, _ = CONFIGS[r["config"]]
            out.append(f"| {system} | {setting} | {r['identical']} of {N_PAGES} | {pct(r['row_first'])} | {pct(r['row_second'])} |")
        out.append("")
    # API routing: which companies processed the pages (OpenRouter spreads one model name over several providers)
    routing = []
    for cfg, (system, how, setting, _) in CONFIGS.items():
        d = RESULTS / cfg
        if how != API or not complete(d):
            continue
        meta = json.loads((d / "_meta.json").read_text()) if (d / "_meta.json").exists() else {}
        backend = str(meta.get("backend", ""))
        prov = Counter()
        for f in (d / "_raw").glob("*.json") if (d / "_raw").exists() else []:
            try:
                prov[json.loads(f.read_text()).get("provider") or ""] += 1
            except Exception:
                pass
        prov.pop("", None)
        if prov:
            route = "OpenRouter"
        else:
            route = "vendor API"
            prov = Counter({"Mistral AI" if "mistral" in backend.lower() else "Cohere" if "cohere" in backend.lower()
                            else "LandingAI" if "landingai" in backend.lower() else "?": N_PAGES})
        routing.append(dict(system=system, route=route, n=len(prov), providers=dict(prov.most_common())))
    if routing:
        out += ["## API routing", "",
                "Which companies processed the 158 page images of each API run. Through OpenRouter one model name is "
                "served by several providers, each with its own serving stack and possibly its own quantisation.", "",
                "| System | Route | Providers | Pages per provider |", "|---|---|---:|---|"]
        for r in sorted(routing, key=lambda r: -r["n"]):
            out.append(f"| {r['system']} | {r['route']} | {r['n']} | " + ", ".join(f"{k} {v}" for k, v in r["providers"].items()) + " |")
        out.append("")
    # row recall by provider, for OpenRouter runs spread over several providers. Each statement is scored on its own
    # pages only, and only when all of them went to one provider. OpenRouter chose the provider per page, so each
    # provider saw different statements: indicative, not a controlled comparison.
    by_provider = {}
    gt_all = gts[None]
    for r in routing:
        if r["route"] != "OpenRouter" or r["n"] < 2:
            continue
        cfg = next(c for c, v in CONFIGS.items() if v[0] == r["system"] and v[1] == API)
        d = RESULTS / cfg
        prov = {f.stem: json.loads(f.read_text()).get("provider") for f in (d / "_raw").glob("*.json")}
        texts = score.page_texts(d)
        agg = defaultdict(lambda: [0, 0, 0])
        for fid, gt in gt_all.items():
            for st, tb in zip(gt["statements"], score.gtlib.to_eval_tables(gt)):
                pages = [f"{fid}_p{p:02d}" for p in st["pages"]]
                ps = {prov.get(p) for p in pages}
                if len(ps) != 1 or None in ps or not all(p in texts for p in pages):
                    continue
                c = score.E.score_tables([tb], "\n".join(texts[p] for p in pages))
                a = agg[ps.pop()]; a[0] += c["rows_hit"]; a[1] += c["rows_tot"]; a[2] += 1
        by_provider[r["system"]] = {k: dict(statements=n, rows=t, row_recall=h / t) for k, (h, t, n) in agg.items() if t}
    if by_provider:
        out += ["Row recall by provider (each statement scored on its own pages, when all of them went to one provider; "
                "each provider saw different statements, so this is indicative only):", "",
                "| System | Provider | Statements | Rows | Row recall |", "|---|---|---:|---:|---:|"]
        for system, provs in by_provider.items():
            for k, v in sorted(provs.items(), key=lambda kv: -kv[1]["rows"]):
                out.append(f"| {system} | {k} | {v['statements']} | {v['rows']} | {pct(v['row_recall'])} |")
        out += ["", "A controlled test that sends the same statements to named providers (fallbacks off) is in `PROVIDERS.md`.", ""]
    # same weights: API against self-hosted
    same = []
    for api_cfg, local_cfg in SAME_WEIGHTS:
        if api_cfg in per_run and local_cfg in per_run:
            ra, rl = per_run[api_cfg], per_run[local_cfg]
            same.append(dict(system=CONFIGS[api_cfg][0], api=ra["all"]["row_recall"], local=rl["all"]["row_recall"],
                             api_test=ra.get("test", {}).get("row_recall"), local_test=rl.get("test", {}).get("row_recall"),
                             api_fig=ra["all"]["fig_recall"], local_fig=rl["all"]["fig_recall"]))
    if same:
        out += ["## Same weights: API against self-hosted", "",
                "The same open-weight model called through a hosted API and served on the VM from the official "
                "checkpoint (same prompt, greedy decoding, reasoning off).", "",
                "| System | Row recall, API (32 filings) | Row recall, self-hosted (32 filings) | API (test) | Self-hosted (test) | "
                "Figures, API | Figures, self-hosted |", "|---|---:|---:|---:|---:|---:|---:|"]
        for r in same:
            t = lambda x: pct(x) if x is not None else "–"
            out.append(f"| {r['system']} | {pct(r['api'])} | {pct(r['local'])} | {t(r['api_test'])} | {t(r['local_test'])} | "
                       f"{pct(r['api_fig'])} | {pct(r['local_fig'])} |")
        out.append("")
    out += ["## Notes on the runs", "",
            "- **Serving stack.** vLLM 0.27.1 for dots.mocr, Qwen3-VL-32B, Qwen3.8-27B, Nemotron and the Persian–Arabic line "
            "model, Qari-OCR v0.3 and PaddleOCR-VL-1.6 (whose vendor pipeline, PaddleOCR 3.7 on PaddlePaddle 3.2.1, runs layout "
            "detection and sends each block to the model on the vLLM server); the vLLM 0.17 container for Chandra OCR 1 and 2 "
            "(FlashInfer attention) and Nanonets-OCR2; the vendor's vLLM 0.20.1 recipe for Surya OCR 2.",
            "- **Nanonets-OCR2 under vLLM 0.27.1** returned only '!!!!' (NaN logits) on every page; the same checkpoint in "
            "the vLLM 0.17 container read normally. The failed run is kept in `results32/_broken/`.",
            "- **Qwen3.8-27B self-hosted** needed `--max-num-seqs 64`: vLLM's default of 1024 exceeds the 301 Mamba-cache "
            "blocks this hybrid-attention model gets on one H100, and the server refused to start.",
            "- **Qari-OCR v0.3 and PaddleOCR-VL-1.6** were added on 2 Oct 2026 on the same VM, each alone on the GPU, with the "
            "checkpoint revisions in `CHECKPOINTS.md`. Qari-OCR v0.3 stopped on the loop rule on 102 of 158 pages. "
            "PaddleOCR-VL-1.6's pipeline returns all pages of a batch together, so its median seconds per page is not given.",
            "- **North Micro Vision Instruct** was evaluated and then dropped from the evaluation; its outputs, including a re-run "
            "with the tokenizer fix of its checkpoint (revision fa548d9, 2 Oct 2026, still 0.0% row recall), stay in "
            "`results32/north_micro_*`.",
            "- **Nemotron Nano 12B VL** tiles a page into at most 12 tiles of 512 px (6 plus a thumbnail for these pages), "
            "about 130 dpi effective; its failures are content invented at that resolution, not missing images.",
            "- **Surya OCR 2** ran through the vendor's page-by-page pipeline, so its speed is not comparable with the "
            "16-requests-in-flight rows.",
            "- **Decoding.** Greedy for every system except dots.mocr (temperature 0.1, vendor setting; 3 seeds). Reasoning "
            "was switched off for the Qwen models.",
            ""]
    if skipped:
        out += [f"Runs not scored (incomplete or not in the configuration list): {', '.join(skipped)}", ""]
    (PAPER / "bench" / "RESULTS.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    for rec in per_run.values():                  # keep the summary small: drop per-statement lists
        for sp in ("test", "dev", "all"):
            rec.get(sp, {}).pop("per_stmt", None)
    (PAPER / "bench" / "results_summary.json").write_text(json.dumps(
        {"runs": per_run, "tables": summary, "speed": speed, "repeatability": rep, "same_weights": same, "routing": routing, "by_provider": by_provider, "by_format": by_format}, ensure_ascii=False, indent=1, default=str))
    print("\n".join(out))


if __name__ == "__main__":
    main()
