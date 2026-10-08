import sys; sys.path.insert(0, "."); import eval2
from pathlib import Path
from collections import Counter, defaultdict
GT = eval2.parse_gt(open("drilling_main_tables.md").read())
TNAME = {1: "P&L p10", 2: "OCI p10", 3: "Balance p08-09", 4: "Equity p11 (landscape)", 5: "Cashflow p12-13", 6: "Non-cash p13"}
RUNS = {"local plain": "local_ref/chandra2_plain_drill", "local clahe": "results_drill/chandra2_clahe",
        "H100 plain": "results_pipe/chandra2_plain", "H100 clahe": "results_pipe/chandra2_clahe",
        "H100 hires": "results_pipe/chandra2_hires_portrait", "H100 at-cap": "results_pipe/chandra2_chandra_cap"}
def digits(v): return f"{abs(v):.0f}"
miss_count = Counter(); miss_runs = defaultdict(list); near = defaultdict(set); nruns = Counter()
for rn, d in RUNS.items():
    for ti, tb in enumerate(GT, 1):
        fs = [Path(d) / f"{p}.md" for p in eval2.TABLE_PAGES["drilling"][ti]]
        if not all(f.exists() for f in fs): continue
        nruns[ti] += 1
        lines = []
        for f in fs: lines += eval2.lines_of(eval2.extract_text(f.read_text(errors="replace")))
        lines = eval2.truncate_loops("\n".join(lines))[0].split("\n")
        out_abs = Counter(abs(v) for l in lines for v in eval2.numbers(l))
        for row in tb["rows"]:
            figs = [abs(f) for f in row["figs"]]
            if figs and not any(all(f in [abs(x) for x in eval2.numbers(l)] for f in figs) for l in lines):
                key = (ti, row["label"][:38]); miss_count[key] += 1; miss_runs[key].append(rn)
                for f in figs:
                    if out_abs[f] == 0:
                        for o in out_abs:
                            if len(digits(o)) == len(digits(f)) and sum(a != b for a, b in zip(digits(o), digits(f))) == 1:
                                near[key].add(f"{f:,.0f} read as {o:,.0f}")
print("Chandra-2 on Arabian Drilling: rows missed, aggregated across 6 runs (Mac + H100 variants)")
for (ti, lab), c in sorted(miss_count.items(), key=lambda x: -x[1]):
    print(f"  {c}/{nruns[ti]} runs  [{TNAME[ti]:<22}] {lab}")
    if near[(ti, lab)]:
        print(f"          digit misreads seen: {sorted(near[(ti, lab)])[:4]}")
    rs = miss_runs[(ti, lab)]
    if len(rs) < nruns[ti]:
        print(f"          failed in: {', '.join(rs)}")
