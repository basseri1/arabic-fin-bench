"""GT-free structure-consistency retry for one results dir over pages32 (same ladder as pipeline.py:
T 0.2/0.4/0.6 with seeds 1-3; keep the first attempt without flags, else the one with most figures).
usage: python run32_retry.py <results_dir> <pages_dir> <model> [url]"""
import json, os, shutil, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, ".")
import structure_check
res, pdir, model = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
url = sys.argv[4] if len(sys.argv) > 4 else None
def take(src, dst):
    """Replace dst with src (keeping dst as .orig), with its token-probability file when there is one."""
    shutil.copy(dst, str(dst) + ".orig"); shutil.copy(src, dst)
    st, dt = src.with_name(src.stem + ".tok.json"), dst.with_name(dst.stem + ".tok.json")
    if st.exists(): shutil.copy(st, dt)
    elif dt.exists(): dt.unlink()
def one(f):
    pg = f.stem
    r0 = structure_check.check_text(structure_check.page_text(f))
    if not r0["flags"]: return None
    best = (r0["figures"], None); log = dict(page=pg, flags=r0["flags"], attempts=[])
    for seed, t in enumerate(("0.2", "0.4", "0.6"), 1):
        tp = Path("_tmp") / f"r32_{res.name}_{pg}"; tp.mkdir(parents=True, exist_ok=True); shutil.copy(pdir / f"{pg}.png", tp / f"{pg}.png")
        to = Path("_tmp") / f"r32o_{res.name}_{pg}_s{seed}"
        if to.exists(): shutil.rmtree(to)
        env = dict(os.environ, PAGES_DIR=str(tp), BENCH_TEMP=t, BENCH_SEED=str(seed), BENCH_CONC="1")
        cmd = [sys.executable, "bench_vllm.py", "--model", model, "--out", str(to)] + (["--url", url] if url else [])
        subprocess.run(cmd, env=env, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        g = to / f"{pg}.md"
        if not g.exists() or g.stat().st_size == 0: log["attempts"].append(dict(seed=seed, result="no output")); continue
        r = structure_check.check_text(structure_check.page_text(g)); log["attempts"].append(dict(seed=seed, flags=r["flags"], figures=r["figures"]))
        if not r["flags"]:
            take(g, f); log["chosen"] = seed; break
        if r["figures"] > best[0]: best = (r["figures"], g)
    else:
        if best[1] is not None: take(best[1], f); log["chosen"] = f"most figures ({best[0]})"
        else: log["chosen"] = "original kept"
    print(f"[retry] {pg}: {r0['flags']} -> {log.get('chosen')}", flush=True)
    return log
with ThreadPoolExecutor(max_workers=4) as ex:
    logs = [l for l in ex.map(one, sorted(res.glob("*.md"))) if l]
(res / "_retries.json").write_text(json.dumps(logs, ensure_ascii=False, indent=1))
print(f"retries: {len(logs)} flagged pages in {res}")
