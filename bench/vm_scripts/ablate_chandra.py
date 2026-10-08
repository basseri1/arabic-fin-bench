"""Chandra-2 pipeline-decision candidates on the Ma'aden scans (runs after Stage D). Existing runs (plain, CLAHE, CLAHE+2x,
red-free, column split) are reused; new: padding, dots-layout crop, PP-DocLayout crop, blue+red ink removal, red-free+pad."""
import sys, os, time, subprocess, json
from pathlib import Path
sys.path.insert(0, "."); import eval2, prep_lib, cv2
B = Path("."); MLX = str(B / "venv_mlx/bin/python"); pages = [f"maaden_p{n}" for n in range(11, 17)]
GT = eval2.parse_gt(open("maaden_main_tables.md").read())
def score(d):
    tot = {"rows_hit": 0, "rows_tot": 0, "fig_hit": 0, "fig_tot": 0}
    for ti, tb in enumerate(GT, 1):
        fs = [Path(d) / f"{p}.md" for p in eval2.TABLE_PAGES["maaden"][ti]]
        if not all(f.exists() for f in fs): return None
        blob = "\n".join(eval2.truncate_loops("\n".join(eval2.lines_of(eval2.extract_text(f.read_text(errors="replace")))))[0] for f in fs)
        c = eval2.score_tables([tb], blob)
        for k in tot: tot[k] += c[k]
    return tot
def run(name, prep):
    pdir = B / "pages_abl" / f"ch_{name}"; pdir.mkdir(parents=True, exist_ok=True)
    for pg in pages:
        out = pdir / f"{pg}.png"
        if not out.exists(): cv2.imwrite(str(out), prep_lib.prepare(B / "pages" / f"{pg}.png", prep, f"results_enh/dots_mocr/{pg}.md"))
    res = B / "results_abl" / f"chandra2_{name}"
    done = all((res / f"{pg}.md").exists() and (res / f"{pg}.md").stat().st_size > 100 for pg in pages)
    t0 = time.time()
    if not done:
        if res.exists(): import shutil; shutil.rmtree(res)
        e = dict(os.environ, PAGES_DIR=str(pdir), TOKENIZERS_PARALLELISM="false", MLX_MEM_LIMIT_GB="22")
        subprocess.run([MLX, "bench.py", "--model", "chandra2", "--out", str(res)], env=e, stdout=open(f"logs/abl_chandra_{name}.log", "a"), stderr=subprocess.STDOUT)
    t = score(res); line = f"chandra2 {name:<22} rows {t['rows_hit']:>3}/{t['rows_tot']}  figs {t['fig_hit']:>3}/{t['fig_tot']}  ({(time.time()-t0)/60:.0f} min)" if t else f"chandra2 {name}: scoring failed"
    print(line, flush=True); open("logs/abl_chandra_summary.log", "a").write(line + "\n")
while "STAGE D DONE" not in (Path("logs/stage_d.log").read_text() if Path("logs/stage_d.log").exists() else ""): time.sleep(90)
for name, d in (("plain", "results/chandra2"), ("clahe", "results_enh/chandra2"), ("clahe_2x", "results_enh2x/chandra2"), ("redfree", "results_exp/chandra2_redfree")):
    t = score(d); line = f"chandra2 {name:<22} rows {t['rows_hit']:>3}/{t['rows_tot']}  figs {t['fig_hit']:>3}/{t['fig_tot']}  (existing)"; print(line, flush=True); open("logs/abl_chandra_summary.log", "a").write(line + "\n")
for name, prep in (("clahe_pad", "clahe_pad"), ("crop_clahe", "crop_clahe"), ("croppp_clahe", "croppp_clahe"), ("inkfree_clahe", "inkfree_clahe"), ("redfree_clahe_pad", "redfree_clahe_pad"), ("plain_pad", "pad")):
    run(name, prep)
print("CHANDRA ABLATION DONE", flush=True)
