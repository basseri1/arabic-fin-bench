"""One-time backfill: add year column headers to stored results of jobs processed before the header feature.
Replicates the pipeline's promotion logic (page-header year scan via cached OCR artifacts, in-table year-row
fallback, junk empty-header cleanup, year-body-row drop). Only touches tables with missing/blank cols.
Run on the VM: cd ~/ocr_benchmark && python3 backfill_cols.py
"""
import json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / "ocr_benchmark" / "webapp"))
sys.path.insert(0, str(Path.home() / "ocr_benchmark"))
import eval2
import docdetect
from app import merged_lines

JD = Path.home() / "qawaim_jobs"
YEAR_PAT = re.compile(r"(?<![\d٠-٩])(?:20[12]\d|[٠-٩]{4})(?![\d٠-٩])")

def row_years(r):
    nums = [x for c in r for x in eval2.numbers(str(c))]
    return [abs(x) for x in nums] if nums and all(2015 <= abs(x) <= 2030 for x in nums) else []

changed = skipped = 0
for jd in sorted(JD.iterdir()):
    rf = jd / "result.json"
    if not rf.exists(): continue
    try: r = json.loads(rf.read_text())
    except Exception: continue
    dirty = False
    for p in r.get("pages", []):
        no = p.get("no")
        stem = f"p{no:03d}" if isinstance(no, int) else None
        year_order, dual = [], False
        if stem and (jd / f"{stem}.md").exists():
            try:
                mls = merged_lines(jd, stem)
                dual = bool(re.search(r"دولار|USD", " ".join(mls[:14])))
                for ml in mls[:40]:
                    ys = [int(docdetect.west(m)) for m in YEAR_PAT.findall(ml)]
                    ys = [y for y in ys if 2015 <= y <= 2030]
                    if len(ys) >= 2: year_order = ys[:2]; break
            except Exception: pass
        for reg in p.get("regions", []):
            if reg.get("kind") != "table": continue
            cols = reg.get("cols")
            blank = bool(cols) and not any(str(c or "").strip() for c in cols)
            if cols and not blank: continue                 # already has real headers
            if blank: reg.pop("cols", None); dirty = True   # junk cleanup
            rows = reg.get("rows") or []
            width = max((len(x) for x in rows), default=0)
            if width < 3: continue
            yo = list(year_order)
            if not yo:
                for row in rows[:4]:
                    ys2 = row_years(row)
                    if len(ys2) >= 2: yo = ys2[:2]; break
            if not yo: continue
            nval = width - 2
            ys = [str(y) for y in yo]
            if dual and nval >= 4:
                heads = [ys[0] + " ريال", ys[1] + " ريال", ys[0] + " دولار", ys[1] + " دولار"][:nval]
            else:
                heads = (ys * ((nval + 1) // 2))[:nval]
            reg["cols"] = ["البند", "إيضاح"] + heads + [""] * (width - 2 - len(heads))
            keep = [i for i, row in enumerate(rows) if not row_years(row)]
            if len(keep) < len(rows):
                reg["rows"] = [rows[i] for i in keep]
                if reg.get("cellmeta"): reg["cellmeta"] = [reg["cellmeta"][i] for i in keep if i < len(reg["cellmeta"])]
                if reg.get("rowys"): reg["rowys"] = [reg["rowys"][i] for i in keep if i < len(reg["rowys"])]
            dirty = True
    if dirty:
        rf.write_text(json.dumps(r, ensure_ascii=False)); changed += 1
    else:
        skipped += 1
print(f"backfilled {changed} jobs, untouched {skipped}")
