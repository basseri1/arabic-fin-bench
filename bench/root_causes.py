"""Root causes of the fact errors of each system: our parsing, the way we run the model, or the model's own output.

1. Parsing. Each system's output is read with one parser for its format (HTML tables: Cohere Parse, dots.mocr, Chandra
   OCR 2; Markdown tables: Mistral OCR), without repairs of the model's output. The HTML parser now honours rowspan as
   well as colspan (2026-10-03). The common-base outcomes are compared with the earlier, colspan-only parser.
2. Rows without a label: whether the raw output row holds any Arabic text that the parser did not take as a label, and
   whether the label sits on a row of its own just above (a split label).
3. Label shifts (misplaced rows): what starts each run of consecutive shifted rows: figures written on a section
   heading's row, a label written on its own row just above (a wrapped or split label), or neither.
4. Period errors: the table has no header (and none to inherit), the header names no year, two printed columns share a
   year that the header does not separate, the header years do not line up with the columns of figures, or a header
   year maps to another period.
5. The way the model is run: the common-base outcomes of each configuration of dots.mocr and Chandra OCR 2, and, for
   dots.mocr, the pipeline stage at which labels are lost on the pages where the adopted output lacks them.
Writes bench/ROOT_CAUSES.md and bench/root_causes_summary.json.   usage: python bench/root_causes.py
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from rapidfuzz import fuzz

PAPER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PAPER / "bench"))
import common_subset as CS  # noqa: E402
import rq2_strict as R  # noqa: E402
import validate  # noqa: E402

CURRENT_PARSER = validate.parse_tables              # the parser in use (HTML with rowspan, or Markdown)

AR = re.compile(r"[ء-ي]{2,}")
FOUR = ["Cohere Parse", "Mistral OCR", "dots.mocr pipeline, seed 0", "Chandra OCR 2, own input size"]
CONFIGS = {"dots.mocr": ["dots_mocr_plain_s0", "dots_mocr_plain_s0_bm", "dots_mocr_clahe_s0_raw", "dots_mocr_clahe_s0",
                         "dots_mocr_clahe_s0_bm", "dots_mocr_clahe_s0_bm_ver"],
           "Chandra OCR 2": ["chandra2_plain", "chandra2_plain_ver", "chandra2_chandra_cap", "chandra2_chandra_cap_ver"]}
CONFIG_NOTE = {"dots_mocr_plain_s0": "200 dpi page", "dots_mocr_plain_s0_bm": "200 dpi + band-merge",
               "dots_mocr_clahe_s0_raw": "CLAHE", "dots_mocr_clahe_s0": "CLAHE + structure retry",
               "dots_mocr_clahe_s0_bm": "CLAHE + retry + band-merge", "dots_mocr_clahe_s0_bm_ver": "adopted (+ verification)",
               "chandra2_plain": "200 dpi page", "chandra2_plain_ver": "200 dpi + verification",
               "chandra2_chandra_cap": "own input size", "chandra2_chandra_cap_ver": "own input size + verification"}


def parse_tables_colspan_only(text):
    """The parser before 2026-10-03: colspan expanded, rowspan ignored (kept to measure what the fix changed)."""
    tables = []
    for tb in re.finditer(r"<table.*?</table>", text, flags=re.S | re.I):
        rows = []
        for tr in re.finditer(r"<tr.*?</tr>", tb.group(0), flags=re.S | re.I):
            cells = []
            for m in re.finditer(r"<t([dh])([^>]*)>(.*?)</t[dh]>", tr.group(0), flags=re.S | re.I):
                span = re.search(r'colspan\s*=\s*"?(\d+)', m.group(2)); n = int(span.group(1)) if span else 1
                cells.append(re.sub(r"<[^>]+>", " ", m.group(3)).strip()); cells.extend([""] * (n - 1))
            if cells:
                rows.append(cells)
        if rows:
            tables.append(rows)
    return tables if tables else CURRENT_PARSER(text)


def has_fig(row):
    return any(validate.cell_value(x) not in (None, 0.0) for x in row)


def run(run_name, test, tr, tc, second):
    cache = {}
    res = R.analyse(run_name, second, second, None, test, tr, tc, cache)
    recs = []
    o, _ = CS.outcomes(res, test, recs)
    return o, recs, cache


def no_label_rows(recs, cache, run_name, test):
    out = Counter()
    for r in recs:
        if not (r["outcome"] == "unresolved" and r["side"] == "row" and r["cell"].get("row_status") == "no label"):
            continue
        c = r["cell"]; d = cache[(run_name, r["filing"])][c["doc"]]; ri = d["raw"][c["i"]]
        if any(AR.search(x or "") for x in d["grid"][ri]):
            out["Arabic text in the row, not taken as a label"] += 1
            continue
        above = d["grid"][ri - 1] if ri > 0 else []
        if any(AR.search(x or "") for x in above) and not has_fig(above):
            gl = next(x for x in test[r["filing"]]["statements"][r["k"][0]]["rows"] if x["id"] == r["k"][1])
            lab = R.nlabel(" ".join(x for x in above if AR.search(x or "")))
            if lab and fuzz.partial_ratio(lab, R.nlabel(gl.get("label_ar", ""))) >= 80:
                out["label of this line on its own row just above"] += 1
                continue
        out["no label in the output row"] += 1
    return out


def shift_triggers(recs, cache, run_name, test):
    trig, byd = Counter(), defaultdict(list)
    for r in recs:
        if r["outcome"] == "misplaced" and r["side"] == "row":
            byd[(r["filing"], r["cell"]["doc"])].append(r)
    for (fid, di), rs in byd.items():
        d = cache[(run_name, fid)][di]
        idx = sorted({r["cell"]["i"] for r in rs})
        for i in [i for i in idx if i - 1 not in idx]:
            r = next(x for x in rs if x["cell"]["i"] == i)
            st = test[fid]["statements"][r["k"][0]]
            rk = tuple(r["cell"].get("row_key") or ())
            kind = next((x.get("kind") for x in st["rows"] if rk and x["id"] == rk[1]), None)
            ri = d["raw"][i]
            above = [g for g in (d["grid"][q] for q in range(max(0, ri - 2), ri)) if any(AR.search(x or "") for x in g) and not has_fig(g)]
            if kind == "section":
                trig["figures written on a heading's row"] += 1
            elif above:
                lab = R.nlabel(" ".join(x for x in above[-1] if AR.search(x or "")))
                sec = any(x.get("kind") == "section" and fuzz.ratio(R.nlabel(x.get("label_ar", "")), lab) >= 80 for x in st["rows"])
                trig["a heading on its own row just above" if sec else "a label on its own row just above (wrapped or split label)"] += 1
            else:
                trig["neither"] += 1
    return trig


def period_causes(recs, cache, run_name, test):
    out = Counter()
    for r in recs:
        if r["side"] != "column" or r["outcome"] not in ("unresolved", "misplaced"):
            continue
        c = r["cell"]; d = cache[(run_name, r["filing"])][c["doc"]]
        st = test[r["filing"]]["statements"][r["k"][0]]
        gyears = [x["period"][:4] for x in st["columns"] if x.get("period")]
        if not any(h.strip() for h in d["header"]):
            why = "no header (none to inherit)"
        elif not any(d["years"]):
            why = "header names no year"
        elif r["outcome"] == "unresolved" and len(set(gyears)) < len(gyears):
            why = "two printed columns share a year the header does not separate"
        elif len([d["years"][q] for q in d["subst"] if d["years"][q]]) != len(d["subst"]):
            why = "header years do not line up with the columns of figures"
        else:
            why = "header year maps to another period"
        out[f"{r['outcome']}: {why}"] += 1
    return out


def label_share(run_name, fid, st, p):
    f = R.RESULTS / run_name / f"{fid}_p{p:02d}.md"
    if not f.exists():
        return None
    raw = f.read_text(errors="replace")
    tables = " ".join(re.sub(r"<[^>]+>", " ", t) for t in re.findall(r"<table.*?</table>", raw, flags=re.S))
    labs = [x for x in (R.nlabel(r.get("label_ar", "")) for r in st["rows"] if r.get("kind") != "section") if len(x) >= 6]
    t = R.nlabel(tables)
    return sum(1 for x in labs if t and fuzz.partial_ratio(x, t) >= 90) / len(labs) if labs else None


def main():
    S = json.load(open(PAPER / "bench" / "rq2_strict_summary.json"))
    tr, tc = S["thresholds"]["row"], S["thresholds"]["col"]
    test = R.score.load_gt(str(PAPER / "gt"), "test")
    second = R.MAIN["dots.mocr pipeline, seed 0"][0]
    summary = dict(parser={}, no_label={}, shifts={}, periods={}, configs={}, dots_stages={})
    keys = ("complete", "unresolved: row", "misplaced: row", "unresolved: column", "misplaced: column", "misread or omitted")
    new_parse = CURRENT_PARSER
    for name in FOUR:
        rn = CS.SYSTEMS[name]
        validate.parse_tables = parse_tables_colspan_only
        o_old, _, _ = run(rn, test, tr, tc, second)
        validate.parse_tables = new_parse
        o, recs, cache = run(rn, test, tr, tc, second)
        summary["parser"][name] = {k: [o_old[k], o[k]] for k in keys}
        summary["no_label"][name] = dict(no_label_rows(recs, cache, rn, test))
        summary["shifts"][name] = dict(shift_triggers(recs, cache, rn, test))
        summary["periods"][name] = dict(period_causes(recs, cache, rn, test))
        print(name, "done", flush=True)
    for model, runs in CONFIGS.items():
        for rn in runs:
            o, _, _ = run(rn, test, tr, tc, second)
            n = o["eligible"]
            summary["configs"][rn] = {k: o[k] / n for k in keys} | {"value wrong or missing": (o["sign"] + o["misread or omitted"]) / n}
    stages = CONFIGS["dots.mocr"]
    for fid, gt in test.items():
        for st in gt["statements"]:
            if st["type"] == "changes_in_equity":
                continue
            for p in st["pages"]:
                s = {v: label_share(v, fid, st, p) for v in stages}
                if s[stages[-1]] is not None and s[stages[-1]] < 0.5:
                    summary["dots_stages"][f"{fid}_p{p:02d} ({st['type']})"] = s
    (PAPER / "bench" / "root_causes_summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")

    md = ["# Root causes of the fact errors", "", "Method: header of `bench/root_causes.py`. Common base of Table 10 (3,878 figures, test split).", "",
          "## 1. Parsing: one parser per output format", "",
          "| System | Output format | Complete | No row | Wrong row | No period | Wrong period | Value wrong or missing |", "|---|---|---|---|---|---|---|---|"]
    fmt = {"Cohere Parse": "HTML tables", "Mistral OCR": "Markdown tables", "dots.mocr pipeline, seed 0": "HTML tables (layout output)",
           "Chandra OCR 2, own input size": "HTML tables in layout blocks"}
    for name, v in summary["parser"].items():
        cell = lambda k: f"{v[k][0]} → {v[k][1]}" if v[k][0] != v[k][1] else f"{v[k][1]}"
        md.append(f"| {name} | {fmt[name]} | {cell('complete')} | {cell('unresolved: row')} | {cell('misplaced: row')} | "
                  f"{cell('unresolved: column')} | {cell('misplaced: column')} | {cell('misread or omitted')} |")
    md += ["", "Figures, colspan-only parser → parser with rowspan. Only Cohere Parse changes: its headers span rows (the "
           "notes heading covers the year rows), and ignoring rowspan put each year over the wrong column.", "",
           "## 2. Rows without a label", "", "| System | Rows without a label | Breakdown |", "|---|---:|---|"]
    for name, v in summary["no_label"].items():
        md.append(f"| {name} | {sum(v.values())} | " + "; ".join(f"{k}: {n}" for k, n in sorted(v.items(), key=lambda x: -x[1])) + " |")
    md += ["", "## 3. What starts a run of shifted labels", "", "| System | Runs | Breakdown |", "|---|---:|---|"]
    for name, v in summary["shifts"].items():
        n = sum(v.values())
        md.append(f"| {name} | {n} | " + "; ".join(f"{k}: {c} ({100 * c / n:.0f}%)" for k, c in sorted(v.items(), key=lambda x: -x[1])) + " |")
    md += ["", "## 4. Period errors", "", "| System | Figures | Breakdown |", "|---|---:|---|"]
    for name, v in summary["periods"].items():
        md.append(f"| {name} | {sum(v.values())} | " + "; ".join(f"{k}: {c}" for k, c in sorted(v.items(), key=lambda x: -x[1])) + " |")
    md += ["", "## 5. The way the model is run", "", "| Run | Setting | Complete | No row | Wrong row | No period | Wrong period | Value wrong or missing |",
           "|---|---|---:|---:|---:|---:|---:|---:|"]
    for rn, v in summary["configs"].items():
        md.append(f"| {rn} | {CONFIG_NOTE[rn]} | " + " | ".join(f"{100 * v[k]:.1f}%" for k in keys[:5]) + f" | {100 * v['value wrong or missing']:.1f}% |")
    md += ["", "dots.mocr: share of the printed labels found in its tables, on the statement pages where the adopted output "
           "has fewer than half:", "", "| Page | " + " | ".join(CONFIG_NOTE[v] for v in stages) + " |", "|---|" + "---:|" * len(stages)]
    for pg, s in summary["dots_stages"].items():
        md.append(f"| {pg} | " + " | ".join("–" if s[v] is None else f"{s[v]:.2f}" for v in stages) + " |")
    lost = [pg for pg, s in summary["dots_stages"].items() if (s[stages[0]] or 0) >= 0.5 or (s[stages[2]] or 0) >= 0.5]
    md += ["", f"On {len(summary['dots_stages'])} such pages, {len(lost)} had most labels in an earlier stage (lost to CLAHE or to the "
           "structure retry, which keeps the attempt with the most figures and never looks at labels); on the others no "
           "configuration writes the labels."]
    (PAPER / "bench" / "ROOT_CAUSES.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
