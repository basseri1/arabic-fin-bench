"""Snapshot of the dots.mocr ablation progress -> progress.json (read by progress.html)."""
import json, re, time, os
from pathlib import Path
B = Path("."); PAGES = 6
R1 = ["dpi150_clahe", "gray", "clahe10", "clahe30", "clahe20_t16", "clahe_pad", "clahe_unsharp", "clahe_redfree_pad", "clahe_T0", "clahe_promptocr"]
R2 = ["inkfree", "crop_dots", "crop_surya", "crop_pp", "crop_fixed", "crop_dots_inkfree", "crop_pp_inkfree"]
scores = {}
for line in (B / "logs/abl_dots_summary.log").read_text().splitlines() if (B / "logs/abl_dots_summary.log").exists() else []:
    m = re.match(r"(\S+?)\s+rows\s+(\d+)/(\d+)\s+figs\s+(\d+)/(\d+)\s+\((\d+) min\)", line)
    if m: scores[m.group(1)] = dict(rows=int(m.group(2)), rows_tot=int(m.group(3)), figs=int(m.group(4)), figs_tot=int(m.group(5)), mins=int(m.group(6)))
def status(v):
    d = B / "results_abl" / f"dots_{v}"; n = len([f for f in d.glob("*.md") if f.stat().st_size > 100]) if d.exists() else 0
    st = "done" if v in scores else ("running" if n or (d.exists()) else "pending")
    cur = None
    if st == "running":
        log = B / f"logs/abl_dots_{v}.log"
        if log.exists():
            last = [l for l in log.read_text().splitlines() if "tok/s" in l]
            cur = last[-1][-60:] if last else None
        cur_page = None
        if d.exists():
            t = (d / "_timing.jsonl")
            started = max((f.stat().st_mtime for f in d.glob("*.md")), default=d.stat().st_mtime)
            cur_page = round(time.time() - started)
        return dict(name=v, status=st, pages=n, since=cur_page, last=cur)
    return dict(name=v, status=st, pages=PAGES if st == "done" else n, score=scores.get(v))
rounds = [dict(title="Stage A · image preparation & decoding choices (resolution, CLAHE strength, grayscale, padding, sharpening, T=0, prompt)", variants=[status(v) for v in R1]),
          dict(title="Stage B · page cleaning: signature/annotation ink removal, header/footer/signature crops (dots / surya / PP-DocLayout / fixed)", variants=[status(v) for v in R2])]
base = {k: scores.get(k) for k in ()}
# Stage B2: combinations (greedy forward selection + all-kept)
cb = B / "logs/combos.txt"
if cb.exists() and cb.read_text().strip():
    vs = []
    for label in cb.read_text().split():
        d = B / "results_abl" / ("dots_combo_" + label.replace("+", "_")); n = len([f for f in d.glob("*.md") if f.stat().st_size > 100]) if d.exists() else 0
        sc = scores.get("combo:" + label)
        vs.append(dict(name=label, status="done" if sc else ("running" if d.exists() else "pending"), pages=6 if sc else n, score=sc, since=None, last=None))
    rounds.append(dict(title="Stage B2 · combinations: greedy forward selection from the best single step, then everything kept at once", variants=vs))
# Stage C: full-validation pipeline runs (17 pages) for the kept candidates
cf = B / "logs/stage_c_candidates.txt"
if cf.exists():
    vs = []
    for prep in cf.read_text().split():
        d = B / "results_pipe" / f"dots_mocr_{prep}"; n = len([f for f in d.glob("*.md") if f.stat().st_size > 100]) if d.exists() else 0
        log = B / f"logs/pipe_dots_{prep}.log"; fin = log.exists() and "_bm_ver" in log.read_text()
        vs.append(dict(name=prep, status="done" if fin else ("running" if n else "pending"), pages=n, total=17, since=None, last=None, score=None))
    rounds.append(dict(title="Stage C · full validation: 17 pages (Aramco + Ma'aden + Drilling), band-merge + verification", variants=vs, total=17))
json.dump(dict(updated=time.strftime("%H:%M:%S"), baselines=dict(plain=130, clahe=173, clahe_redfree=174, rows_tot=175), rounds=rounds), open("progress.json", "w"))
