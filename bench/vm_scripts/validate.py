#!/usr/bin/env python
"""Arithmetic validation + correction for OCR'd financial statements (no ground truth used).

Per document (all its pages):
  1. Parse every table into a cell matrix (HTML with colspan and rowspan, or Markdown). Drop label/note columns.
  2. Relationships: a row whose value equals the sum of a contiguous block (>=2 rows) above it, in some column.
     The same block is then tested in every column.
  3. Anchors: cells inside a satisfied relationship, or whose value recurs elsewhere in the document
     (cross-statement), are trusted.
  4. Suspects: cells of a broken relationship that are not anchored.
  5. Fixes: (a) a unique single-digit edit (substitute/insert/delete) of one unanchored cell that repairs every
     broken relationship it belongs to; (b) label cross-reference: the same (normalized) label elsewhere in the
     document carries an anchored value within single-digit distance -> adopt it.
  6. Everything else stays flagged (for a second reader / re-OCR).
Usage: python validate.py <results_dir> [--doc aramco|maaden] [--apply <out_dir>] [--verbose]
"""
import sys, re, json, itertools
from pathlib import Path
from collections import Counter, defaultdict
sys.path.insert(0, str(Path(__file__).resolve().parent)); import eval2
from rapidfuzz import fuzz

AR_LETTERS = re.compile(r"[ء-ي]{2,}")

# ---------------------------------------------------------------- parsing
def parse_tables(text):
    """Tables as grids of cell texts. HTML: a cell spanning several columns (colspan) or rows (rowspan) keeps its
    text in its first position and leaves the positions it covers empty, so that every cell stays in its column.
    Markdown: rows of pipe-separated cells."""
    tables = []
    for tb in re.finditer(r"<table.*?</table>", text, flags=re.S | re.I):
        rows, covered = [], {}                         # covered[column] = rows still spanned by a cell above
        for tr in re.finditer(r"<tr.*?</tr>", tb.group(0), flags=re.S | re.I):
            cells = []
            def skip_covered():
                while covered.get(len(cells), 0) > 0:
                    covered[len(cells)] -= 1; cells.append("")
            for m in re.finditer(r"<t([dh])([^>]*)>(.*?)</t[dh]>", tr.group(0), flags=re.S | re.I):
                skip_covered()
                span = re.search(r'colspan\s*=\s*"?(\d+)', m.group(2)); n = int(span.group(1)) if span else 1
                down = re.search(r'rowspan\s*=\s*"?(\d+)', m.group(2)); down = int(down.group(1)) if down else 1
                txt = re.sub(r"<[^>]+>", " ", m.group(3)).strip()
                for q in range(n):
                    if down > 1: covered[len(cells)] = down - 1
                    cells.append(txt if q == 0 else "")
            skip_covered()
            if cells: rows.append(cells)
        if rows: tables.append(rows)
    if not tables:
        cur = []
        for line in text.splitlines():
            st = line.strip()
            if st.startswith("|"):
                cells = [c.strip() for c in st.strip("|").split("|")]
                if all(re.fullmatch(r":?-{2,}:?", c) or c == "" for c in cells): continue
                cur.append(cells)
            elif cur:
                tables.append(cur); cur = []
        if cur: tables.append(cur)
    return tables

def cell_value(c):
    cs = c.strip()
    if cs == "" or re.fullmatch(r"[-–—ـ\s]+", cs): return 0.0
    if AR_LETTERS.search(cs): return None
    n = eval2.numbers(cs, signed=True)
    return n[0] if len(n) == 1 else None

def matrix(rows):
    W = max(len(r) for r in rows); grid = [r + [""] * (W - len(r)) for r in rows]
    kinds = []
    for j in range(W):
        col = [g[j] for g in grid]; txt = sum(1 for c in col if AR_LETTERS.search(c))
        vals = [cell_value(c) for c in col]; nums = [v for v in vals if v not in (None, 0.0)]
        if txt >= max(2, 0.4 * len(col)) and txt >= len(nums): kinds.append("label"); continue
        if nums and sum(1 for v in nums if abs(v) < 100) >= 0.6 * len(nums): kinds.append("note"); continue
        kinds.append("data" if nums else "empty")
    cols = [j for j, k in enumerate(kinds) if k == "data"]
    mat = []
    for g in grid:
        label = " ".join(g[j] for j, k in enumerate(kinds) if k == "label" and g[j]).strip()
        vals = [cell_value(g[j]) for j in cols]
        if all(v is None for v in vals) or (all(v in (None, 0.0) for v in vals) and not label): continue
        mat.append([label, vals])
    return mat, len(cols)

# ---------------------------------------------------------------- relationships
def relationships(mat, width, tol=0.5):
    rels = set()
    for c in range(width):
        for t in range(1, len(mat)):
            tv = mat[t][1][c]
            if tv in (None, 0.0): continue
            s, cnt = 0.0, 0
            for k in range(t - 1, -1, -1):
                v = mat[k][1][c]
                if v is None: continue
                s += v; cnt += 1
                if cnt >= 2 and abs(s - tv) <= tol: rels.add((t, k, t - 1)); break
                if cnt > 60: break
    return rels

def block_status(mat, t, k, e, c, tol=0.5):
    tv = mat[t][1][c]; vals = [mat[i][1][c] for i in range(k, e + 1)]
    if tv is None or any(v is None for v in vals): return None
    return tv - sum(vals)

def digit_edits(v):
    s = f"{abs(int(round(v)))}"; neg = v < 0; out = set()
    for i in range(len(s)):
        for d in "0123456789":
            if d != s[i]: out.add(s[:i] + d + s[i+1:])
        if len(s) > 1: out.add(s[:i] + s[i+1:])
        for d in "0123456789": out.add(s[:i] + d + s[i:])
    for d in "0123456789": out.add(s + d)
    return {(-1 if neg else 1) * int(x) for x in out if x and (not x.startswith("0") or x == "0")}

def norm_label(l):
    return eval2.norm_ar(re.sub(r"[\d٠-٩(),.:\-]+", " ", l))

# ---------------------------------------------------------------- document-level validation
def validate_doc(results_dir, pages, verbose=False, second_dir=None):
    results_dir = Path(results_dir)
    second_pool = None
    if second_dir:
        second_pool = set()
        for pg in pages: second_pool |= second_reader_values(second_dir, pg)
    docs = []   # per page: list of (table_idx, mat, width, rels)
    for pg in pages:
        f = results_dir / f"{pg}.md"
        if not f.exists(): continue
        text = eval2.extract_text(f.read_text(errors="replace"))
        for ti, rows in enumerate(parse_tables(text)):
            mat, width = matrix(rows)
            if not mat or width == 0: continue
            docs.append({"page": pg, "table": ti, "mat": mat, "width": width, "rels": relationships(mat, width)})
    # value frequency across the document (cross-statement anchors)
    freq = Counter(abs(v) for d in docs for _, vals in d["mat"] for v in vals if v not in (None, 0.0))
    # anchored values by label (from satisfied relationships)
    anchored_by_label = defaultdict(list)
    report = {"fixes": [], "flags": [], "stats": {"tables": len(docs), "relationships": 0, "broken": 0}}
    for d in docs:
        mat, width, rels = d["mat"], d["width"], d["rels"]
        anchored = set(); broken = []
        for (t, k, e) in rels:
            status = {c: block_status(mat, t, k, e, c) for c in range(width)}
            def informative(c):
                tv = mat[t][1][c]; vals = [mat[i][1][c] for i in range(k, e + 1)]
                return tv not in (None, 0.0) or any(v not in (None, 0.0) for v in vals)
            testable = [c for c, d in status.items() if d is not None and informative(c)]
            ok = [c for c in testable if abs(status[c]) <= 0.5]
            if not testable or len(ok) < max(1, len(testable) / 2.0):   # coincidental sum, not structure
                continue
            for c in testable:
                report["stats"]["relationships"] += 1
                if abs(status[c]) <= 0.5:
                    for i in list(range(k, e + 1)) + [t]: anchored.add((i, c))
                else:
                    broken.append((t, k, e, c, status[c])); report["stats"]["broken"] += 1
        for i, (lab, vals) in enumerate(mat):
            for c, v in enumerate(vals):
                if v not in (None, 0.0) and freq[abs(v)] >= 2: anchored.add((i, c))
        for (i, c) in anchored:
            v = mat[i][1][c]
            if v not in (None, 0.0) and mat[i][0]: anchored_by_label[norm_label(mat[i][0])].append((id(d), c, abs(v)))
        d["anchored"], d["broken"] = anchored, broken
    # fixes
    for d in docs:
        mat, width = d["mat"], d["width"]
        cand_by_cell = defaultdict(list)
        for (t, k, e, c, diff) in d["broken"]:
            cells = [(i, c) for i in list(range(k, e + 1)) + [t] if (i, c) not in d["anchored"] and mat[i][1][c] not in (None,)]
            for (i, cc) in cells:
                v = mat[i][1][cc]
                if v is None: continue
                for cand in digit_edits(v):
                    # does this single edit repair every broken relationship this cell belongs to?
                    ok = True
                    for (t2, k2, e2, c2, _) in d["broken"]:
                        if c2 != cc or not (k2 <= i <= e2 or i == t2): continue
                        vals = [cand if j == i else mat[j][1][c2] for j in range(k2, e2 + 1)]
                        tv = cand if t2 == i else mat[t2][1][c2]
                        if tv is None or any(x is None for x in vals) or abs(tv - sum(vals)) > 0.5: ok = False; break
                    if ok: cand_by_cell[(i, cc)].append(cand)
        # unique-cell rule per broken block: accept only if exactly one cell in the block can repair it
        for (t, k, e, c, diff) in d["broken"]:
            repairers = [(i, c) for i in list(range(k, e + 1)) + [t] if cand_by_cell.get((i, c))]
            if len(repairers) == 1 and len(set(cand_by_cell[repairers[0]])) == 1:
                i, cc = repairers[0]; new = cand_by_cell[(i, cc)][0]; old = mat[i][1][cc]
                if old != new:
                    report["fixes"].append({"page": d["page"], "row": mat[i][0][:60], "col": cc, "from": old, "to": new, "rule": "arith-unique"})
                    mat[i][1][cc] = float(new); d["anchored"].add((i, cc))
            else:
                # label cross-reference for the unanchored cells of this block
                fixed = False
                for i in list(range(k, e + 1)) + [t]:
                    if (i, c) in d["anchored"]: continue
                    v = mat[i][1][c]; lab = norm_label(mat[i][0])
                    if v in (None, 0.0) or not lab: continue
                    for lab2, vals2 in anchored_by_label.items():
                        if fuzz.ratio(lab, lab2) < 90: continue
                        for (src, col2, av) in vals2:
                            if src == id(d): continue
                            if av != abs(v) and av in {abs(x) for x in digit_edits(v)}:
                                new = av if v >= 0 else -av
                                report["fixes"].append({"page": d["page"], "row": mat[i][0][:60], "col": c, "from": v, "to": new, "rule": "label-xref"})
                                mat[i][1][c] = float(new); d["anchored"].add((i, c)); fixed = True; break
                        if fixed: break
                    if fixed: break
                unanch = [i for i in list(range(k, e + 1)) + [t] if (i, c) not in d["anchored"]]
                if not fixed and second_pool is not None and unanch:
                    repairers = []
                    for i in unanch:
                        v = mat[i][1][c]
                        if v in (None, 0.0): continue
                        alts = {x for x in digit_edits(v) if abs(x) in second_pool and abs(x) != abs(v)}
                        for cand in alts:
                            cand = cand if v >= 0 else -abs(cand)
                            vals = [cand if j == i else mat[j][1][c] for j in range(k, e + 1)]
                            tv = cand if t == i else mat[t][1][c]
                            if tv is not None and all(x is not None for x in vals) and abs(tv - sum(vals)) <= 0.5:
                                repairers.append((i, cand))
                    if len(repairers) == 1:
                        i, cand = repairers[0]
                        report["fixes"].append({"page": d["page"], "row": mat[i][0][:60], "col": c, "from": mat[i][1][c], "to": cand, "rule": "second-reader"})
                        mat[i][1][c] = float(cand); d["anchored"].add((i, c)); fixed = True
                if not fixed and unanch:
                    report["flags"].append({"page": d["page"], "block": f"rows {k}-{e} -> total '{mat[t][0][:40]}'", "col": c, "diff": diff,
                                            "cells": [mat[i][0][:30] for i in range(k, e + 1) if (i, c) not in d["anchored"]][:8]})
    return report, docs

def _num_regex(v):
    digs = f"{abs(int(round(v)))}"
    ai = "".join(chr(0x660 + int(d)) for d in digs)
    pat_w = r"[,٬\s]?".join(re.escape(d) for d in digs)
    pat_a = r"[,٬\s]?".join(re.escape(d) for d in ai)
    return re.compile(rf"(?<![\d٠-٩])({pat_w}|{pat_a})(?![\d٠-٩])")

def _fmt_like(new_v, sample):
    s = f"{abs(int(round(new_v))):,}"
    return s.translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")) if re.search(r"[٠-٩]", sample) else s

def apply_fixes(results_dir, out_dir, pages, report):
    """Write corrected copies of the pages (number located by digit sequence, replaced in the same script)."""
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    by_page = defaultdict(list)
    for f in report["fixes"]: by_page[f["page"]].append(f)
    for pg in pages:
        src = Path(results_dir) / f"{pg}.md"
        if not src.exists(): continue
        t = src.read_text(errors="replace")
        for f in by_page.get(pg, []):
            m = _num_regex(f["from"]).search(t)
            if m: t = t[:m.start()] + _fmt_like(f["to"], m.group(0)) + t[m.end():]
        (out / f"{pg}.md").write_text(t)
    for extra in ("_timing.jsonl", "_meta.json"):
        if (Path(results_dir) / extra).exists(): (out / extra).write_text((Path(results_dir) / extra).read_text())

def second_reader_values(second_dir, page):
    """All numeric values a second model read on the same page (document-level pool is built by caller)."""
    f = Path(second_dir) / f"{page}.md"
    if not f.exists(): return set()
    text = eval2.extract_text(f.read_text(errors="replace"))
    return {abs(v) for v in eval2.numbers("\n".join(eval2.lines_of(text)), signed=False)}

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("results_dir"); ap.add_argument("--doc", default="both"); ap.add_argument("--apply", default=""); ap.add_argument("--verbose", action="store_true"); ap.add_argument("--second", default="")
    a = ap.parse_args()
    all_pages = {"aramco": ["aramco_p12", "aramco_p13", "aramco_p14", "aramco_p15", "aramco_p16"], "maaden": ["maaden_p11", "maaden_p12", "maaden_p13", "maaden_p14", "maaden_p15", "maaden_p16"],
                 "drilling": ["drilling_p08", "drilling_p09", "drilling_p10", "drilling_p11", "drilling_p12", "drilling_p13"]}
    docs = ["aramco", "maaden"] if a.doc == "both" else [a.doc]
    for doc in docs:
        rep, _ = validate_doc(a.results_dir, all_pages[doc], a.verbose, second_dir=a.second or None)
        print(f"== {doc}: tables {rep['stats']['tables']}, relationships checked {rep['stats']['relationships']}, broken {rep['stats']['broken']}, fixes {len(rep['fixes'])}, flags {len(rep['flags'])}")
        for f in rep["fixes"]: print(f"   FIX  [{f['page']}] {f['row'][:45]!r} col{f['col']}: {int(f['from']):,} -> {int(f['to']):,}  ({f['rule']})")
        for f in rep["flags"][:12]: print(f"   FLAG [{f['page']}] {f['block']} col{f['col']} diff={f['diff']:,.0f} cells={f['cells']}")
        if a.apply: apply_fixes(a.results_dir, a.apply, all_pages[doc], rep)
