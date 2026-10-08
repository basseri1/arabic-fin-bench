"""Stage B2 (combinations, greedy forward selection on Ma'aden) then Stage C (full 3-document validation).
Steps that were >= the CLAHE baseline in Stage A/B are composable tokens (prep_lib) or env overrides (decoding/prompt)."""
import re, time, subprocess, sys, os, json
from pathlib import Path
sys.path.insert(0, "."); import eval2, prep_lib, cv2, post_dots
B = Path("."); MLX = str(B / "venv_mlx/bin/python"); pages = [f"maaden_p{n}" for n in range(11, 17)]
BASE_ROWS, BASE_FIGS = 173, 366
STEP = {"clahe_pad": dict(tok={"pad"}), "clahe_redfree_pad": dict(tok={"redfree", "pad"}), "inkfree": dict(tok={"inkfree"}),
        "crop_dots": dict(tok={"crop"}), "crop_pp": dict(tok={"croppp"}), "crop_surya": dict(tok={"cropsurya"}), "crop_fixed": dict(tok={"cropfixed"}),
        "crop_dots_inkfree": dict(tok={"crop", "inkfree"}), "crop_pp_inkfree": dict(tok={"croppp", "inkfree"}),
        "clahe_T0": dict(env={"BENCH_TEMP": "0.0"}), "clahe_promptocr": dict(env={"BENCH_PROMPT_FILE": "_tmp/prompt_ocr.txt"})}
CROPS = {"crop", "croppp", "cropsurya", "cropfixed"}; INK = {"inkfree", "redfree"}
def normalise(tok):
    tok = set(tok)
    if "inkfree" in tok: tok.discard("redfree")            # blue+red removal supersedes red-only
    crops = tok & CROPS
    if len(crops) > 1: raise ValueError("two crops")
    return tok
def prep_name(tok, env):
    order = ["crop", "croppp", "cropsurya", "cropfixed", "inkfree", "redfree", "clahe", "pad"]
    name = "_".join(t for t in order if t in (tok | {"clahe"}))
    return name, name + ("" if not env else "+" + "+".join(k.split("_")[-1] + v.replace("/", "").replace(".", "")[:6] for k, v in sorted(env.items())))
def bm_text(f):
    raw = f.read_text(errors="replace"); bl = post_dots.blocks_of(raw)
    return post_dots.render(bl) if bl else raw
def score(d):
    """Band-merge-aware score (band-merge is a kept pipeline step, so upstream steps are judged with it in place)."""
    GT = eval2.parse_gt(open("maaden_main_tables.md").read()); tot = {"rows_hit": 0, "rows_tot": 0, "fig_hit": 0, "fig_tot": 0}
    for ti, tb in enumerate(GT, 1):
        fs = [Path(d) / f"{p}.md" for p in eval2.TABLE_PAGES["maaden"][ti]]
        if not all(f.exists() for f in fs): return None
        blob = "\n".join(eval2.truncate_loops("\n".join(eval2.lines_of(eval2.extract_text(bm_text(f)))))[0] for f in fs)
        c = eval2.score_tables([tb], blob)
        for k in tot: tot[k] += c[k]
    return tot
def run_combo(tok, env):
    prep, label = prep_name(tok, env)
    pdir = B / "pages_abl" / ("combo_" + label.replace("+", "_")); pdir.mkdir(parents=True, exist_ok=True)
    for pg in pages:
        out = pdir / f"{pg}.png"
        if not out.exists(): cv2.imwrite(str(out), prep_lib.prepare(B / "pages" / f"{pg}.png", prep, f"results_enh/dots_mocr/{pg}.md"))
    res = B / "results_abl" / ("dots_combo_" + label.replace("+", "_"))
    done = all((res / f"{pg}.md").exists() and (res / f"{pg}.md").stat().st_size > 100 for pg in pages)
    t0 = time.time()
    if not done:
        if res.exists(): import shutil; shutil.rmtree(res)
        e = dict(os.environ, PAGES_DIR=str(pdir), TOKENIZERS_PARALLELISM="false", MLX_MEM_LIMIT_GB="22", **env)
        subprocess.run([MLX, "bench.py", "--model", "dots_mocr", "--out", str(res)], env=e, stdout=open(f"logs/abl_dots_combo_{label.replace('+','_')}.log", "a"), stderr=subprocess.STDOUT)
    s = score(res); mins = (time.time() - t0) / 60
    line = f"combo:{label:<44} rows {s['rows_hit']:>3}/{s['rows_tot']}  figs {s['fig_hit']:>3}/{s['fig_tot']}  ({mins:.0f} min)"
    print(line, flush=True); open("logs/abl_dots_summary.log", "a").write(line + "\n")
    return (s["rows_hit"], s["fig_hit"])
while "ABLATION2 DONE" not in Path("logs/abl_dots2.log").read_text(): time.sleep(60)
base = score("results_enh/dots_mocr"); BASE_ROWS, BASE_FIGS = base["rows_hit"], base["fig_hit"]
print(f"band-merged CLAHE baseline: {BASE_ROWS}/175 rows, {BASE_FIGS}/367 figs", flush=True)
scores = {}
for v in STEP:
    d = B / "results_abl" / f"dots_{v}"; sc = score(d) if d.exists() else None
    if sc: scores[v] = (sc["rows_hit"], sc["fig_hit"], 0); print(f"  bm {v:<20} {sc['rows_hit']}/175  {sc['fig_hit']}/367", flush=True)
open("logs/abl_dots_summary.log", "a").write("".join(f"bm:{v:<19} rows {r:>3}/175  figs {f:>3}/367  (0 min)\n" for v, (r, f, _) in scores.items()))
# repeatability of the baseline (same CLAHE pages, other sampling seeds) = the noise floor for all decisions
for seed in (1, 2):
    res = B / "results_abl" / f"dots_clahe_seed{seed}"
    if not all((res / f"{pg}.md").exists() for pg in pages):
        e = dict(os.environ, PAGES_DIR=str(B / "pages_enh_clahe"), TOKENIZERS_PARALLELISM="false", MLX_MEM_LIMIT_GB="22", BENCH_SEED=str(seed))
        subprocess.run([MLX, "bench.py", "--model", "dots_mocr", "--out", str(res)], env=e, stdout=open(f"logs/abl_dots_clahe_seed{seed}.log", "a"), stderr=subprocess.STDOUT)
    sc = score(res); line = f"clahe_seed{seed:<10} rows {sc['rows_hit']:>3}/175  figs {sc['fig_hit']:>3}/367  (7 min)"
    print(line, flush=True); open("logs/abl_dots_summary.log", "a").write(line + "\n")
kept = [v for v, (r, f, _) in scores.items() if v in STEP and (r > BASE_ROWS or (r == BASE_ROWS and f >= BASE_FIGS))]
kept.sort(key=lambda v: (-scores[v][0], -scores[v][1], scores[v][2]))
print("kept single steps (best first):", kept, flush=True)
Path("logs/combos.txt").write_text("")
tested = {}
def key(tok, env): return (frozenset(tok), tuple(sorted(env.items())))
def run_once(tok, env):
    k = key(tok, env)
    if k not in tested:
        Path("logs/combos.txt").write_text(Path("logs/combos.txt").read_text() + prep_name(tok, env)[1] + "\n")
        tested[k] = run_combo(tok, env)
    return tested[k]
if kept:
    best_v = kept[0]; cur_tok = normalise(STEP[best_v].get("tok", set())); cur_env = dict(STEP[best_v].get("env", {}))
    cur = (scores[best_v][0], scores[best_v][1]); tested[key(cur_tok, cur_env)] = cur
    print(f"start from {best_v}: {cur}", flush=True); trials = 0
    while trials < 8:                                        # greedy forward selection
        best_add = None
        for v in kept:
            tok = set(STEP[v].get("tok", set())); env = dict(STEP[v].get("env", {}))
            if tok <= cur_tok and all(cur_env.get(k) == x for k, x in env.items()): continue
            if (tok & CROPS) and (cur_tok & CROPS) and not (tok & CROPS <= cur_tok): continue   # two different crops
            try: ntok = normalise(cur_tok | tok)
            except ValueError: continue
            nenv = {**cur_env, **env}
            if key(ntok, nenv) in tested and tested[key(ntok, nenv)] is not None and trials: pass
            r = run_once(ntok, nenv); trials += 1
            if best_add is None or r > best_add[0]: best_add = (r, ntok, nenv)
            if trials >= 8: break
        if best_add and best_add[0] > cur: cur, cur_tok, cur_env = best_add; print(f"  -> improved to {cur} with {prep_name(cur_tok, cur_env)[1]}", flush=True)
        else: break
    # everything kept at once (best crop + ink removal + pad + env steps)
    all_tok, all_env = set(), {}
    for v in kept:
        tok = set(STEP[v].get("tok", set()))
        if (tok & CROPS) and (all_tok & CROPS): tok -= CROPS
        all_tok |= tok; all_env.update(STEP[v].get("env", {}))
    all_tok = normalise(all_tok); r_all = run_once(all_tok, all_env)
    final = [("baseline", "clahe", {}), ("best_single", prep_name(normalise(STEP[best_v].get("tok", set())), STEP[best_v].get("env", {}))[0], dict(STEP[best_v].get("env", {}))),
             ("best_combo", prep_name(cur_tok, cur_env)[0], dict(cur_env)), ("all_kept", prep_name(all_tok, all_env)[0], dict(all_env))]
else:
    final = [("baseline", "clahe", {})]
# Stage C: full 3-document validation for the distinct configurations
seen = set(); cands = []
for role, prep, env in final:
    k = (prep, tuple(sorted(env.items())))
    if k in seen: continue
    seen.add(k); cands.append((role, prep, env))
Path("logs/stage_c_candidates.txt").write_text("\n".join(p for _, p, _ in cands))
json.dump([dict(role=r, prep=p, env=e) for r, p, e in cands], open("logs/stage_c_config.json", "w"), indent=1)
print("Stage C configurations:", cands, flush=True)
for role, prep, env in cands:
    envs = ",".join(f"{k}={v}" for k, v in env.items())
    print(f"\n##### pipeline dots_mocr / {role}: {prep} {envs}  {time.strftime('%H:%M')}", flush=True)
    subprocess.run([sys.executable, "pipeline.py", "--model", "dots_mocr", "--prep", prep] + (["--env", envs] if envs else []), stdout=open(f"logs/pipe_dots_{prep}.log", "a"), stderr=subprocess.STDOUT)
    print(Path(f"logs/pipe_dots_{prep}.log").read_text()[-1800:], flush=True)
print("STAGE C DONE", flush=True)
