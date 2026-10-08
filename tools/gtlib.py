"""Ground truth for Arabic financial-statement tables: load, validate, and convert to the scorer's structure.

One JSON file per filing (see schema.json). Cell values are signed numbers exactly as printed (parentheses become a
minus sign), the string "nil" for a printed dash, or absent for an empty cell. Scale and currency live on each
statement, so values are never rescaled.
"""
import json
import re
import sys
from pathlib import Path

import jsonschema

TOOLS = Path(__file__).resolve().parent
PAPER = TOOLS.parent
BENCH = Path("/path/to/DocProcess/ocr_benchmark")   # pilot Markdown sources (tools/md_to_json.py)
sys.path.insert(0, str(PAPER / "bench" / "vm_scripts"))                    # the benchmark's parsers
import eval2  # noqa: E402  (numbers() is the benchmark's own figure parser)

SCHEMA = json.loads((TOOLS / "schema.json").read_text(encoding="utf-8"))
AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹٫٬", "0123456789" "0123456789" ".,")


# ---------------------------------------------------------------- values
def parse_value(s):
    """Printed cell text -> signed number, "nil" (a dash) or None (empty). Raises ValueError otherwise."""
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return s
    t = str(s).strip().translate(AR_DIGITS).replace("‏", "").replace("‎", "")
    t = re.sub(r"[*_]", "", t).strip()
    if t == "":
        return None
    if re.fullmatch(r"[-–—−]+", t):
        return "nil"
    neg = t.startswith("(") and t.endswith(")")
    t = t.strip("()").strip()
    if t.startswith(("-", "−", "–")):
        neg, t = True, t[1:].strip()
    t = t.replace(",", "").replace("،", "").replace(" ", "")
    if not re.fullmatch(r"\d+(\.\d+)?", t):
        raise ValueError(f"not a figure: {s!r}")
    v = float(t) if "." in t else int(t)
    return -v if neg else v


def fmt_value(v):
    """Signed number -> the conventional printed form: (1,234) for negatives, - for nil."""
    if v is None:
        return ""
    if v == "nil":
        return "-"
    a = abs(v)
    body = f"{a:,}" if isinstance(a, float) and not a.is_integer() else f"{int(a):,}"
    return f"({body})" if v < 0 else body


# ---------------------------------------------------------------- io
def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(gt, path):
    Path(path).write_text(json.dumps(gt, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- validation
def _num(v):
    return 0 if v in (None, "nil") else v


def validate(gt, tol=1.0):
    """-> (errors, warnings). Errors make the file unusable; warnings deserve a look."""
    errors, warnings = [], []
    for e in sorted(jsonschema.Draft202012Validator(SCHEMA).iter_errors(gt), key=lambda e: list(e.path)):
        errors.append(f"schema: {'/'.join(str(p) for p in e.path) or '(root)'}: {e.message}")
    if errors:
        return errors, warnings
    seen_st = set()
    for st in gt["statements"]:
        sid = st["id"]
        if sid in seen_st:
            errors.append(f"{sid}: duplicate statement id")
        seen_st.add(sid)
        cols = [c["id"] for c in st["columns"]]
        if len(set(cols)) != len(cols):
            errors.append(f"{sid}: duplicate column ids")
        rows = {}
        for r in st["rows"]:
            if r["id"] in rows:
                errors.append(f"{sid}/{r['id']}: duplicate row id")
            rows[r["id"]] = r
            for c in (r.get("values") or {}):
                if c not in cols:
                    errors.append(f"{sid}/{r['id']}: value for unknown column {c!r}")
            if r["kind"] == "section" and r.get("values"):
                warnings.append(f"{sid}/{r['id']}: section row carries values")
            if r["kind"] in ("item", "subtotal", "total") and not r.get("values"):
                warnings.append(f"{sid}/{r['id']}: {r['kind']} row has no values")
        for r in st["rows"]:
            refs = r.get("sum_of") or []
            for ref in refs:
                if ref.lstrip("-") not in rows:
                    errors.append(f"{sid}/{r['id']}: sum_of references unknown row {ref!r}")
            if not refs or any(ref.lstrip("-") not in rows for ref in refs):
                continue
            for c in cols:
                v = (r.get("values") or {}).get(c)
                if v is None:
                    continue
                v = _num(v)                                  # a printed dash means zero
                exp = sum((-1 if ref.startswith("-") else 1) * _num((rows[ref.lstrip("-")].get("values") or {}).get(c))
                          for ref in refs)
                if abs(v - exp) > tol + 1e-9:
                    errors.append(f"{sid}/{r['id']} [{c}]: printed {fmt_value(v)} but its components sum to {fmt_value(exp)}")
        if len(st["rows"]) < 3:
            warnings.append(f"{sid}: only {len(st['rows'])} rows")
    return errors, warnings


def stats(gt):
    rows = figs = sums = 0
    for st in gt["statements"]:
        for r in st["rows"]:
            vals = [v for v in (r.get("values") or {}).values() if isinstance(v, (int, float))]
            if vals:
                rows += 1
                figs += len(vals)
            sums += bool(r.get("sum_of"))
    return {"statements": len(gt["statements"]), "rows": rows, "figures": figs, "checked_totals": sums}


# ---------------------------------------------------------------- scorer adapter
def to_eval_tables(gt):
    """Mirror eval2.parse_gt: one table per statement, rows with >=1 figure, allnums from every printed cell."""
    tables = []
    for st in gt["statements"]:
        cols = st["columns"]
        has_notes = any(r.get("notes") for r in st["rows"])
        header = ["البيان"] + (["إيضاح"] if has_notes else []) + [c.get("label", c["id"]) for c in cols]
        tb = {"header": header, "rows": [], "allnums": eval2.numbers(" ".join(header))}
        for r in st["rows"]:
            vals = [fmt_value((r.get("values") or {}).get(c["id"])) for c in cols]
            cells = [r.get("label_ar", "")] + (["، ".join(r.get("notes") or [])] if has_notes else []) + vals
            tb["allnums"] += eval2.numbers(" ".join(cells))
            figs = eval2.numbers(" ".join(vals), signed=True)
            if figs:
                tb["rows"].append({"label": r.get("label_ar", ""), "figs": figs})
        tables.append(tb)
    return tables
