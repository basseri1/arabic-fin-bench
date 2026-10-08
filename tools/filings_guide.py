"""Write paper/FILINGS.md: how to obtain each of the 32 filings, which the release does not redistribute.

For every filing: issuer, report and period, the PDF's page count, the pages transcribed, its SHA-256 checksum and its
URL on the Saudi Exchange where one was recorded. For the nine without a recorded URL, the issuer's Arabic name and
the place of the report on the exchange's website, so that the file can be found and then verified by its checksum.
Reads dataset_inventory.csv and gt/.   usage: python tools/filings_guide.py
"""
import csv
import json
import re
from pathlib import Path

PAPER = Path(__file__).resolve().parent.parent


def main():
    inv = list(csv.DictReader(open(PAPER / "dataset_inventory.csv", encoding="utf-8-sig")))
    out = ["# Obtaining the filings", "",
           "The benchmark does not redistribute the filings or their page images (Saudi Exchange terms of use). Every file "
           "was obtained from the Saudi Exchange website (www.saudiexchange.sa). Obtain each one as described below, then "
           "check its SHA-256 checksum (`shasum -a 256 FILE.pdf` or `certutil -hashfile FILE.pdf SHA256`) and render its "
           "statement pages with `bench/render_pages.py` to reproduce the exact page images the systems received.", "",
           "Written by `tools/filings_guide.py` from `dataset_inventory.csv` and `gt/`.", ""]
    for r in sorted(inv, key=lambda x: x["filing_id"]):
        gt = json.load(open(PAPER / "gt" / f"{r['filing_id']}.json", encoding="utf-8"))
        pages = sorted({int(p) for st in gt["statements"] for p in st["pages"]})
        entity = re.sub(r" — .*", "", r["entity"]).strip()
        rep = {"Annual": "annual report (audited financial statements)", "Interim (H1)": "interim financial statements, first half",
               "Interim (Q1)": "interim financial statements, first quarter"}[r["report"]]
        out += [f"## {r['filing_id']}", "",
                f"- Issuer: {entity}" + ("" if re.match(r"^[\w\-]+\.pdf$", r["file_name_ar"]) or r["file_name_ar"].endswith(".pdf")
                                         else f" ({r['file_name_ar']})"),
                f"- Report: {rep}, period ending {r['period_end']}; Arabic version, {r['pdf_pages']} PDF pages",
                f"- Statement pages transcribed: {', '.join(map(str, pages))}",
                f"- SHA-256: `{r['sha256']}`"]
        if r["public_source_url"].strip():
            out.append(f"- URL: {r['public_source_url']} (downloaded or checked against the exchange's copy on 27 Sep 2026)")
        else:
            out.append(f"- URL: not recorded. On www.saudiexchange.sa, find the issuer by its name"
                       f"{' (Arabic name above)' if not r['file_name_ar'].endswith('.pdf') else ''}, open its financial reports, and "
                       f"select the {rep} for the period ending {r['period_end']}, Arabic version, {r['pdf_pages']} pages. "
                       "The file was not re-checked against the exchange's current pages; verify it by the checksum above.")
        out.append("")
    (PAPER / "FILINGS.md").write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {PAPER / 'FILINGS.md'} ({len(inv)} filings)")


if __name__ == "__main__":
    main()
