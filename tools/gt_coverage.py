"""Write paper/GT_COVERAGE.md: how many ground-truth figures the printed-total checks protect.

A figure is covered when it is the total or a component of a printed total, in the same column, whose components are
listed in sum_of (validate_gt.py checks that every such total reconciles). A misread digit in a covered figure breaks
a total; an error in an uncovered figure, or a value placed under the wrong line, does not. Figures are counted as in
gtlib.stats (every numeric value of a row), by the format of the statement pages.

usage: python tools/gt_coverage.py
"""
import csv
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gtlib  # noqa: E402

PAPER = gtlib.PAPER
FORMATS = [("scanned", "fully scanned"), ("images", "images in a digital PDF"), ("", "text layer")]  # first match wins


def fmt_of(s):
    s = s.lower()
    return next(name for key, name in FORMATS if key in s)


def main():
    inv = {r["filing_id"]: r for r in csv.DictReader(open(PAPER / "dataset_inventory.csv", encoding="utf-8-sig"))}
    tot, cov = Counter(), Counter()
    unc_type, unc_kind = Counter(), Counter()
    for f in sorted((PAPER / "gt").glob("*.json")):
        gt = gtlib.load(f)
        fm = fmt_of(inv[gt["filing_id"]]["statement_pages_format"])
        for st in gt["statements"]:
            rows = {r["id"]: r for r in st["rows"]}
            covered = set()
            for r in st["rows"]:
                refs = [ref.lstrip("-") for ref in (r.get("sum_of") or [])]
                if not refs:
                    continue
                for c, v in (r.get("values") or {}).items():
                    if v is None:
                        continue
                    for rid in [r["id"]] + refs:
                        if (rows.get(rid, {}).get("values") or {}).get(c) is not None:
                            covered.add((rid, c))
            for r in st["rows"]:
                for c, v in (r.get("values") or {}).items():
                    if not isinstance(v, (int, float)):
                        continue
                    tot[fm] += 1
                    if (r["id"], c) in covered:
                        cov[fm] += 1
                    else:
                        unc_type[st["type"]] += 1
                        unc_kind[r["kind"]] += 1
    out = ["# Ground-truth figures protected by printed-total checks", "",
           "A figure is covered when it is the total or a component of a printed total (same column) whose components "
           "are listed and reconcile. Written by `tools/gt_coverage.py`.", "",
           "| Statement pages | Figures | Covered | Share |", "|---|---:|---:|---:|"]
    for _, name in reversed(FORMATS):
        out.append(f"| {name} | {tot[name]:,} | {cov[name]:,} | {cov[name] / tot[name]:.1%} |")
    T, C = sum(tot.values()), sum(cov.values())
    out += [f"| **all** | **{T:,}** | **{C:,}** | **{C / T:.1%}** |", "",
            f"Not covered: {T - C:,} figures. By statement type: "
            + ", ".join(f"{k} {v}" for k, v in unc_type.most_common()) + ". By row kind: "
            + ", ".join(f"{k} {v}" for k, v in unc_kind.most_common()) + ".", "",
            "Not checked by arithmetic at all: the line and period under which a figure is recorded. Two components "
            "swapped between lines still add up to their total, so placement in the ground truth rests on the "
            "cell-by-cell verification against the page images."]
    (PAPER / "GT_COVERAGE.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
