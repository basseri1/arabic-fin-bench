"""Exception ledger: the inconsistencies printed in the filings, kept apart from the total checks they affect.

Every printed total or subtotal in the ground truth lists its components (`sum_of`) and must reconcile, except those that a
printed inconsistency makes fail as printed. This script lists, from the ground-truth files themselves:
  1. the printed inconsistencies (source errors, kept as printed in the transcription);
  2. the total checks each one affects: the totals left without a component list, with the printed value, the sum of the
     printed components and the sum once the inconsistency is corrected, which must equal the printed total;
  3. apparent gaps that were checked against the page and found not to exist (recorded apart, not as source errors).
Values are read from gt/*.json; only the component lists of the unchecked totals and the corrections are written here.

Writes EXCEPTIONS.md and exceptions.json next to dataset_inventory.csv (not in gt/, whose files the scorer loads).   usage: python tools/exception_ledger.py
"""
import json
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1]

# printed inconsistencies: (filing, statement, row, column, kind, what the page shows, the correction the rest implies)
INCONSISTENCIES = [
    dict(id="I1", filing="alinma_tokio_marine_FY2022", st="s2", row="r28", col="c1", kind="sign", line_en="Changes in mathematical reserves",
         note="2022 figure printed in parentheses; the subtotal and the cash-flow statement imply a positive figure",
         corrected=358),
    dict(id="I2", filing="alinma_tokio_marine_FY2022", st="s2", row="r34", col="c1", kind="sign", line_en="Allowance for doubtful debts",
         note="2022 figure printed in parentheses; the subtotal and the cash-flow statement imply a positive figure",
         corrected=8580),
    dict(id="I3", filing="blom_saudi_fund_FY2022", st="s2", row="r10", col="c1", kind="sign", line_en="Total expenses",
         note="2022 total expenses printed without parentheses, unlike its components and the 2021 figure",
         corrected=-564308),
    dict(id="I4", filing="nama_FY2024", st="s3", row="r3", col="c5", kind="sign", line_en="Other comprehensive loss (total equity)",
         note="total-equity column of other comprehensive income printed in parentheses; its component and the "
              "comprehensive income statement show a positive figure", corrected=385),
    dict(id="I5", filing="bishah_FY2016", st="s2", row="r9", col="c2", kind="truncated subtotal", line_en="Net loss before extraordinary losses",
         note="2015 subtotal printed as (1,474); its components give (1,473,570), the figure carried to the next total",
         corrected=-1473570),
    dict(id="I6", filing="cenomi_retail_FY2024", st="s4", row="r4", col="c7", kind="rounding gap", line_en="Other comprehensive income (total equity)",
         note="2023 other comprehensive income in the changes-in-equity statement is one riyal from the comprehensive "
              "income statement", corrected=None, other=("s3", "r9", "c2")),
]

# total checks left without a component list, with the components a reader would list
AFFECTED = [
    dict(by="I1", filing="alinma_tokio_marine_FY2022", st="s2", row="r31", col="c1", line_en="Total underwriting costs and expenses", sum_of=["r26", "r27", "r28", "r29", "r30"]),
    dict(by="I2", filing="alinma_tokio_marine_FY2022", st="s2", row="r38", col="c1", line_en="Total other operating expenses, net", sum_of=["r33", "r34", "r35", "r36", "r37"]),
    dict(by="I3", filing="blom_saudi_fund_FY2022", st="s2", row="r10", col="c1", line_en="Total expenses", sum_of=["r8", "r9"]),
    dict(by="I3", filing="blom_saudi_fund_FY2022", st="s2", row="r11", col="c1", line_en="Net income for the year", sum_of=["r6", "r10"]),
    dict(by="I4", filing="nama_FY2024", st="s3", row="r4", col="c5", line_en="Total comprehensive income (total equity)", sum_of=["r2", "r3"]),
    dict(by="I5", filing="bishah_FY2016", st="s2", row="r9", col="c2", line_en="Net loss before extraordinary losses", sum_of=["r6", "r7", "r8"]),
]

# apparent gaps checked against the page and found not to be in the source
NOT_IN_SOURCE = [
    dict(filing="halwani_FY2024", st="cash_flows", line="سداد التزامات عقود إيجار (lease payments)", period="2023",
         page_value=-8095329, misread=-8065329, subtotal_line="صافي النقد (المستخدم في) الأنشطة التمويلية", subtotal=-21681009,
         note="A check of the ground truth read the lease payments as (8,065,329), which would leave the financing "
              "subtotal 30,000 short. The page (re-read at 400 dpi) shows (8,095,329); with it the subtotal reconciles. "
              "The ground truth already had (8,095,329) and is unchanged."),
]


def num(v):
    return 0 if v in (None, "nil", "-") else v


def main():
    gts = {}

    def row(fid, sid, rid):
        if fid not in gts:
            gts[fid] = json.load(open(PAPER / "gt" / f"{fid}.json"))
        st = next(s for s in gts[fid]["statements"] if s["id"] == sid)
        return st, next(r for r in st["rows"] if r["id"] == rid)

    corr = {(x["filing"], x["st"], x["row"], x["col"]): x["corrected"] for x in INCONSISTENCIES if x["corrected"] is not None}
    out = dict(inconsistencies=[], affected=[], not_in_source=NOT_IN_SOURCE)
    for x in INCONSISTENCIES:
        st, r = row(x["filing"], x["st"], x["row"])
        rec = dict(x, statement=st["type"], label=r.get("label_ar", ""), period=(next(c for c in st["columns"] if c["id"] == x["col"]).get("period") or ""),
                   printed=r["values"][x["col"]], scale=st.get("unit", {}).get("scale", 1))
        if x.get("other"):
            st2, r2 = row(x["filing"], *x["other"][:2])
            rec["other_statement"], rec["other_value"] = st2["type"], r2["values"][x["other"][2]]
            rec["gap"] = rec["printed"] - rec["other_value"]
        out["inconsistencies"].append(rec)
    # every subtotal/total without a component list must be explained by an entry here
    unlisted = {(g["filing_id"], st["id"], r["id"]) for g in [json.load(open(f)) for f in sorted((PAPER / "gt").glob("*.json"))]
                for st in g["statements"] for r in st["rows"] if r["kind"] in ("subtotal", "total") and not r.get("sum_of")}
    assert unlisted == {(a["filing"], a["st"], a["row"]) for a in AFFECTED}, unlisted
    for a in AFFECTED:
        st, r = row(a["filing"], a["st"], a["row"])
        comps = [row(a["filing"], a["st"], c)[1] for c in a["sum_of"]]
        printed = num(r["values"][a["col"]])
        as_printed = sum(num(c["values"].get(a["col"])) for c in comps)
        fixed = sum(corr.get((a["filing"], a["st"], c["id"], a["col"]), num(c["values"].get(a["col"]))) for c in comps)
        assert abs(fixed - corr.get((a["filing"], a["st"], a["row"], a["col"]), printed)) <= 1, (a, fixed, printed)
        out["affected"].append(dict(a, statement=st["type"], label=r.get("label_ar", ""),
                                    period=(next(c for c in st["columns"] if c["id"] == a["col"]).get("period") or ""),
                                    printed=printed, components_as_printed=as_printed, components_corrected=fixed,
                                    scale=st.get("unit", {}).get("scale", 1)))
    totals = listed = 0
    for f in sorted((PAPER / "gt").glob("*.json")):
        g = json.load(open(f))
        for st in g["statements"]:
            for r in st["rows"]:
                if r["kind"] in ("subtotal", "total"):
                    totals += 1; listed += bool(r.get("sum_of"))
    out["counts"] = dict(printed_totals=totals, with_component_list=listed, affected=len(AFFECTED), inconsistencies=len(INCONSISTENCIES))
    (PAPER / "exceptions.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    f = lambda v: "–" if v in (None, "nil") else (f"({abs(v):,})" if v < 0 else f"{v:,}")
    md = ["# Exception ledger", "",
          f"Printed totals and subtotals: {totals}. With a component list, all reconciling: {listed}. Without one: "
          f"{len(AFFECTED)}, each because a printed inconsistency below makes it fail as printed. "
          "Source errors are kept exactly as printed in the transcription and scored as printed.", "",
          "## 1. Printed inconsistencies (source errors)", "",
          "| ID | Filing | Statement | Line | Period | Kind | Printed | Implied by the rest of the filing | Note |",
          "|---|---|---|---|---|---|---:|---:|---|"]
    for x in out["inconsistencies"]:
        implied = f(x["corrected"]) if x["corrected"] is not None else f"{f(x['other_value'])} in the {x['other_statement'].replace('_', ' ')} statement"
        md.append(f"| {x['id']} | {x['filing']} | {x['statement'].replace('_', ' ')} | {x['label']} | {x['period'][:4] or 'total equity'} | "
                  f"{x['kind']} | {f(x['printed'])} | {implied} | {x['note']} |")
    md += ["", "## 2. Total checks affected (left without a component list)", "",
           "| Caused by | Filing | Statement | Total | Period | Printed | Components as printed | Components corrected | Treatment |",
           "|---|---|---|---|---|---:|---:|---:|---|"]
    for a in out["affected"]:
        md.append(f"| {a['by']} | {a['filing']} | {a['statement'].replace('_', ' ')} | {a['label']} | {a['period'][:4] or 'total equity'} | "
                  f"{f(a['printed'])} | {f(a['components_as_printed'])} | {f(a['components_corrected'])} | kept as printed; not counted "
                  "among the reconciled totals; scored as printed |")
    md += ["", "## 3. Checked, not in the source", "", "| Filing | Statement | Line | Period | Page | Misread as | Note |", "|---|---|---|---|---:|---:|---|"]
    for x in NOT_IN_SOURCE:
        md.append(f"| {x['filing']} | {x['st'].replace('_', ' ')} | {x['line']} | {x['period']} | {f(x['page_value'])} | {f(x['misread'])} | {x['note']} |")
    (PAPER / "EXCEPTIONS.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
