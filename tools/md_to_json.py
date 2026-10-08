"""Convert the three pilot ground-truth Markdown files to the JSON format (one file per filing).

usage: python md_to_json.py            -> writes paper/gt/{aramco,maaden,arabian_drilling}_FY2024.json
The totals structure (row kinds and sum_of) comes from pilot_sums.json, so every filing is checked the same way.
"""
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gtlib  # noqa: E402

BENCH = gtlib.BENCH
PILOT = {  # md stem -> filing metadata the Markdown does not carry
    "aramco": dict(filing_id="aramco_FY2024", entity="Saudi Aramco", scale=1000000, digits="western"),
    "maaden": dict(filing_id="maaden_FY2024", entity="Ma'aden (Saudi Arabian Mining Co.)", scale=1, digits="arabic-indic"),
    "drilling": dict(filing_id="arabian_drilling_FY2024", entity="Arabian Drilling", scale=1, digits="arabic-indic"),
}
TYPES = [  # title keyword -> statement type (checked in order)
    (r"المركز المالي", "financial_position"),
    (r"التغيرات في حقوق الملكية", "changes_in_equity"),
    (r"التدفقات النقدية(?!.*غير النقدية)", "cash_flows"),
    (r"غير نقدية|غير النقدية", "other"),
    (r"الربح أو الخسارة والدخل الشامل", "income_and_comprehensive_income"),
    (r"الدخل الشامل", "comprehensive_income"),
    (r"الربح أو الخسارة|قائمة الدخل", "income"),
]


def stmt_type(title):
    for pat, t in TYPES:
        if re.search(pat, title):
            return t
    return "other"


def column(cid, label, default_ccy):
    yr = re.search(r"(20\d\d)", label)
    ccy = "USD" if "دولار" in label else ("SAR" if "ريال" in label else default_ccy)
    col = {"id": cid, "label": label, "currency": ccy}
    if yr:
        col["period"] = f"{yr.group(1)}-12-31"
    return col


KIND = {"i": "item", "st": "subtotal", "t": "total", "s": "section"}


def apply_sums(fid, statements):
    """Row kinds and sum_of for the pilot filings (the Markdown ground truth carries neither)."""
    from draft_to_json import sum_refs
    spec = json.loads((gtlib.TOOLS / "pilot_sums.json").read_text(encoding="utf-8")).get(fid, {})
    by_id = {st["id"]: st for st in statements}
    for sid, rows in spec.items():
        st = by_id[sid]
        for num, rule in rows.items():
            kind, _, refs = rule.partition(" ")
            row = st["rows"][int(num) - 1]
            row["kind"] = KIND[kind]
            if refs:
                row["sum_of"] = sum_refs(refs, len(st["rows"]))


def inventory():
    p = gtlib.PAPER / "dataset_inventory.csv"
    return {r["filing_id"]: r for r in csv.DictReader(open(p, encoding="utf-8-sig"))}


def convert(stem):
    meta = PILOT[stem]
    md = (BENCH / f"{stem}_main_tables.md").read_text(encoding="utf-8")
    inv = inventory()[meta["filing_id"]]
    pages_by_table = {k: sorted({int(p.rsplit("_p", 1)[1]) for p in v}) for k, v in gtlib.eval2.TABLE_PAGES[stem].items()}
    statements, title, cur = [], "", None
    for line in md.splitlines():
        s = line.strip()
        if s.startswith("#"):
            title = re.sub(r"^#+\s*(\d+\.\s*)?", "", s).strip()
            cur = None
            continue
        if not s.startswith("|"):
            cur = None
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
            continue
        if cur is None:                                  # header row opens a new statement table
            has_notes = len(cells) > 1 and re.fullmatch(r"\s*إيضاح(ات)?\s*", cells[1]) is not None
            vcells = cells[2:] if has_notes else cells[1:]
            ccy = "SAR"
            cur = {"id": f"s{len(statements) + 1}", "type": stmt_type(title), "title_ar": title,
                   "pages": pages_by_table.get(len(statements) + 1, []),
                   "unit": {"currency": ccy, "scale": meta["scale"]},
                   "columns": [column(f"c{i + 1}", lab, ccy) for i, lab in enumerate(vcells)], "rows": [],
                   "_has_notes": has_notes}
            statements.append(cur)
            continue
        has_notes = cur["_has_notes"]
        raw_label = cells[0]
        label = re.sub(r"[*_]", "", raw_label).strip()
        notes = [n.strip() for n in re.split(r"[،,]", cells[1]) if n.strip()] if has_notes and len(cells) > 1 else []
        vcells = cells[2:] if has_notes else cells[1:]
        values = {}
        for col, txt in zip(cur["columns"], vcells):
            v = gtlib.parse_value(txt)
            if v is not None:
                values[col["id"]] = v
        bold = raw_label.startswith("**")
        kind = "section" if not values else ("total" if bold else "item")
        row = {"id": f"r{len(cur['rows']) + 1}", "kind": kind, "label_ar": label}
        if notes:
            row["notes"] = notes
        if values:
            row["values"] = values
        cur["rows"].append(row)
    for st in statements:
        st.pop("_has_notes", None)
    apply_sums(meta["filing_id"], statements)
    return {"schema_version": "1.0", "filing_id": meta["filing_id"], "entity": meta["entity"],
            "source": {"url": inv.get("public_source_url", ""), "sha256": inv["sha256"], "file": f"filings/{meta['filing_id']}.pdf"},
            "period_end": "2024-12-31", "report": "annual", "consolidated": True, "digits": meta["digits"],
            "annotator": "pilot ground truth (hand-verified)", "statements": statements}


if __name__ == "__main__":
    for stem in PILOT:
        gt = convert(stem)
        out = gtlib.PAPER / "gt" / f"{gt['filing_id']}.json"
        gtlib.save(gt, out)
        errors, warnings = gtlib.validate(gt)
        print(f"{out.name}: {gtlib.stats(gt)} | errors {len(errors)} | warnings {len(warnings)}")
        for e in errors[:5]:
            print("   ERROR", e)
