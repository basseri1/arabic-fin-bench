"""Stage C: after Stage A/B finish, run every candidate that was >= the CLAHE baseline on Ma'aden through the full
pipeline on all three documents (17 pages) with band-merge + verification, plus the CLAHE baseline itself."""
import re, time, subprocess, sys
from pathlib import Path
MAP = {"clahe30": None, "clahe20_t16": None, "clahe_pad": "clahe_pad", "clahe_redfree_pad": "redfree_clahe_pad", "clahe_T0": None, "clahe_promptocr": None,
       "inkfree": "inkfree_clahe", "crop_dots": "crop_clahe", "crop_surya": "cropsurya_clahe", "crop_pp": "croppp_clahe", "crop_fixed": "cropfixed_clahe",
       "crop_dots_inkfree": "crop_inkfree_clahe", "crop_pp_inkfree": "croppp_inkfree_clahe"}
while "ABLATION2 DONE" not in Path("logs/abl_dots2.log").read_text(): time.sleep(60)
scores = {}
for line in Path("logs/abl_dots_summary.log").read_text().splitlines():
    m = re.match(r"(\S+)\s+rows\s+(\d+)/\d+\s+figs\s+(\d+)/", line)
    if m: scores[m.group(1)] = (int(m.group(2)), int(m.group(3)))
cands = ["clahe"] + [MAP[v] for v, (r, f) in scores.items() if v in MAP and MAP[v] and (r > 173 or (r == 173 and f >= 366))]
cands = list(dict.fromkeys(cands)); print("Stage C candidates:", cands, flush=True)
Path("logs/stage_c_candidates.txt").write_text("\n".join(cands))
for prep in cands:
    print(f"\n##### pipeline dots_mocr / {prep}  {time.strftime('%H:%M')}", flush=True)
    subprocess.run([sys.executable, "pipeline.py", "--model", "dots_mocr", "--prep", prep], stdout=open(f"logs/pipe_dots_{prep}.log", "a"), stderr=subprocess.STDOUT)
    print(Path(f"logs/pipe_dots_{prep}.log").read_text()[-1500:], flush=True)
print("STAGE C DONE", flush=True)
