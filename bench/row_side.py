"""The row side of the common base (Table 10) in detail: what the misplaced and unresolved row-side figures are.

1. Misplaced row: where the label the output attached to the figure sits in the ground truth, relative to the figure's
   own line: the next line, the line before, two lines away, three or more, a section heading, or another statement.
2. Lines printed without a label: eligible ground-truth figures on subtotals and totals that carry no label in the
   filing. No output can state their line item, so the scorer never credits them; they are counted per system, and
   the row side is given with and without them.
3. Where each system puts the labels of its table rows, on the test pages of statements whose columns are periods:
   pages on which most ground-truth labels (six characters or more) are found in the output's tables, outside its
   tables only, or nowhere in the output (fuzzy partial match at 90).
Writes bench/ROW_SIDE.md and bench/row_side_summary.json.   usage: python bench/row_side.py
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

from rapidfuzz import fuzz

PAPER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PAPER / "bench"))
import common_subset as CS  # noqa: E402
import rq2_strict as R  # noqa: E402

OFFSETS = ("next line", "line before", "section heading", "two lines away", "three or more lines away",
           "another statement", "credited to another cell")


def offset(test, a):
    c, (si, rid, _) = a["cell"], a["k"]
    rk = tuple(c.get("row_key") or ())
    if not rk:
        return "credited to another cell"
    if rk[0] != si:
        return "another statement"
    rows = test[a["filing"]]["statements"][si]["rows"]
    if next(r for r in rows if r["id"] == rk[1]).get("kind") == "section":
        return "section heading"
    ids = [r["id"] for r in rows if r.get("kind") != "section"]
    d = ids.index(rk[1]) - ids.index(rid)
    return {1: "next line", -1: "line before"}.get(d, "two lines away" if abs(d) == 2 else "three or more lines away")


def label_placement(run, test):
    pages = Counter()
    for fid, gt in test.items():
        for st in gt["statements"]:
            if st["type"] == "changes_in_equity":
                continue
            labels = [R.nlabel(r.get("label_ar", "")) for r in st["rows"] if r.get("kind") != "section"]
            labels = [x for x in labels if len(x) >= 6]
            for p in st["pages"]:
                f = R.RESULTS / run / f"{fid}_p{p:02d}.md"
                if not f.exists() or not labels:
                    continue
                raw = f.read_text(errors="replace")
                tables = " ".join(re.sub(r"<[^>]+>", " ", t) for t in re.findall(r"<table.*?</table>", raw, flags=re.S))
                if not tables:                                       # Markdown tables: rows of pipe-separated cells
                    tables = " ".join(l for l in raw.splitlines() if l.strip().startswith("|"))
                    outside = " ".join(l for l in raw.splitlines() if not l.strip().startswith("|"))
                else:
                    outside = re.sub(r"<table.*?</table>", " ", raw, flags=re.S)
                found = lambda txt: sum(1 for x in labels if txt and fuzz.partial_ratio(x, txt) >= 90)
                tin, tout = found(R.nlabel(tables)), found(R.nlabel(outside))
                pages["pages"] += 1
                if tin >= len(labels) / 2:
                    pages["labels mostly in its tables"] += 1
                elif tout >= len(labels) / 2:
                    pages["labels mostly outside its tables"] += 1
                else:
                    pages["labels mostly absent"] += 1
    return dict(pages)


def main():
    S = json.load(open(PAPER / "bench" / "rq2_strict_summary.json"))
    tr, tc = S["thresholds"]["row"], S["thresholds"]["col"]
    test = R.score.load_gt(str(PAPER / "gt"), "test")
    second = R.MAIN["dots.mocr pipeline, seed 0"][0]
    common = json.load(open(PAPER / "bench" / "common_subset_summary.json"))["systems"]
    unlabeled = set()
    for fid, gt in test.items():
        _, _, elig = CS.eligible_cells(gt)
        for (si, rid, cid) in elig:
            r = next(x for x in gt["statements"][si]["rows"] if x["id"] == rid)
            if not R.nlabel(r.get("label_ar", "")):
                unlabeled.add((fid, si, rid, cid))
    cache, out = {}, dict(unlabeled_cells=len(unlabeled), systems={})
    for name, run in CS.SYSTEMS.items():
        res = R.analyse(run, second, second, None, test, tr, tc, cache)
        assign = []
        o, _ = CS.outcomes(res, test, assign)
        n = o["eligible"]
        assert o["misplaced: row"] == round(common[name]["sides"]["misplaced: row"] * n)
        mis = [a for a in assign if a["outcome"] == "misplaced" and a["side"] == "row"]
        unr = [a for a in assign if a["outcome"] == "unresolved" and a["side"] == "row"]
        on_blank = lambda a: (a["filing"], *a["k"]) in unlabeled
        off = Counter(offset(test, a) for a in mis)
        blank_out = Counter("complete" if a["outcome"] == "complete" else f"{a['outcome']}: {a['side']}"
                            for a in assign if on_blank(a))
        row = len(mis) + len(unr)
        out["systems"][name] = dict(
            eligible=n, misplaced_row=len(mis), offsets={k: off[k] for k in OFFSETS},
            unresolved_row=len(unr), unresolved_row_status=dict(Counter(a["cell"].get("row_status") for a in unr)),
            unresolved_row_unlabeled=sum(map(on_blank, unr)), misplaced_row_unlabeled=sum(map(on_blank, mis)),
            unlabeled_outcomes=dict(blank_out), row_side=row / n,
            row_side_without_unlabeled=(row - sum(map(on_blank, unr)) - sum(map(on_blank, mis))) / n,
            period_side=common[name]["sides"]["unresolved: column"] + common[name]["sides"]["misplaced: column"],
            label_placement=label_placement(run, test))
        print(name, out["systems"][name]["offsets"], flush=True)
    (PAPER / "bench" / "row_side_summary.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    pct = lambda a, b: f"{100 * a / b:.1f}%" if b else "–"
    md = ["# The row side of the common base", "", "Method: header of `bench/row_side.py`. Common base as in Table 10 "
          f"(`bench/common_subset.py`): {next(iter(out['systems'].values()))['eligible']:,} figures.", "",
          "## Where the label of a misplaced figure points", "",
          "| System | Misplaced row | " + " | ".join(OFFSETS) + " | One line off |", "|---|---:|" + "---:|" * (len(OFFSETS) + 1)]
    for name, v in out["systems"].items():
        m, f = v["misplaced_row"], v["offsets"]
        md.append(f"| {name} | {m} | " + " | ".join(f"{f[k]} ({pct(f[k], m)})" for k in OFFSETS) +
                  f" | {pct(f['next line'] + f['line before'], m)} |")
    md += ["", "## Lines printed without a label", "",
           f"{len(unlabeled)} of the eligible figures ({pct(len(unlabeled), next(iter(out['systems'].values()))['eligible'])}) "
           "sit on subtotals or totals that carry no label in the filing. No output can state their line item, so the scorer "
           "never credits them as complete facts.", "",
           "| System | Unresolved row | of which: no label / label unmatched | of which on unlabeled lines | Misplaced row on unlabeled lines | Row side | Row side without unlabeled lines | Period side |",
           "|---|---:|---|---:|---:|---:|---:|---:|"]
    for name, v in out["systems"].items():
        st = v["unresolved_row_status"]
        md.append(f"| {name} | {v['unresolved_row']} | {st.get('no label', 0)} / {st.get('label unmatched', 0)} | "
                  f"{v['unresolved_row_unlabeled']} | {v['misplaced_row_unlabeled']} | {100 * v['row_side']:.1f}% | "
                  f"{100 * v['row_side_without_unlabeled']:.1f}% | {100 * v['period_side']:.1f}% |")
    md += ["", "## Where each system puts the labels of its table rows (test pages, statements with period columns)", "",
           "| System | Pages | Labels mostly in its tables | Mostly outside its tables only | Mostly absent from the output |",
           "|---|---:|---:|---:|---:|"]
    for name, v in out["systems"].items():
        lp = v["label_placement"]
        md.append(f"| {name} | {lp['pages']} | {lp.get('labels mostly in its tables', 0)} | "
                  f"{lp.get('labels mostly outside its tables', 0)} | {lp.get('labels mostly absent', 0)} |")
    (PAPER / "bench" / "ROW_SIDE.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
