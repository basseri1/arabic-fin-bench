"""Validate ground-truth / draft JSON files: schema, ids, arithmetic (sum_of), and optionally the text-layer cross-check.

usage: python validate_gt.py paper/gt/*.json paper/drafts/*.json [--textlayer] [--tol 1]
Exit status 1 when any file has errors. Subtractions in sum_of ("-r12") are checked here (the workbook's live
check handles additions only).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gtlib  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--tol", type=float, default=1.0)
    ap.add_argument("--textlayer", action="store_true", help="also compare figures with the PDF text layer")
    a = ap.parse_args()
    bad, total = 0, {"statements": 0, "rows": 0, "figures": 0, "checked_totals": 0}
    print(f"{'filing':36s} {'stmts':>5s} {'rows':>5s} {'figures':>7s} {'totals':>6s}  status")
    for f in a.files:
        gt = gtlib.load(f)
        errors, warnings = gtlib.validate(gt, a.tol)
        st = gtlib.stats(gt)
        for k in total:
            total[k] += st[k]
        note = ""
        if a.textlayer and not errors:
            import textlayer
            report, _ = textlayer.check(gt)
            checked = [m for _, m in report if m is not None]
            if checked:
                miss = sum(len(m) for m in checked)
                note = f" | text layer: {miss} figure(s) not found" if miss else " | text layer: all figures found"
        status = f"{len(errors)} errors" if errors else "ok"
        print(f"{gt['filing_id']:36s} {st['statements']:>5d} {st['rows']:>5d} {st['figures']:>7d} {st['checked_totals']:>6d}  {status}{note}")
        for e in errors:
            print("    ERROR  ", e)
        bad += bool(errors)
    print(f"{'TOTAL (' + str(len(a.files)) + ' files)':36s} {total['statements']:>5d} {total['rows']:>5d} {total['figures']:>7d} {total['checked_totals']:>6d}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
