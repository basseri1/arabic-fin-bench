"""Write paper/DATASET_STATUS.md: per-filing counts, strata, checks and verification status.

usage: python dataset_report.py [--textlayer]
"""
import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gtlib  # noqa: E402

FORMAT = [("garbled", "text (garbled)"), ("Images inside digital PDF", "images in digital PDF"),
          ("Fully scanned", "fully scanned"), ("Text", "text")]              # order matters: first match wins


def fmt_of(s):
    for key, name in FORMAT:
        if key.lower() in s.lower():
            return name
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--textlayer", action="store_true")
    a = ap.parse_args()
    inv = {r["filing_id"]: r for r in csv.DictReader(open(gtlib.PAPER / "dataset_inventory.csv", encoding="utf-8-sig"))}
    rows, tot = [], Counter()
    for fid, r in inv.items():
        gpath, dpath = gtlib.PAPER / "gt" / f"{fid}.json", gtlib.PAPER / "drafts" / f"{fid}.json"
        path = gpath if gpath.exists() else dpath
        if not path.exists():
            rows.append((fid, r, None, "missing", "")); continue
        gt = gtlib.load(path)
        errors, _ = gtlib.validate(gt)
        st = gtlib.stats(gt)
        if path != gpath:
            status = "annotator, awaiting verification"
        elif gt.get("annotator", "").startswith("annotator"):
            status = f"annotator, verified by {gt.get('verified_by', '?')}"
        else:
            status = "verified (pilot, annotator-transcribed)"
        if errors:
            status += f" — {len(errors)} errors"
        tl = ""
        if a.textlayer and fmt_of(r["statement_pages_format"]).startswith("text"):
            import textlayer
            report, _ = textlayer.check(gt)
            checked = [m for _, m in report if m is not None]
            miss = sum(len(m) for m in checked)
            tl = "no text layer" if not checked else ("all found" if miss == 0 else f"{miss} missing")
        rows.append((fid, r, st, status, tl))
        tot.update(st)
    rows.sort(key=lambda x: (x[1]["proposed_split"].split()[0], x[0]))
    out = ["# Dataset status", "",
           f"{len(rows)} filings · {tot['statements']} statements · {tot['rows']:,} rows with figures · "
           f"{tot['figures']:,} figures · {tot['checked_totals']} totals checked arithmetically", "",
           "| Filing | Sector | Report | Split | Statement pages | Stmts | Rows | Figures | Totals ✓ | Text-layer check | Status |",
           "|---|---|---|---|---|---:|---:|---:|---:|---|---|"]
    for fid, r, st, status, tl in rows:
        if st is None:
            out.append(f"| {fid} | {r['sector']} | {r['report']} | {r['proposed_split']} | {fmt_of(r['statement_pages_format'])} | | | | | | {status} |")
            continue
        out.append(f"| {fid} | {r['sector']} | {r['report'].split(' (')[0]} | {r['proposed_split'].split(' (')[0]} | "
                   f"{fmt_of(r['statement_pages_format'])} | {st['statements']} | {st['rows']} | {st['figures']:,} | "
                   f"{st['checked_totals']} | {tl or '–'} | {status} |")
    def strata(key, fn=lambda v: v):
        c, f = Counter(), Counter()
        for fid, r, st, _, _ in rows:
            c[fn(r[key])] += 1
            f[fn(r[key])] += st["figures"] if st else 0
        return ", ".join(f"{k} {c[k]} ({f[k]:,} figures)" for k in sorted(c, key=lambda k: -c[k]))
    out += ["", "## Strata", "",
            f"- **Statement-page format:** {strata('statement_pages_format', fmt_of)}",
            f"- **Sector:** {strata('sector')}",
            f"- **Entity type:** {strata('entity_type')}",
            f"- **Split:** {strata('proposed_split', lambda v: v.split()[0])}",
            f"- **Report:** {strata('report', lambda v: v.split(' (')[0])}"]
    log = gtlib.PAPER / "drafts" / "corrections_log.csv"
    if log.exists():
        corr = list(csv.DictReader(open(log, encoding="utf-8")))
        drafted = sum(st["figures"] for fid, r, st, status, _ in rows if st and status.startswith("annotator")) or 1
        conf = Counter(c["confusion"].split(" (")[0] for c in corr)
        out += ["", "## Drafting slips caught by the automatic checks", "",
                f"{len(corr)} of {drafted:,} annotator figures ({len(corr) / drafted:.2%}) were misread at first and "
                f"corrected before approval, in {len({c['filing_id'] for c in corr})} filings: "
                + ", ".join(f"{n}× {k}" for k, n in conf.most_common()) + ". Details: `drafts/corrections_log.csv`."]
    (gtlib.PAPER / "DATASET_STATUS.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out[:3]))


if __name__ == "__main__":
    main()
