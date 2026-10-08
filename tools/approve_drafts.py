
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gtlib  # noqa: E402
import make_workbook  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--by", required=True, help="who approved the drafts")
    ap.add_argument("--date", required=True, help="approval date, YYYY-MM-DD")
    a = ap.parse_args()
    bad = 0
    for f in a.files:
        gt = gtlib.load(f)
        out = gtlib.PAPER / "gt" / f"{gt['filing_id']}.json"
        if out.exists():
            print(f"skip {gt['filing_id']}: gt/ already has it"); continue
        gt["annotator"] = "annotator; automatic checks: arithmetic totals, plus the text layer where the page has one"
        gt["verified_by"] = f"{a.by} (approved {a.date})"
        errors, _ = gtlib.validate(gt)
        if errors:
            bad += 1; print(f"NOT written {gt['filing_id']}: {len(errors)} errors"); continue
        gtlib.save(gt, out)
        make_workbook.build(gt["filing_id"], gt, prefilled=False)
        print(f"approved {gt['filing_id']} -> {out.relative_to(gtlib.PAPER)}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
