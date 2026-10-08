"""End-to-end run on all three documents: prepare pages -> OCR model -> (band-merge for dots) -> verification -> scores.
Usage: python3 pipeline.py --model dots_mocr --prep clahe [--tag name] [--layout-from results_enh/dots_mocr,results_drill/dots_mocr_clahe]"""
import argparse, os, subprocess, sys, json, shutil
from pathlib import Path
sys.path.insert(0, "."); import prep_lib, cv2
ap = argparse.ArgumentParser(); ap.add_argument("--model", required=True); ap.add_argument("--prep", default="clahe")
ap.add_argument("--tag", default=None); ap.add_argument("--layout-from", default="results_enh/dots_mocr,results_drill/dots_mocr_clahe")
ap.add_argument("--no-verify", action="store_true"); ap.add_argument("--env", default=""); ap.add_argument("--no-retry", action="store_true"); ap.add_argument("--max-retries", type=int, default=3); a = ap.parse_args()
B = Path("."); MLX = str(B / "venv_mlx/bin/python") if os.environ.get("BENCH_BACKEND", "mlx") == "mlx" else sys.executable
RUNNER = str(B / ("bench.py" if os.environ.get("BENCH_BACKEND", "mlx") == "mlx" else "bench_vllm.py")); tag = a.tag or f"{a.model}_{a.prep}" + ("" if not a.env else "_" + a.env.replace("=", "").replace(",", "_").replace("/", "").replace(".", "")[:30])
SRC = {"aramco": ("pages", [f"aramco_p{n}" for n in range(12, 17)]), "maaden": ("pages", [f"maaden_p{n}" for n in range(11, 17)]),
       "drilling": ("pages_drill", [f"drilling_p{n:02d}" for n in range(8, 14)])}
pdir = B / "pages_pipe" / a.prep; pdir.mkdir(parents=True, exist_ok=True)
for doc, (src, pages) in SRC.items():
    for pg in pages:
        out = pdir / f"{pg}.png"
        if out.exists(): continue
        lay = next((Path(d) / f"{pg}.md" for d in a.layout_from.split(",") if (Path(d) / f"{pg}.md").exists()), None)
        cv2.imwrite(str(out), prep_lib.prepare(B / src / f"{pg}.png", a.prep, lay))
res = B / "results_pipe" / tag
done = all((res / f"{pg}.md").exists() for _, pages in SRC.values() for pg in pages)
if not done:
    if res.exists(): shutil.rmtree(res)
    env = dict(os.environ, PAGES_DIR=str(pdir), TOKENIZERS_PARALLELISM="false", MLX_MEM_LIMIT_GB=os.environ.get("MLX_MEM_LIMIT_GB", "22"), **dict(kv.split("=", 1) for kv in a.env.split(",") if kv))
    subprocess.run([MLX, RUNNER, "--model", a.model, "--out", str(res)], env=env, check=False)
# structure-consistency check + retry with other sampling seeds (GT-free; catches dropped columns / lost structure)
import structure_check, shutil as _sh
def run_retries():
    retries = []
    for doc, (src, pages) in SRC.items():
        for pg in pages:
            f = res / f"{pg}.md"
            if not f.exists(): continue
            r0 = structure_check.check_text(structure_check.page_text(f))
            if not r0["flags"]: continue
            best = (r0["figures"], None); log = dict(page=pg, flags=r0["flags"], attempts=[])
            ladder = [{"BENCH_TEMP": t, "BENCH_SEED": str(i + 1)} for i, t in enumerate(("0.2", "0.4", "0.6"))][:a.max_retries]   # temperature ladder (datalab's retry recipe); works for greedy and sampled runs alike
            for seed, step in enumerate(ladder, 1):
                tp = B / "_tmp" / f"retry_{tag}_{pg}"; tp.mkdir(parents=True, exist_ok=True); _sh.copy(pdir / f"{pg}.png", tp / f"{pg}.png")
                to = B / "_tmp" / f"retry_out_{tag}_{pg}_s{seed}"
                env = dict(os.environ, PAGES_DIR=str(tp), TOKENIZERS_PARALLELISM="false", MLX_MEM_LIMIT_GB=os.environ.get("MLX_MEM_LIMIT_GB", "22"), **step, **dict(kv.split("=", 1) for kv in a.env.split(",") if kv))
                subprocess.run([MLX, RUNNER, "--model", a.model, "--out", str(to)], env=env, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                g = to / f"{pg}.md"
                if not g.exists(): log["attempts"].append(dict(seed=seed, result="no output")); continue
                r = structure_check.check_text(structure_check.page_text(g)); log["attempts"].append(dict(seed=seed, flags=r["flags"], figures=r["figures"]))
                if not r["flags"]:
                    _sh.copy(f, str(f) + ".orig"); _sh.copy(g, f); log["chosen"] = seed; break
                if r["figures"] > best[0]: best = (r["figures"], g)
            else:
                if best[1] is not None: _sh.copy(f, str(f) + ".orig"); _sh.copy(best[1], f); log["chosen"] = f"most figures ({best[0]})"
                else: log["chosen"] = "original kept"
            retries.append(log); print(f"[retry] {pg}: {r0['flags']} -> {log.get('chosen')}", flush=True)
    (res / "_retries.json").write_text(json.dumps(retries, ensure_ascii=False, indent=1))
    return retries
if not a.no_retry:
    run_retries()
final = res
if a.model.startswith("dots"):
    subprocess.run([sys.executable, "post_dots.py", str(res), str(res) + "_bm"], check=True); final = Path(str(res) + "_bm")
if not a.no_verify:
    ver = Path(str(final) + "_ver")
    for doc in SRC:
        subprocess.run([sys.executable, "validate.py", str(final), "--doc", doc, "--apply", str(ver)], check=False)
    final = ver
print(f"\n=== {tag}: scores (raw -> band-merged -> verified) ===", flush=True)
for d in [res, Path(str(res) + "_bm"), Path(str(res) + "_bm_ver")] if a.model.startswith("dots") else [res, Path(str(res) + "_ver")]:
    if d.exists():
        out = subprocess.run([sys.executable, "eval2.py", "--results", str(d.parent), "--per-table"], env=dict(os.environ, EVAL_DOCS="aramco,maaden,drilling"), capture_output=True, text=True).stdout
        print(f"--- {d.name}"); print("\n".join(l for l in out.splitlines() if l.startswith(d.name + " ") or l.startswith("model")))
