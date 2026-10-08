"""Self-consistency across N sampled readings of the same page: keep the medoid (the reading whose figure multiset
agrees most with the others). Usage: python consensus.py <out_dir> <dir1> <dir2> <dir3> ..."""
import sys, json, shutil
from pathlib import Path
from collections import Counter
sys.path.insert(0, "."); import eval2, post_dots
def figs(f):
    raw = f.read_text(errors="replace"); bl = post_dots.blocks_of(raw); text = post_dots.render(bl) if bl else raw
    return Counter(abs(v) for l in eval2.lines_of(eval2.extract_text(text)) for v in eval2.numbers(l) if abs(v) >= 1000 or v != int(v))
out = Path(sys.argv[1]); dirs = [Path(d) for d in sys.argv[2:]]; out.mkdir(parents=True, exist_ok=True); log = {}
for f in sorted(dirs[0].glob("*.md")):
    cands = [(d, d / f.name) for d in dirs if (d / f.name).exists()]
    F = [figs(p) for _, p in cands]
    score = [sum(sum((F[i] & F[j]).values()) for j in range(len(F)) if j != i) + 0.001 * sum(F[i].values()) for i in range(len(F))]
    best = max(range(len(F)), key=lambda i: score[i]); shutil.copy(cands[best][1], out / f.name)
    tj = cands[best][0] / (f.stem + ".tok.json")
    if tj.exists(): shutil.copy(tj, out / tj.name)
    log[f.stem] = dict(chosen=str(cands[best][0].name), agreement=[round(s) for s in score])
for extra in ("_timing.jsonl", "_meta.json"):
    if (dirs[0] / extra).exists(): shutil.copy(dirs[0] / extra, out / extra)
json.dump(log, open(out / "_consensus.json", "w"), indent=1); print({k: v["chosen"] for k, v in log.items()})
