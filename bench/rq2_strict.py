"""Strict evaluation of verification and routing (RQ2), answering an external review of the evaluation.

1. Facts, not values. A figure counts as a correct fact only when the output itself puts it in the right context: its
   row label resolves to the ground-truth row, its column header to the ground-truth column (the reporting period, or
   the component of an equity matrix), and its signed value equals that cell. Context is read from the output's own
   labels and headers, never from the values, so a swapped year or a misplaced row is an error even when the number
   exists elsewhere in the filing. A line printed without a label (a subtotal or total) has no line item to state, so
   a figure in an output row without a label states it correctly. Ground-truth cells are credited one to one. Rows are aligned in order (a monotone
   alignment of label similarities), so repeated labels, such as the two year blocks of an equity matrix, resolve by
   position. The similarity thresholds are chosen on the development split and then frozen.
2. Measures per decision rule: acceptance coverage, accepted-fact error rate, correct automatic recovery, error-
   detection recall, omission detection and total review workload.
3. Each verification component separately, on the token re-runs, where every component is available for the same
   outputs: accept everything; arithmetic only; agreement only; both (the rule fixed in the pilot); plus completeness
   checks; plus token probabilities. Also at a matched review budget of 10%.
4. Failures that can fool both checks: natural cases in the real outputs, and a synthetic challenge set reported
   separately.
5. Uncertainty that respects clustering by filing: a design-effect correction of the exact binomial bound, using the
   intra-filing correlation of errors, and the share of filings with an accepted error.

The figure filter, anchoring, engine agreement and tiers mirror bench/confidence32.py; a parity check at start-up
verifies that the figures and their signals are identical.
Writes bench/RQ2_STRICT.md and bench/rq2_strict_summary.json.   usage: python bench/rq2_strict.py
"""
import json
import math
import random
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from rapidfuzz import fuzz
from rapidfuzz.process import cdist

PAPER = Path(__file__).resolve().parents[1]
for _p in ("tools", "bench", "bench/vm_scripts"):
    sys.path.insert(0, str(PAPER / _p))
import confidence32 as C  # noqa: E402
import eval2  # noqa: E402
import score  # noqa: E402
import stats_rq  # noqa: E402
import validate  # noqa: E402

RESULTS = C.RESULTS
DIG = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
YEAR = re.compile(r"(?<!\d)(19[89]\d|20[0-4]\d)(?!\d)")
USD = re.compile(r"دولار|usd|\$", re.I)
SAR = re.compile(r"ريال|sar", re.I)
TOL = 0.0051                                   # values are compared after the shared parser's rounding to 2 decimals
BUDGET = 0.10
# delivered output -> (independent self-hosted engine, which is also the second reader of the row check; token directory)
MAIN = {"dots.mocr pipeline, seed 0": ("dots_mocr_clahe_s0_bm_ver", "chandra2_chandra_cap", None),
        "dots.mocr pipeline, seed 1": ("dots_mocr_clahe_s1_bm_ver", "chandra2_chandra_cap", None),
        "dots.mocr pipeline, seed 2": ("dots_mocr_clahe_s2_bm_ver", "chandra2_chandra_cap", None),
        "Chandra OCR 2, own input size": ("chandra2_chandra_cap_ver", "dots_mocr_clahe_s0_bm_ver", None)}
TOKEN = {"dots.mocr pipeline, seed 0 (token run)": ("dots_mocr_clahe_lp_s0_bm_ver", "chandra2_chandra_cap", "dots_mocr_clahe_lp_s0"),
         "Chandra OCR 2, own input size (token run)": ("chandra2_chandra_cap_lp_ver", "dots_mocr_clahe_s0_bm_ver", "chandra2_chandra_cap_lp")}


# ------------------------------------------------------------------ output tables with their context
def table_matrix(rows):
    """validate.matrix, also returning the padded grid, the column kinds, the data columns and each row's grid index."""
    W = max(len(r) for r in rows)
    grid = [list(r) + [""] * (W - len(r)) for r in rows]
    kinds = []
    for j in range(W):
        col = [g[j] for g in grid]
        txt = sum(1 for c in col if validate.AR_LETTERS.search(c))
        vals = [validate.cell_value(c) for c in col]
        nums = [v for v in vals if v not in (None, 0.0)]
        if txt >= max(2, 0.4 * len(col)) and txt >= len(nums):
            kinds.append("label"); continue
        if nums and sum(1 for v in nums if abs(v) < 100) >= 0.6 * len(nums):
            kinds.append("note"); continue
        kinds.append("data" if nums else "empty")
    cols = [j for j, k in enumerate(kinds) if k == "data"]
    mat, raw = [], []
    for ri, g in enumerate(grid):
        label = " ".join(g[j] for j, k in enumerate(kinds) if k == "label" and g[j]).strip()
        vals = [validate.cell_value(g[j]) for j in cols]
        if all(v is None for v in vals) or (all(v in (None, 0.0) for v in vals) and not label):
            continue
        mat.append([label, vals]); raw.append(ri)
    return dict(mat=mat, width=len(cols), grid=grid, cols=cols, kinds=kinds, raw=raw)


RANGE = re.compile(r"(?<![ء-ي])من(?![ء-ي]).*(?:الى|إلى|حتى)")


def year_of(text):
    """The period year a header cell states: its only year, or the end year of a 'from ... to ...' range."""
    t = text.translate(DIG)
    ys = YEAR.findall(t)
    if len(set(ys)) == 1:
        return ys[0]
    if ys and RANGE.search(t):
        return ys[-1]
    return None


def finish_doc(d):
    """Header text and period of each data column, from the rows above the first figure. When the header cells are
    shifted against the data columns (a common defect: a year row with one cell too few), but the year cells are as
    many as the columns that hold figures, the years are assigned to those columns in order, as a reader would."""
    first = next((d["raw"][i] for i, (_, vals) in enumerate(d["mat"]) if any(v is not None and C.is_figure(v) for v in vals)),
                 len(d["grid"]))
    d["first"] = first
    d["header"] = [" ".join(d["grid"][r][j] for r in range(first) if d["grid"][r][j]).strip() for j in d["cols"]]
    fig_rows = [vals for _, vals in d["mat"] if any(v is not None and C.is_figure(v) for v in vals)]
    d["subst"] = [c for c in range(d["width"]) if sum(1 for vals in fig_rows if vals[c] is not None and C.is_figure(vals[c])) >= 2]
    years = [year_of(h) for h in d["header"]]
    if not all(years[c] for c in d["subst"]):
        # fill missing years from the header row that holds the most year cells, in order, but only when it is as long as
        # the columns holding figures and agrees with every year the columns already state
        best = max((d["grid"][r] for r in range(first)), key=lambda row: sum(1 for x in row if year_of(x)), default=[])
        seq = [year_of(x) for x in best if year_of(x)]
        if seq and len(seq) == len(d["subst"]) and all(years[c] in (None, y) for c, y in zip(d["subst"], seq)):
            for c, y in zip(d["subst"], seq):
                years[c] = y
    d["years"] = years
    return d


def filing_docs(run, fid):
    docs = []
    for pg in C.pages_of(fid):
        f = RESULTS / run / f"{pg}.md"
        if not f.exists():
            continue
        text = eval2.extract_text(f.read_text(errors="replace"))
        for rows in validate.parse_tables(text):
            d = table_matrix(rows)
            if d["mat"] and d["width"]:
                d["page"] = pg
                docs.append(finish_doc(d))
    return docs


def signals(docs):
    """Anchored / suspect status of every figure, as confidence32.cell_signals, keeping each figure's position."""
    freq = Counter(abs(v) for d in docs for _, vals in d["mat"] for v in vals if v not in (None, 0.0))
    cells = []
    for di, d in enumerate(docs):
        mat, width = d["mat"], d["width"]
        anchored, in_broken = set(), set()
        for (t, k, e) in validate.relationships(mat, width):
            status = {c: validate.block_status(mat, t, k, e, c) for c in range(width)}
            informative = lambda c: mat[t][1][c] not in (None, 0.0) or any(mat[i][1][c] not in (None, 0.0) for i in range(k, e + 1))
            testable = [c for c, x in status.items() if x is not None and informative(c)]
            ok = [c for c in testable if abs(status[c]) <= 0.5]
            if not testable or len(ok) < max(1, len(testable) / 2.0):
                continue
            for c in testable:
                block = list(range(k, e + 1)) + [t]
                (anchored if abs(status[c]) <= 0.5 else in_broken).update((i, c) for i in block)
        for i, (_, vals) in enumerate(mat):
            for c, v in enumerate(vals):
                if v not in (None, 0.0) and freq[abs(v)] >= 2:
                    anchored.add((i, c))
        for i, (label, vals) in enumerate(mat):
            for c, v in enumerate(vals):
                if C.is_figure(v):
                    cells.append(dict(page=d["page"], doc=di, i=i, c=c, value=abs(v), signed=v, label=label,
                                      header=d["header"][c], anchored=(i, c) in anchored,
                                      suspect=(i, c) in in_broken and (i, c) not in anchored))
    return cells


def table_flag(d):
    """Ground-truth-free structure check of one table: fewer value columns than the periods in its header."""
    years = set(YEAR.findall(" ".join(d["header"]).translate(DIG)))
    expect = 2 if len(years) >= 2 else 1
    per_row = sorted(sum(1 for v in vals if v not in (None, 0.0) and abs(v) >= 1000) for _, vals in d["mat"])
    per_row = [n for n in per_row if n > 0]
    return len(d["mat"]) >= 5 and bool(per_row) and per_row[len(per_row) // 2] < expect


# ------------------------------------------------------------------ ground truth and context resolution
def nlabel(s):
    s = eval2.norm_ar((s or "").translate(DIG))
    s = re.sub(r"(\d{4})\s*م(?=\s|$)", r"\1", s)
    s = re.sub(r"(?<!\d)\d{1,3}(?!\d)", " ", s)          # note references; four-digit years stay
    return re.sub(r"\s+", " ", s).strip()


def gnorm(v):
    if not isinstance(v, (int, float)) or v == 0:
        return None
    return math.copysign(C.norm(v), v)


def gt_index(gt):
    sts = []
    for si, st in enumerate(gt["statements"]):
        cols = [dict(id=c["id"], year=(c.get("period") or "")[:4], label=nlabel(c.get("label", "")), cur=c.get("currency", ""))
                for c in st["columns"]]
        rows = [dict(id=r["id"], label=nlabel(r.get("label_ar", "")), values={k: gnorm(v) for k, v in (r.get("values") or {}).items()})
                for r in st["rows"]]
        sts.append(dict(i=si, type=st["type"], pages=set(st.get("pages", [])), cols=cols, rows=rows,
                        periodic=any(c["year"] for c in cols)))
    cells = {(st["i"], r["id"], c["id"]): r["values"].get(c["id"]) for st in sts for r in st["rows"] for c in st["cols"]}
    return sts, cells


def page_no(pg):
    return int(pg.rsplit("_p", 1)[1])


def align_rows(out_labels, cand, theta):
    """Monotone alignment of output rows to candidate ground-truth rows maximising total label similarity; pairs below
    theta are not allowed. Returns {output row: (statement, row id)}."""
    n, m = len(out_labels), len(cand)
    if not n or not m:
        return {}
    sim = cdist([l or "\x00" for l in out_labels], [r["label"] or "\x01" for _, r in cand], scorer=fuzz.ratio)
    S = np.zeros((n + 1, m + 1)); B = np.zeros((n + 1, m + 1), dtype=np.int8)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            best, bp = S[i - 1, j], 1
            if S[i, j - 1] > best:
                best, bp = S[i, j - 1], 2
            s = sim[i - 1, j - 1]
            if out_labels[i - 1] and s >= theta and S[i - 1, j - 1] + s > best:
                best, bp = S[i - 1, j - 1] + s, 3
            S[i, j], B[i, j] = best, bp
    out, i, j = {}, n, m
    while i > 0 and j > 0:
        if B[i, j] == 3:
            out[i - 1] = (cand[j - 1][0], cand[j - 1][1]["id"]); i, j = i - 1, j - 1
        elif B[i, j] == 1:
            i -= 1
        else:
            j -= 1
    return out


SPAN = {"ثلاث": 3, "ست": 6, "تسع": 9, "اثني عشر": 12, "سنه": 12}


def span_of(text):
    """The length of period a header or column label names (three, six, nine or twelve months), if exactly one."""
    found = {m for k, m in SPAN.items() if re.search(r"(?<![ء-ي])" + k, text)}
    return found.pop() if len(found) == 1 else None


def map_columns(d, st, theta_col):
    """Ground-truth column claimed by each data column of an output table, from its header only (never the values).
    Periods: when the header years of the columns holding figures match the statement's sequence of periods, in printed
    or reversed order, they map in order; otherwise each column maps by its year, and a year shared by several periods
    (three and six months, riyals and dollars) must be settled by the header's own words, or the column stays unresolved.
    Equity matrices: when the output has as many columns as the statement, they map in order, the direction chosen by
    header similarity; otherwise they stay unresolved."""
    out = [None] * d["width"]
    sub = d["subst"]
    if st["periodic"]:
        yo = [d["years"][c] for c in sub]
        yg = [x["year"] for x in st["cols"]]
        if yo and None not in yo and len(yo) == len(yg) and (yo == yg or yo == yg[::-1]):
            fwd = yo == yg
            if yo == yg[::-1] and yo == yg:         # symmetric sequences (e.g. 2023, 2022, 2022, 2023): decide by spans
                fwd = sum(span_of(nlabel(d["header"][c])) == span_of(x["label"]) for c, x in zip(sub, st["cols"])) >= \
                      sum(span_of(nlabel(d["header"][c])) == span_of(x["label"]) for c, x in zip(sub, st["cols"][::-1]))
            for c, x in zip(sub, st["cols"] if fwd else st["cols"][::-1]):
                out[c] = x["id"]
            return out
        for c in range(d["width"]):
            y, h = d["years"][c], d["header"][c]
            if not y:
                continue
            cands = [x for x in st["cols"] if x["year"] == y]
            if len(cands) > 1:
                ht = h.translate(DIG)
                cur = "USD" if USD.search(ht) else "SAR" if SAR.search(ht) else None
                if cur and len({x["cur"] for x in cands}) > 1:
                    cands = [x for x in cands if x["cur"] == cur]
            if len(cands) > 1:
                sp = span_of(nlabel(h))
                cands = [x for x in cands if sp and span_of(x["label"]) == sp]
            if len(cands) == 1:
                out[c] = cands[0]["id"]
    else:
        heads = [nlabel(d["header"][c]) for c in sub]
        gl = [x["label"] for x in st["cols"]]
        if sub and len(sub) == len(gl):
            f = sum(fuzz.token_set_ratio(h, g) for h, g in zip(heads, gl))
            b = sum(fuzz.token_set_ratio(h, g) for h, g in zip(heads, gl[::-1]))
            if max(f, b) >= theta_col * len(gl) * 0.75:
                for c, x in zip(sub, st["cols"] if f >= b else st["cols"][::-1]):
                    out[c] = x["id"]
                return out
        # when the output has a different number of columns, components are not guessed: the columns stay unresolved
    dup = {k for k, v in Counter(x for x in out if x).items() if v > 1}      # one to one: ambiguous claims resolve to neither
    return [None if x in dup else x for x in out]


def resolve(docs, sts, theta_row, theta_col):
    """Context claimed by the output, read from its own row labels and column headers (never from the values).
    Returns (rows, cols, doc_sts): rows[(doc, row)] = ("ok", (statement, row id)) or (reason, None); cols[doc] =
    {statement: [column id or None per data column]}; doc_sts[doc] = the statements the table belongs to."""
    rows, cols, doc_sts, last = {}, {}, {}, {}
    for di, d in enumerate(docs):
        pno = page_no(d["page"])
        cand_sts = [st for st in sts if pno in st["pages"]]
        cand = [(st["i"], r) for st in cand_sts for r in st["rows"]]
        labels = [nlabel(l) for l, _ in d["mat"]]
        rowmap = align_rows(labels, cand, theta_row)
        for i in range(len(d["mat"])):
            rows[(di, i)] = ("ok", rowmap[i]) if i in rowmap else (("no label" if not labels[i] else "label unmatched"), None)
        present = Counter(si for si, _ in rowmap.values())
        doc_sts[di] = [present.most_common(1)[0][0]] if present else [st["i"] for st in cand_sts]
        cols[di] = {}
        for si in set(doc_sts[di]) | set(present):
            cm = map_columns(d, sts[si], theta_col)
            if all(x is None for x in cm) and not any(h.strip() for h in d["header"]) and (si, d["width"]) in last:
                cm = last[(si, d["width"])]               # a continuation table without a header inherits the last one
            cols[di][si] = cm
            if any(cm):
                last[(si, d["width"])] = cm
    return rows, cols, doc_sts


ERRORS = {"wrong row", "wrong column", "sign", "wrong value"}
COMPLETE = {"correct", "duplicate"}
INCOMPLETE = {"correct, row not stated", "column not stated", "correct, column not assessed"}


def context_index(docs):
    """For the second engine: value -> [(normalised row label, period year)] as its own tables state them."""
    idx = defaultdict(list)
    for d in docs:
        for label, vals in d["mat"]:
            for c, v in enumerate(vals):
                if v is not None and C.is_figure(v):
                    idx[round(abs(v), 2)].append((nlabel(label), d["years"][c]))
    return idx


def context_agrees(cell, idx, theta_row):
    """The second engine reads the same value under a matching row label and, where both state one, the same period."""
    lab, yr = nlabel(cell["label"]), cell.get("year")
    if not lab:
        return False
    for l2, y2 in idx.get(round(cell["value"], 2), []):
        if l2 and fuzz.ratio(lab, l2) >= theta_row and (not yr or not y2 or yr == y2):
            return True
    return False


def classify(cells, resolved, gtc, sts, G):
    """Fact class of every emitted figure, in output order. Period or column: from the table header, for every figure.
    Row: from the row label, when the table row states one. A line printed without a label (a subtotal or total) is
    stated by an output row without a label. Ground-truth cells are credited one to one."""
    rows, cols, doc_sts = resolved
    credited = set()
    unlabeled = {st["i"]: [r["id"] for r in st["rows"] if not r["label"]] for st in sts}
    colvals = defaultdict(list)
    for (si, rid, cid), v in gtc.items():
        if v is not None:
            colvals[(si, cid)].append(v)
    rowvals = defaultdict(list)
    for (si, rid, cid), v in gtc.items():
        if v is not None:
            rowvals[(si, rid)].append(v)
    for cell in cells:
        v, va, di = cell["signed"], cell["value"], cell["doc"]
        value_ok = C.error_class(va, G) is None
        rstat, rkey = rows[(di, cell["i"])]
        if rkey and not sts[rkey[0]]["periodic"]:
            # equity matrices: two-level component headers cannot be resolved reliably, so only the row is assessed
            cell.update(value_ok=value_ok, row_status=rstat, ctx=None, claimed=[], row_key=rkey)
            rv = rowvals[(rkey[0], rkey[1])]
            if not value_ok:
                cell["fact"] = "wrong value"
            elif any(abs(g - v) <= TOL for g in rv):
                cell["fact"] = "correct, column not assessed"
            elif any(abs(abs(g) - va) <= TOL for g in rv):
                cell["fact"] = "sign"
            else:
                cell["fact"] = "wrong row"
            continue
        sts_c = [rkey[0]] if rkey else doc_sts[di]
        claimed = [(si, cols[di].get(si, [None] * (cell["c"] + 1))[cell["c"]]) for si in sts_c if sts[si]["periodic"]]
        claimed = [(si, cid) for si, cid in claimed if cid]
        cell.update(value_ok=value_ok, row_status=rstat, ctx=None, claimed=claimed, row_key=rkey)
        if not value_ok:
            cell["fact"] = "wrong value"; continue
        if not claimed:
            cell["fact"] = "column not stated"; continue
        inside = [g for k in claimed for g in colvals[k]]
        if not any(abs(g - v) <= TOL for g in inside):
            if any(abs(abs(g) - va) <= TOL for g in inside):
                cell["fact"] = "sign"
            else:
                cell["fact"] = "wrong column"            # the value belongs to another period or component
            continue
        if not rkey:
            blank = [(si, rid, cid) for si, cid in claimed for rid in unlabeled.get(si, ())
                     if (si, rid, cid) not in credited and gtc.get((si, rid, cid)) is not None
                     and abs(gtc[(si, rid, cid)] - v) <= TOL]
            if rstat == "no label" and blank:                # no label printed, none written: the row is stated
                cell.update(fact="correct", ctx=blank[0], row_key=blank[0][:2], row_status="unlabeled line")
                credited.add(blank[0])
                continue
            cell["fact"] = "correct, row not stated"; continue
        key = (rkey[0], rkey[1], dict(claimed).get(rkey[0]))
        g = gtc.get(key) if key[2] else None
        if g is not None and abs(g - v) <= TOL:
            cell["fact"] = "duplicate" if key in credited else "correct"
            cell["ctx"] = key
            credited.add(key)
        else:
            cell["fact"] = "wrong row"
    return credited


# ------------------------------------------------------------------ one output, all filings
def analyse(run, engine, second, tok_dir, gts, theta_row, theta_col, docs_cache=None):
    out = dict(cells=[], gt_scope=0, statements=[], filings={})
    for fid, gt in gts.items():
        docs = docs_cache[(run, fid)] if docs_cache is not None and (run, fid) in docs_cache else filing_docs(run, fid)
        if docs_cache is not None:
            docs_cache[(run, fid)] = docs
        cells = signals(docs)
        pool = C.value_pool(RESULTS / engine, C.pages_of(fid))
        tix = {pg: C.token_index(RESULTS / tok_dir, pg) for pg in C.pages_of(fid)} if tok_dir else {}
        tflag = {di: table_flag(d) for di, d in enumerate(docs)}
        fflag = stats_rq.row_disagreement(run, second, fid) > stats_rq.TAU_ROWS
        sts, gtc = gt_index(gt)
        G = C.gt_values(gt)
        resolved = resolve(docs, sts, theta_row, theta_col)
        cidx = context_index(filing_docs(engine, fid))
        for cell in cells:
            ti = tix.get(cell["page"])
            cell["year"] = docs[cell["doc"]]["years"][cell["c"]]
            cell["ctx_agree"] = context_agrees(cell, cidx, theta_row)
            cell.update(filing=fid, engine=cell["value"] in pool, p_min=ti.get(cell["value"]) if ti else None,
                        has_label=bool(cell["label"].strip()), has_header=bool(re.search(r"[\d٠-٩]{4}|[ء-ي]", cell["header"])),
                        table_flag=tflag[cell["doc"]], filing_flag=fflag)
        classify(cells, resolved, gtc, sts, G)
        out["cells"] += cells
        scope = {k for k, v in gtc.items() if v is not None and C.is_figure(v)}
        out["gt_scope"] += len(scope)
        out["filings"][fid] = dict(scope=scope, flag=fflag, pages_flag={docs[di]["page"] for di, f in tflag.items() if f})
        for st in sts:                                        # omissions, by value, one to one on the statement's pages
            sc = Counter(round(abs(gtc[(st["i"], r["id"], c["id"])]), 2) for r in st["rows"] for c in st["cols"]
                         if (st["i"], r["id"], c["id"]) in scope)
            emitted = Counter(round(cell["value"], 2) for cell in cells if page_no(cell["page"]) in st["pages"])
            missing = sum((sc - emitted).values())
            n = sum(sc.values())
            pages = {f"{fid}_p{p:02d}" for p in st["pages"]}
            out["statements"].append(dict(filing=fid, st=st["i"], n=n, missing=missing,
                                          omission=n > 0 and missing >= max(1, 0.05 * n),
                                          doc_flag=fflag or bool(pages & out["filings"][fid]["pages_flag"])))
    return out


# ------------------------------------------------------------------ decision rules and measures
RULES = {
    "accept everything": lambda c: True,
    "arithmetic only": lambda c: c["anchored"],
    "agreement only": lambda c: c["engine"],
    "arithmetic + agreement (rule fixed in the pilot)": lambda c: c["anchored"] and c["engine"],
    "+ completeness checks": lambda c: c["anchored"] and c["engine"] and c["has_label"] and c["has_header"]
                                       and not c["table_flag"] and not c["filing_flag"],
    "+ context agreement": lambda c: c["anchored"] and c["engine"] and c["has_label"] and c["has_header"]
                                     and not c["table_flag"] and not c["filing_flag"] and c["ctx_agree"],
    "+ token probabilities": lambda c: c["anchored"] and c["engine"] and c["has_label"] and c["has_header"]
                                       and not c["table_flag"] and not c["filing_flag"] and c["ctx_agree"]
                                       and not (c["p_min"] is not None and c["p_min"] < 0.95),
}
DOC_LEVEL = {"+ completeness checks", "+ context agreement", "+ token probabilities"}


def cp_upper(k, n, alpha=0.05):
    """Exact one-sided upper bound for a binomial proportion (Clopper-Pearson), in its beta-quantile form."""
    from scipy.stats import beta
    if n <= 0:
        return float("nan")
    if k >= n:
        return 1.0
    return float(beta.ppf(1 - alpha, k + 1, n - k))


def icc(groups):
    """ANOVA estimator of the intra-class correlation of a binary outcome (errors clustered by filing)."""
    groups = [g for g in groups if g]
    k, N = len(groups), sum(len(g) for g in groups)
    if k < 2 or N <= k:
        return 0.0
    mean = sum(sum(g) for g in groups) / N
    ssb = sum(len(g) * (sum(g) / len(g) - mean) ** 2 for g in groups)
    ssw = sum(sum((x - sum(g) / len(g)) ** 2 for x in g) for g in groups)
    msb, msw = ssb / (k - 1), ssw / (N - k)
    m0 = (N - sum(len(g) ** 2 for g in groups) / N) / (k - 1)
    den = msb + (m0 - 1) * msw
    return max(0.0, (msb - msw) / den) if den > 0 else 0.0


def measures(res, rule, rho, doc_level):
    cells = res["cells"]
    acc = [c for c in cells if RULES[rule](c)]
    wrong = [c for c in cells if c["fact"] in ERRORS]
    acc_wrong = [c for c in acc if c["fact"] in ERRORS]
    acc_incomplete = [c for c in acc if c["fact"] in INCOMPLETE]
    acc_value_wrong = [c for c in acc if not c["value_ok"]]
    # facts, as the authors define them (3 Oct 2026): a figure is right only as a complete fact; every other outcome,
    # a row or period that is not stated included, is wrong. Equity-matrix columns, which the scorer does not resolve,
    # are not assessable and are left out of these rates.
    assessable = [c for c in acc if c["fact"] != "correct, column not assessed"]
    acc_wrong_fact = [c for c in assessable if c["fact"] not in COMPLETE]
    wrong_fact = [c for c in cells if c["fact"] not in COMPLETE and c["fact"] != "correct, column not assessed"]
    credited = {(c["filing"], c["ctx"]) for c in acc if c["fact"] == "correct"}
    n_acc = len(acc)
    by_f = defaultdict(int)
    for c in acc:
        by_f[c["filing"]] += 1
    mbar = n_acc / max(1, len(by_f))
    deff = 1 + max(0.0, mbar - 1) * rho
    n_eff, k_eff = n_acc / deff, len(acc_wrong) / deff
    filings_with_err = len({c["filing"] for c in acc_wrong})
    oms = [s for s in res["statements"] if s["omission"]]
    detected = [s for s in oms if doc_level and s["doc_flag"]]
    # review workload: figures sent to review, plus every in-scope figure of a filing flagged at document level, plus
    # the in-scope figures of statements on a flagged table's page (no double counting)
    review_fig = defaultdict(int)
    for c in cells:
        if not RULES[rule](c):
            review_fig[c["filing"]] += 1
    workload = 0
    for fid, fr in res["filings"].items():
        if doc_level and fr["flag"]:
            workload += max(len(fr["scope"]), sum(1 for c in cells if c["filing"] == fid))
        else:
            workload += review_fig[fid]
            if doc_level and fr["pages_flag"]:
                workload += sum(s["n"] for s in res["statements"] if s["filing"] == fid and s["doc_flag"])
    return dict(
        rule=rule, emitted=len(cells), accepted=n_acc, coverage=n_acc / len(cells),
        acc_err=len(acc_wrong) / n_acc if n_acc else float("nan"), acc_err_n=len(acc_wrong),
        acc_value_err=len(acc_value_wrong) / n_acc if n_acc else float("nan"),
        acc_classes=dict(Counter(c["fact"] for c in acc_wrong)),
        acc_incomplete=len(acc_incomplete) / n_acc if n_acc else float("nan"),
        recovery_vp=(len(credited) + sum(1 for c in acc if c["fact"] in ("correct, row not stated", "correct, column not assessed"))) / res["gt_scope"],
        ub_naive=cp_upper(len(acc_wrong), n_acc), ub_cluster=cp_upper(round(k_eff), max(1, round(n_eff))),
        deff=deff, filings_err=filings_with_err, filings=len(res["filings"]),
        ub_filings=cp_upper(filings_with_err, len(res["filings"])),
        recovery=len(credited) / res["gt_scope"], detect=sum(1 for c in wrong if not RULES[rule](c)) / len(wrong) if wrong else float("nan"),
        omissions=len(oms), omissions_detected=len(detected), workload=workload / res["gt_scope"],
        fact_assessable=len(assessable), fact_err=len(acc_wrong_fact) / len(assessable) if assessable else float("nan"),
        fact_err_classes=dict(Counter(c["fact"] for c in acc_wrong_fact)),
        fact_detect=sum(1 for c in wrong_fact if not RULES[rule](c)) / len(wrong_fact) if wrong_fact else float("nan"))


def budget_error(cells, key, budget=BUDGET, facts=False):
    """Strict accepted-fact error when the (1 - budget) highest-ranked figures are accepted; ties at the boundary are
    accepted in proportion (the expected error of a random choice among them). facts=True: every outcome other than a
    complete fact counts as wrong, and equity-matrix columns (not assessable) are left out."""
    if facts:
        cells = [c for c in cells if c["fact"] != "correct, column not assessed"]
    groups = defaultdict(list)
    for c in cells:
        groups[key(c)].append(c)
    target = (1 - budget) * len(cells)
    acc = wrong = 0.0
    for k in sorted(groups, reverse=True):
        g = groups[k]
        w = sum(1 for c in g if ((c["fact"] not in COMPLETE) if facts else (c["fact"] in ERRORS)))
        take = min(len(g), target - acc)
        if take <= 0:
            break
        acc += take; wrong += w * take / len(g)
    return wrong / acc if acc else float("nan")


RANKINGS = {
    "arithmetic only": lambda c: (not c["suspect"], c["anchored"]),
    "agreement only": lambda c: (c["engine"],),
    "arithmetic + agreement (rule fixed in the pilot)": lambda c: (not c["suspect"], c["anchored"], c["engine"]),
    "+ completeness checks": lambda c: (not c["filing_flag"] and not c["table_flag"], c["has_label"] and c["has_header"],
                                        not c["suspect"], c["anchored"], c["engine"]),
    "+ context agreement": lambda c: (not c["filing_flag"] and not c["table_flag"], c["has_label"] and c["has_header"],
                                      c["ctx_agree"], not c["suspect"], c["anchored"], c["engine"]),
    "+ token probabilities": lambda c: (not c["filing_flag"] and not c["table_flag"], c["has_label"] and c["has_header"],
                                        c["ctx_agree"], not c["suspect"], c["anchored"], c["engine"],
                                        c["p_min"] if c["p_min"] is not None else 1.0),
}


# ------------------------------------------------------------------ thresholds, chosen on the development split
def resolver_check(res, gts):
    """Figures whose value occurs exactly once in the filing's ground truth have a known cell. Does the context the
    output states (column from the header; row from the label, when stated) point to it?"""
    where = {}
    for fid, gt in gts.items():
        sts, gtc = gt_index(gt)
        cnt = Counter(round(abs(v), 2) for v in gtc.values() if v is not None)
        where[fid] = {round(abs(v), 2): k for k, v in gtc.items() if v is not None and cnt[round(abs(v), 2)] == 1}
    right = wrong = unresolved = 0
    examples = []
    for c in res["cells"]:
        k = where[c["filing"]].get(round(c["value"], 2))
        if k is None or not c["value_ok"]:
            continue
        claimed, rk = c.get("claimed") or [], c.get("row_key")
        if not claimed and not rk:
            unresolved += 1
        elif (claimed and (k[0], k[2]) not in claimed) or (rk and rk != (k[0], k[1])):
            wrong += 1
            examples.append((c, k))
        else:
            right += 1
    res["resolver_wrong"] = examples
    return right, wrong, unresolved


# ------------------------------------------------------------------ synthetic challenge set
def fmt_cell(v):
    s = f"{abs(v):,.2f}".rstrip("0").rstrip(".") if v != int(v) else f"{abs(int(v)):,}"
    return f"({s})" if v < 0 else s


def one_digit_wrong(v):
    s = str(int(abs(v)))
    i = s.find("5")
    t = s[:i] + "0" + s[i + 1:] if i >= 0 else s[:-1] + str((int(s[-1]) + 1) % 10)
    return math.copysign(int(t), v)


def rebuild(d):
    nd = table_matrix(d["grid"])
    nd["page"] = d["page"]
    return finish_doc(nd)


def challenge(run, engine, second, gts, theta_row, theta_col, seed=7, per_filing=2):
    """Inject known errors into the real output, one at a time, and record whether each reaches the accepted set."""
    rng = random.Random(seed)
    kinds = ["period swap (one row)", "period swap (whole table)", "dropped negative", "shifted labels",
             "same digit error in both engines", "dropped column"]
    res = {k: Counter() for k in kinds}
    second_rows = {}
    for fid, gt in sorted(gts.items()):
        base = filing_docs(run, fid)
        pool0 = C.value_pool(RESULTS / engine, C.pages_of(fid))
        sts, gtc = gt_index(gt)
        G = C.gt_values(gt)
        if fid not in second_rows:
            second_rows[fid] = stats_rq.row_tuples(second, fid)
        Q = second_rows[fid]
        cidx = context_index(filing_docs(engine, fid))
        def row_flag(docs):
            P = [Counter(abs(v) for v in vals if v is not None and C.is_figure(v)) for d in docs for _, vals in d["mat"]]
            P = [p for p in P if sum(p.values()) >= 2]
            return (sum(1 for q in Q if not any(not (q - x) for x in P)) / len(Q) if Q else 0.0) > stats_rq.TAU_ROWS
        flag0 = row_flag(base)
        two_col = [di for di, d in enumerate(base) if d["width"] >= 2 and
                   len({YEAR.findall(h.translate(DIG))[0] for h in d["header"] if YEAR.findall(h.translate(DIG))}) >= 2]
        for kind in kinds:
            for _ in range(per_filing):
                docs = [dict(d, grid=[list(r) for r in d["grid"]]) for d in base]
                pool = set(pool0)
                targets = []            # (doc index, grid row, grid column) of the injected cells
                if kind.startswith("period swap") or kind == "dropped column":
                    if not two_col:
                        break
                    di = rng.choice(two_col); d = docs[di]
                    yc = [k for k, h in enumerate(d["header"]) if YEAR.findall(h.translate(DIG))][:2]
                    j1, j2 = d["cols"][yc[0]], d["cols"][yc[1]]
                    rows = [d["raw"][i] for i, (_, vals) in enumerate(d["mat"])
                            if all(vals[k] is not None and C.is_figure(vals[k]) for k in yc) and vals[yc[0]] != vals[yc[1]]]
                    if not rows:
                        continue
                    pick = [rng.choice(rows)] if kind == "period swap (one row)" else rows
                    for r in pick:
                        if kind == "dropped column":
                            d["grid"][r][j2] = ""
                        else:
                            d["grid"][r][j1], d["grid"][r][j2] = d["grid"][r][j2], d["grid"][r][j1]
                            targets += [(di, r, j1), (di, r, j2)]
                    if kind == "dropped column":
                        targets = [(di, None, None)]
                elif kind == "dropped negative":
                    opts = [(di, d["raw"][i], d["cols"][c]) for di, d in enumerate(docs) for i, (_, vals) in enumerate(d["mat"])
                            for c, v in enumerate(vals) if v is not None and v < 0 and C.is_figure(v)]
                    if not opts:
                        break
                    di, r, j = rng.choice(opts)
                    docs[di]["grid"][r][j] = re.sub(r"[()\-−–]", "", docs[di]["grid"][r][j]).strip()
                    targets = [(di, r, j)]
                elif kind == "shifted labels":
                    opts = []
                    for di, d in enumerate(docs):
                        lab = [j for j, k in enumerate(d["kinds"]) if k == "label"]
                        if not lab:
                            continue
                        idx = [i for i, (l, vals) in enumerate(d["mat"]) if l and any(v is not None and C.is_figure(v) for v in vals)]
                        for a in range(len(idx) - 2):
                            if idx[a + 2] - idx[a] == 2:
                                opts.append((di, lab[0], [d["raw"][x] for x in idx[a:a + 3]]))
                    if not opts:
                        break
                    di, lj, rr = rng.choice(opts)
                    g = docs[di]["grid"]
                    labs = [g[r][lj] for r in rr]
                    for r, l in zip(rr, labs[1:] + labs[:1]):
                        g[r][lj] = l
                    targets = [(di, r, j) for r in rr for j in docs[di]["cols"]]
                elif kind == "same digit error in both engines":
                    opts = [(di, d["raw"][i], d["cols"][c], v) for di, d in enumerate(docs) for i, (_, vals) in enumerate(d["mat"])
                            for c, v in enumerate(vals) if v is not None and C.is_figure(v) and v == int(v) and abs(v) in pool]
                    if not opts:
                        break
                    di, r, j, v = rng.choice(opts)
                    w = one_digit_wrong(v)
                    docs[di]["grid"][r][j] = fmt_cell(w)
                    pool.add(abs(w))
                    targets = [(di, r, j)]
                docs = [rebuild(d) for d in docs]
                cells = signals(docs)
                tflag = {di: table_flag(d) for di, d in enumerate(docs)}
                fflag = row_flag(docs)
                resolved = resolve(docs, sts, theta_row, theta_col)
                for cell in cells:
                    cell["year"] = docs[cell["doc"]]["years"][cell["c"]]
                    cell["ctx_agree"] = context_agrees(cell, cidx, theta_row) if kind != "same digit error in both engines" \
                        or (cell["doc"], docs[cell["doc"]]["raw"][cell["i"]], docs[cell["doc"]]["cols"][cell["c"]]) not in set(targets) \
                        else True   # the injected error is made by both engines in the same place
                    cell.update(filing=fid, engine=cell["value"] in pool, p_min=None, has_label=bool(cell["label"].strip()),
                                has_header=bool(re.search(r"[\d٠-٩]{4}|[ء-ي]", cell["header"])),
                                table_flag=tflag[cell["doc"]], filing_flag=fflag)
                classify(cells, resolved, gtc, sts, G)
                res[kind]["instances"] += 1
                if kind == "dropped column":
                    di = targets[0][0]
                    res[kind]["caught, completeness"] += int(fflag or tflag.get(di, False))
                    res[kind]["already flagged"] += int(flag0)
                    continue
                hit = [c for c in cells if (c["doc"], docs[c["doc"]]["raw"][c["i"]], docs[c["doc"]]["cols"][c["c"]]) in set(targets)]
                bad = [c for c in hit if c["fact"] in ERRORS]
                if not bad:
                    res[kind]["no error left"] += 1            # e.g. a swap of two equal cells, or labels that resolve alike
                    continue
                res[kind]["scored as errors"] += 1
                res[kind]["accepted, pilot rule"] += int(any(RULES["arithmetic + agreement (rule fixed in the pilot)"](c) for c in bad))
                res[kind]["accepted, + completeness"] += int(any(RULES["+ completeness checks"](c) for c in bad))
                res[kind]["accepted, + context agreement"] += int(any(RULES["+ context agreement"](c) for c in bad))
    return {k: dict(v) for k, v in res.items()}


# ------------------------------------------------------------------ main
def pct(x, d=1):
    return "–" if x != x else f"{100 * x:.{d}f}%"


def main():
    test = score.load_gt(str(PAPER / "gt"), "test")
    dev = score.load_gt(str(PAPER / "gt"), "dev")
    cache = {}
    # parity with bench/confidence32.py: the same figures with the same signals
    for label, (run, engine, _) in MAIN.items():
        for fid in list(test)[:6]:
            a = sorted((c["page"], c["value"], c["anchored"], c["suspect"]) for c in signals(filing_docs(run, fid)))
            b = sorted((c["page"], c["value"], c["anchored"], c["suspect"]) for c in C.cell_signals(RESULTS / run, C.pages_of(fid)))
            assert a == b, f"parity failure: {label} {fid}"
    print("parity with confidence32: ok", flush=True)

    # thresholds on the development split: maximise (resolved right - resolved wrong) on unique-value figures
    grid = [(tr, tc) for tr in (70, 80, 90) for tc in (70, 80, 90)]
    tune = {}
    for tr, tc in grid:
        r = w = u = 0
        for label in ("dots.mocr pipeline, seed 0", "Chandra OCR 2, own input size"):
            run, engine, tok = MAIN[label]
            res = analyse(run, engine, engine, tok, dev, tr, tc, cache)
            a, b, c = resolver_check(res, dev)
            r, w, u = r + a, w + b, u + c
        tune[(tr, tc)] = (r, w, u)
        print("dev thresholds", tr, tc, "right", r, "wrong", w, "unresolved", u, flush=True)
    theta_row, theta_col = max(tune, key=lambda k: tune[k][0] - tune[k][1])
    print("chosen on dev:", theta_row, theta_col, flush=True)

    summary = dict(thresholds=dict(row=theta_row, col=theta_col, dev_grid={f"{a},{b}": v for (a, b), v in tune.items()}),
                   main={}, ablation={}, budget={}, natural={}, challenge={}, resolver={})
    lines = ["# RQ2, strict: facts in context, components, missing information and blind spots", "",
             "Method: header of `bench/rq2_strict.py`. Held-out test split (22 filings) unless stated. A figure is a "
             "**correct fact** when the output's own row label and column header resolve to the ground-truth cell and the "
             "signed value equals it (one to one).", "",
             "Column identity is assessed in statements whose columns are periods; in equity matrices, whose two-level "
             "component headers could not be resolved reliably, only the row is assessed (this restriction was added after "
             "inspecting test outputs of a commercial reference; it can only lower error counts).", "",
             f"Context thresholds chosen on the development split: row-label similarity {theta_row}, column-header "
             f"similarity {theta_col} (grid of 70/80/90 each; objective: unique-value figures resolved to their own cell "
             "minus those resolved elsewhere).", ""]

    # ---- main runs: facts vs values, measures for the rule fixed in the pilot
    lines += ["## 1. Facts versus values (rule fixed in the pilot: arithmetic + agreement)", "",
              "| Output | Figures | Value right | Complete, correct facts | Correct, row not stated | Correct, column not assessed | Column not stated | Wrong column | Wrong row | Sign | Wrong value |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    mains = {}
    for label, (run, engine, tok) in MAIN.items():
        res = analyse(run, engine, engine, tok, test, theta_row, theta_col, cache)
        mains[label] = res
        cells = res["cells"]; n = len(cells); k = Counter(c["fact"] for c in cells)
        lines.append(f"| {label} | {n:,} | {pct(sum(c['value_ok'] for c in cells) / n)} | {pct((k['correct'] + k['duplicate']) / n)} | "
                     f"{pct(k['correct, row not stated'] / n)} | {pct(k['correct, column not assessed'] / n)} | {pct(k['column not stated'] / n)} | "
                     f"{pct(k['wrong column'] / n)} | {pct(k['wrong row'] / n)} | {pct(k['sign'] / n)} | {pct(k['wrong value'] / n)} |")
        right, wrong, unres = resolver_check(res, test)
        summary["resolver"][label] = dict(right=right, wrong=wrong, unresolved=unres)
    lines += ["", "Resolver check on the test split (figures whose value occurs once in the filing, so their cell is known): "
              + "; ".join(f"{l}: {v['right']} resolved to their cell, {v['wrong']} elsewhere, {v['unresolved']} unresolved"
                          for l, v in summary["resolver"].items()) + ".", ""]

    lines += ["### 1b. Fact-level reading of the leading systems (all emitted figures, test split)", "",
              "| System | Figures | Value right | Complete, correct facts | Correct, row not stated | Correct, column not assessed | Column not stated | Wrong column | Wrong row | Sign | Wrong value | Ground-truth figures recovered as complete facts |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    leaders = {"Mistral OCR": "mistral_ocr_plain", "Cohere Parse": "cohere_parse_plain", "LandingAI ADE": "landingai_ade_plain",
               "dots.mocr pipeline, seed 0": MAIN["dots.mocr pipeline, seed 0"][0], "Chandra OCR 2, own input size": MAIN["Chandra OCR 2, own input size"][0]}
    summary["leaders"] = {}
    for name, run in leaders.items():
        res = mains.get(name) or analyse(run, MAIN["dots.mocr pipeline, seed 0"][0], MAIN["dots.mocr pipeline, seed 0"][0], None, test,
                                         theta_row, theta_col, cache)
        cells = res["cells"]; n = len(cells); k = Counter(c["fact"] for c in cells)
        rec = len({(c["filing"], c["ctx"]) for c in cells if c["fact"] == "correct"}) / res["gt_scope"]
        summary["leaders"][name] = dict(figures=n, classes=dict(k), value_ok=sum(c["value_ok"] for c in cells) / n, recovered_complete=rec)
        lines.append(f"| {name} | {n:,} | {pct(sum(c['value_ok'] for c in cells) / n)} | {pct((k['correct'] + k['duplicate']) / n)} | "
                     f"{pct(k['correct, row not stated'] / n)} | {pct(k['correct, column not assessed'] / n)} | {pct(k['column not stated'] / n)} | "
                     f"{pct(k['wrong column'] / n)} | {pct(k['wrong row'] / n)} | {pct(k['sign'] / n)} | {pct(k['wrong value'] / n)} | {pct(rec)} |")
    lines.append("")

    lines += ["## 2. Measures for the rule fixed in the pilot (strict, test split)", "",
              "| Output | Coverage | Accepted-fact error (95% bound: naive / clustered) | Of which value errors | Accepted, context not stated | "
              "Filings with an accepted error | Correct automatic recovery (complete / value with all stated context right) | Error-detection recall | Review workload |",
              "|---|---:|---|---:|---:|---:|---:|---:|---:|"]
    for label, res in mains.items():
        groups = defaultdict(list)
        for c in res["cells"]:
            groups[c["filing"]].append(1 if c["fact"] in ERRORS else 0)
        rho = icc(list(groups.values()))
        m = measures(res, "arithmetic + agreement (rule fixed in the pilot)", rho, False)
        m["rho"] = rho
        # value level (the earlier scoring): no wrong value accepted; bound corrected for clustering of value errors
        vg = defaultdict(list)
        for c in res["cells"]:
            vg[c["filing"]].append(0 if c["value_ok"] else 1)
        vrho = icc(list(vg.values()))
        acc = [c for c in res["cells"] if RULES["arithmetic + agreement (rule fixed in the pilot)"](c)]
        nf = len({c["filing"] for c in acc})
        vdeff = 1 + max(0.0, len(acc) / nf - 1) * vrho
        m.update(value_rho=vrho, value_deff=vdeff, value_acc_err_n=sum(1 for c in acc if not c["value_ok"]),
                 value_ub_naive=cp_upper(0, len(acc)), value_ub_cluster=cp_upper(0, max(1, round(len(acc) / vdeff))))
        summary["main"][label] = m
        lines.append(f"| {label} | {pct(m['coverage'])} | {pct(m['acc_err'], 2)} ({m['acc_err_n']}; {pct(m['ub_naive'], 2)} / {pct(m['ub_cluster'], 2)}) | "
                     f"{pct(m['acc_value_err'], 2)} | {pct(m['acc_incomplete'])} | {m['filings_err']} of {m['filings']} | {pct(m['recovery'])} / {pct(m['recovery_vp'])} | "
                     f"{pct(m['detect'])} | {pct(m['workload'])} |")
    lines += ["", "Value level (the earlier scoring): no accepted figure has a wrong value; 95% upper bound, naive / corrected for "
              "clustering of value errors by filing: " + "; ".join(f"{l}: {pct(m['value_ub_naive'], 3)} / {pct(m['value_ub_cluster'], 3)} "
              f"(intra-filing correlation {m['value_rho']:.3f}, design effect {m['value_deff']:.1f})" for l, m in summary["main"].items()) + ".",
              "", "Accepted errors by kind: " + "; ".join(f"{l}: " + (", ".join(f"{k} {v}" for k, v in sorted(m["acc_classes"].items())) or "none")
                                                       for l, m in summary["main"].items()) + ".", ""]

    # ---- ablation on the token re-runs
    lines += ["## 3. Each component separately (token re-runs, test split)", "",
              "| Output | Rule | Coverage | Accepted-fact error | 95% bound, clustered | Accepted, context not stated | Recovery | Detection recall | Omissions detected | Review workload | Error at 10% review |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for label, (run, engine, tok) in TOKEN.items():
        res = analyse(run, engine, engine, tok, test, theta_row, theta_col, cache)
        groups = defaultdict(list)
        for c in res["cells"]:
            groups[c["filing"]].append(1 if c["fact"] in ERRORS else 0)
        rho = icc(list(groups.values()))
        summary["ablation"][label] = {}
        for rule in RULES:
            m = measures(res, rule, rho, rule in DOC_LEVEL)
            be = budget_error(res["cells"], RANKINGS[rule]) if rule in RANKINGS else float("nan")
            m["budget_err"] = be
            m["budget_fact_err"] = budget_error(res["cells"], RANKINGS[rule], facts=True) if rule in RANKINGS else float("nan")
            summary["ablation"][label][rule] = m
            lines.append(f"| {label} | {rule} | {pct(m['coverage'])} | {pct(m['acc_err'], 2)} ({m['acc_err_n']}) | {pct(m['ub_cluster'], 2)} | "
                         f"{pct(m['acc_incomplete'])} | {pct(m['recovery'])} | {pct(m['detect'])} | {m['omissions_detected']} of {m['omissions']} | "
                         f"{pct(m['workload'])} | {pct(be, 2)} |")
    lines.append("")

    # ---- natural failures that can fool both checks (main runs)
    lines += ["## 4. Natural failures that can fool both checks (test split)", "",
              "| Output | Wrong column | …accepted | Wrong row | …accepted | Sign | …accepted | Same wrong value in both engines | …accepted | Statements missing >=30% of figures | …flagged at document level |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    rule = RULES["arithmetic + agreement (rule fixed in the pilot)"]
    for label, res in mains.items():
        cells = res["cells"]
        nat = {}
        for kind in ("wrong column", "wrong row", "sign"):
            sel = [c for c in cells if c["fact"] == kind]
            nat[kind] = (len(sel), sum(1 for c in sel if rule(c)))
        both = [c for c in cells if not c["value_ok"] and c["engine"]]
        nat["same wrong value in both engines"] = (len(both), sum(1 for c in both if rule(c)))
        dc = [s for s in res["statements"] if s["n"] and s["missing"] >= 0.3 * s["n"]]
        nat["dropped content (>=30% of a statement)"] = (len(dc), sum(1 for s in dc if s["doc_flag"]))
        summary["natural"][label] = nat
        lines.append(f"| {label} | " + " | ".join(f"{a} | {b}" for a, b in nat.values()) + " |")
    lines.append("")

    # ---- synthetic challenge set
    lines += ["## 5. Synthetic challenge set (reported separately; real outputs with one injected error each)", "",
              "| Output | Injected error | Instances | Scored as errors | Accepted, rule fixed in the pilot | Accepted, + completeness | Accepted, + context agreement | Caught at document level |",
              "|---|---|---:|---:|---:|---:|---:|---:|"]
    for label in ("dots.mocr pipeline, seed 0", "Chandra OCR 2, own input size"):
        run, engine, _ = MAIN[label]
        ch = challenge(run, engine, engine, test, theta_row, theta_col)
        summary["challenge"][label] = ch
        for kind, v in ch.items():
            lines.append(f"| {label} | {kind} | {v.get('instances', 0)} | {v.get('scored as errors', '–')} | "
                         f"{v.get('accepted, pilot rule', '–')} | {v.get('accepted, + completeness', '–')} | {v.get('accepted, + context agreement', '–')} | "
                         f"{v.get('caught, completeness', '–')} |")
    lines.append("")
    (PAPER / "bench" / "RQ2_STRICT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (PAPER / "bench" / "rq2_strict_summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
