"""Convert a plain-text transcription draft to the JSON ground truth, validate it, and optionally build its workbook.

Draft format (paper/drafts/FILING_ID.txt):
    filing_id: almarai_FY2024          # header fields: entity, period_end, report, consolidated (yes/no), digits
    == financial_position | 8 | SAR | 1000 | قائمة المركز المالي الموحدة      (type | pages | currency | scale | title)
    cols: 31 ديسمبر 2024 @2024-12-31 | 31 ديسمبر 2023 @2023-12-31 [USD]      (label @period [currency])
    1 s | الموجودات
    3 i | ممتلكات وآلات ومعدات | 7 | 20,123,456 | (19,876) | -
    11 t | مجموع الموجودات غير المتداولة | | 30,000,000 | 29,000,000 | =3:10 | # optional comment
Rows: number, kind (s section, i item, st subtotal, t total), label, notes, one cell per column (as printed:
parentheses for negatives, - for a printed dash, empty for an empty cell), then optionally =sum_of (row numbers,
ranges a:b, a leading - subtracts) and #comment.

usage: python draft_to_json.py paper/drafts/FILING_ID.txt [--out gt.json] [--workbook]
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gtlib  # noqa: E402

KINDS = {"s": "section", "i": "item", "st": "subtotal", "t": "total"}
HEADER_KEYS = ("filing_id", "entity", "period_end", "report", "consolidated", "digits", "annotator", "comment")


def sum_refs(spec, n_rows):
    refs = []
    for part in spec.replace(" ", "").split(","):
        if not part:
            continue
        neg = part.startswith("-")
        part = part.lstrip("-")
        a, b = (part.split(":") + [None])[:2]
        rng = range(int(a), int(b or a) + 1)
        for x in rng:
            if not 1 <= x <= n_rows:
                raise ValueError(f"sum_of refers to row {x}, outside 1..{n_rows}")
            refs.append(("-" if neg else "") + f"r{x}")
    return refs


def parse(path):
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    meta, statements, problems, pending = {}, [], [], []
    cur = None
    for ln_no, raw in enumerate(lines, 1):
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        where = f"{Path(path).name}:{ln_no}"
        if s.startswith("=="):
            parts = [p.strip() for p in s[2:].split("|")]
            typ, pages, ccy, scale = parts[0], parts[1], parts[2] or "SAR", parts[3] or "1"
            cur = {"id": f"s{len(statements) + 1}", "type": typ, "title_ar": parts[4] if len(parts) > 4 else "",
                   "pages": [int(p) for p in re.split(r"[,\s]+", pages) if p],
                   "unit": {"currency": ccy, "scale": int(scale)}, "columns": [], "rows": []}
            statements.append(cur)
            pending.append([])
            continue
        if cur is None:
            m = re.match(r"(\w+)\s*:\s*(.*)$", s)
            if m and m.group(1) in HEADER_KEYS:
                meta[m.group(1)] = m.group(2).strip()
            else:
                problems.append(f"{where}: unexpected line before the first statement")
            continue
        if s.startswith("cols:"):
            for i, c in enumerate(s[5:].split("|"), 1):
                c = c.strip()
                ccy = re.search(r"\[([A-Z]{3})\]\s*$", c)
                c = re.sub(r"\[[A-Z]{3}\]\s*$", "", c).strip()
                per = re.search(r"@(\d{4}-\d{2}-\d{2})\s*$", c)
                label = re.sub(r"@\d{4}-\d{2}-\d{2}\s*$", "", c).strip()
                col = {"id": f"c{i}", "label": label, "currency": ccy.group(1) if ccy else cur["unit"]["currency"]}
                if per:
                    col["period"] = per.group(1)
                cur["columns"].append(col)
            continue
        m = re.match(r"(\d+)\s+(s|i|st|t)\s*\|(.*)$", s)
        if not m:
            problems.append(f"{where}: cannot read row: {s[:60]}")
            continue
        num, kind, rest = int(m.group(1)), KINDS[m.group(2)], m.group(3)
        if num != len(cur["rows"]) + 1:
            problems.append(f"{where}: row number {num}, expected {len(cur['rows']) + 1}")
        cells = [c.strip() for c in rest.split("|")]
        comment = ""
        if cells and cells[-1].startswith("#"):
            comment = cells.pop()[1:].strip()
        spec = ""
        if cells and cells[-1].startswith("="):
            spec = cells.pop()[1:]
        label = cells[0] if cells else ""
        notes = [n.strip() for n in re.split(r"[،,]", cells[1]) if n.strip()] if len(cells) > 1 else []
        vals = cells[2:]
        ncol = len(cur["columns"])
        if kind != "section" and len(vals) != ncol:
            problems.append(f"{where}: {len(vals)} value cells for {ncol} columns")
        row = {"id": f"r{num}", "kind": kind, "label_ar": label}
        if notes:
            row["notes"] = notes
        values = {}
        for col, v in zip(cur["columns"], vals):
            try:
                pv = gtlib.parse_value(v)
            except ValueError as e:
                problems.append(f"{where}: {e}")
                continue
            if pv is not None:
                values[col["id"]] = pv
        if values:
            row["values"] = values
        if comment:
            row["comment"] = comment
        cur["rows"].append(row)
        if spec:
            pending[-1].append((row, spec, where))
    for st, todo in zip(statements, pending):
        for row, spec, where in todo:
            try:
                row["sum_of"] = sum_refs(spec, len(st["rows"]))
            except ValueError as e:
                problems.append(f"{where}: {e}")
    gt = {"schema_version": "1.0", "filing_id": meta.get("filing_id", Path(path).stem)}
    inv = {}
    try:
        from make_workbook import inventory
        inv = inventory(gt["filing_id"])
    except SystemExit:
        pass
    gt["entity"] = meta.get("entity") or inv.get("entity", "")
    gt["source"] = {"sha256": inv.get("sha256", ""), "file": f"filings/{gt['filing_id']}.pdf"}
    if inv.get("public_source_url"):
        gt["source"]["url"] = inv["public_source_url"]
    for k in ("period_end", "report", "digits", "comment"):
        if meta.get(k):
            gt[k] = meta[k]
    if meta.get("consolidated"):
        gt["consolidated"] = meta["consolidated"].lower() == "yes"
    gt["annotator"] = meta.get("annotator", "annotator (unverified)")
    gt["statements"] = statements
    return gt, problems


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("draft")
    ap.add_argument("--out")
    ap.add_argument("--workbook", action="store_true", help="also write paper/annotation/FILING_ID.xlsx (yellow = to verify)")
    a = ap.parse_args()
    gt, problems = parse(a.draft)
    errors, warnings = gtlib.validate(gt)
    errors = problems + errors
    for e in errors:
        print("ERROR  ", e)
    for w in warnings:
        print("warning", w)
    st = gtlib.stats(gt)
    print(f"{gt['filing_id']}: {st} | {len(errors)} errors, {len(warnings)} warnings")
    out = Path(a.out or gtlib.PAPER / "drafts" / f"{gt['filing_id']}.json")
    gtlib.save(gt, out)
    print("wrote", out)
    if a.workbook:
        import make_workbook
        print("wrote", make_workbook.build(gt["filing_id"], gt, prefilled=True))
