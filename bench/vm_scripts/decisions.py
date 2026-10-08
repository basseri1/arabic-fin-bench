"""Pipeline-decision table for dots.mocr: every candidate step with Ma'aden raw / band-merged scores, the three-company
Stage C validation (where run), cost, and the KEEP / DROP / neutral decision. Writes decisions.json + decisions.md."""
import re, json, subprocess, os, sys
from pathlib import Path
sys.path.insert(0, "."); import eval2, post_dots
B = Path("."); pages = [f"maaden_p{n}" for n in range(11, 17)]
GT = eval2.parse_gt(open("maaden_main_tables.md").read())
def bm_text(f):
    raw = f.read_text(errors="replace"); bl = post_dots.blocks_of(raw); return post_dots.render(bl) if bl else raw
def score(d, bm):
    R = F = 0
    for ti, tb in enumerate(GT, 1):
        fs = [Path(d) / f"{p}.md" for p in eval2.TABLE_PAGES["maaden"][ti]]
        if not all(f.exists() for f in fs): return None
        blob = "\n".join(eval2.truncate_loops("\n".join(eval2.lines_of(eval2.extract_text(bm_text(f) if bm else f.read_text(errors="replace")))))[0] for f in fs)
        c = eval2.score_tables([tb], blob); R += c["rows_hit"]; F += c["fig_hit"]
    return R, F
def secs(d):
    try: return sum(json.loads(l)["secs"] for l in open(Path(d) / "_timing.jsonl") if "maaden" in l) / 6
    except Exception: return None
CANDS = [  # name, results dir, stage, what it is
 ("CLAHE 2.0/8 (baseline)", "results_enh/dots_mocr", "base", "200 dpi gray + CLAHE clip 2, tile 8"),
 ("plain 200 dpi", "results/dots_mocr", "A", "no enhancement"),
 ("150 dpi + CLAHE", "results_abl/dots_dpi150_clahe", "A", "lower render resolution"),
 ("grayscale only", "results_abl/dots_gray", "A", "no CLAHE"),
 ("CLAHE clip 1.0", "results_abl/dots_clahe10", "A", "weaker contrast"),
 ("CLAHE clip 3.0", "results_abl/dots_clahe30", "A", "stronger contrast"),
 ("CLAHE tile 16", "results_abl/dots_clahe20_t16", "A", "larger tiles"),
 ("+ 60 px padding", "results_abl/dots_clahe_pad", "A", "white border"),
 ("+ unsharp", "results_abl/dots_clahe_unsharp", "A", "sharpening"),
 ("+ red-ink removal", "results_exp/dots_mocr_redfree", "A", "HSV mask + inpaint (red)"),
 ("+ red-ink removal + padding", "results_abl/dots_clahe_redfree_pad", "A", ""),
 ("T = 0 decoding", "results_abl/dots_clahe_T0", "A", "greedy instead of dots' T 0.1"),
 ("plain-text prompt", "results_abl/dots_clahe_promptocr", "A", "dots 'prompt_ocr' instead of layout/HTML"),
 ("+ blue+red ink removal", "results_abl/dots_inkfree", "B", "signature strokes inpainted"),
 ("crop: dots self-layout", "results_abl/dots_crop_dots", "B", "header/footer/signatures removed"),
 ("crop: PP-DocLayoutV2", "results_abl/dots_crop_pp", "B", ""),
 ("crop: surya layout2", "results_abl/dots_crop_surya", "B", "no table found on 3/6 pages"),
 ("crop: fixed margins", "results_abl/dots_crop_fixed", "B", "11% top / 14% bottom"),
 ("crop dots + ink removal", "results_abl/dots_crop_dots_inkfree", "B", ""),
 ("crop PP + ink removal", "results_abl/dots_crop_pp_inkfree", "B", ""),
 ("baseline, seed 1", "results_abl/dots_clahe_seed1", "noise", "repeatability"),
 ("baseline, seed 2", "results_abl/dots_clahe_seed2", "noise", "repeatability"),
]
for d in sorted(B.glob("results_abl/dots_combo_*")): CANDS.append((f"combo: {d.name[11:]}", str(d), "B2", "greedy combination"))
base_bm = score("results_enh/dots_mocr", True)
rows = []
for name, d, stage, note in CANDS:
    if not Path(d).exists(): continue
    raw, bm = score(d, False), score(d, True)
    if bm is None: continue
    delta = bm[0] - base_bm[0]; dfig = bm[1] - base_bm[1]
    dec = "baseline" if stage == "base" else "noise" if stage == "noise" else "KEEP" if (delta > 0 or (delta == 0 and dfig > 0)) else "neutral" if (delta == 0 and dfig == 0) else "DROP"
    rows.append(dict(step=name, stage=stage, note=note, raw_rows=raw[0], raw_figs=raw[1], bm_rows=bm[0], bm_figs=bm[1], delta_rows=delta, delta_figs=dfig, s_page=secs(d), decision=dec))
# Stage C (three companies) from results_pipe
stage_c = {}
if Path("results_pipe").exists():
    out = subprocess.run([sys.executable, "eval2.py", "--results", "results_pipe"], env=dict(os.environ, EVAL_DOCS="aramco,maaden,drilling"), capture_output=True, text=True).stdout
    for line in out.splitlines():
        m = re.match(r"(\S+)\s+(aramco|maaden|drilling)\s+(\d+)/(\d+)\s+\d+\s+([\d.]+)%\s+([\d.]+)%\s+([\d.]+)%", line)
        if m: stage_c.setdefault(m.group(1), {})[m.group(2)] = dict(pages=f"{m.group(3)}/{m.group(4)}", fig=float(m.group(5)), row=float(m.group(7)))
json.dump(dict(base_bm=base_bm, rows=rows, stage_c=stage_c), open("decisions.json", "w"), ensure_ascii=False, indent=1)
md = ["| step | stage | Ma'aden rows raw → band-merged (of 175) | figs (of 367) | Δ rows vs baseline | s/page | decision |", "|---|---|---|---|---|---|---|"]
for r in rows: md.append(f"| {r['step']} | {r['stage']} | {r['raw_rows']} → **{r['bm_rows']}** | {r['bm_figs']} | {r['delta_rows']:+d} | {r['s_page'] and round(r['s_page'])} | {r['decision']} |")
if stage_c:
    md += ["", "| Stage C configuration (17 pages) | Aramco rows | Ma'aden rows | Drilling rows |", "|---|---|---|---|"]
    for k, v in stage_c.items(): md.append(f"| {k} | {v.get('aramco',{}).get('row','–')} | {v.get('maaden',{}).get('row','–')} | {v.get('drilling',{}).get('row','–')} |")
Path("decisions.md").write_text("\n".join(md)); print("\n".join(md))
