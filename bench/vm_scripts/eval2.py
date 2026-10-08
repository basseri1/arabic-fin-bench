#!/usr/bin/env python
"""Score results/<model>/*.md against the ground-truth tables.

GT files: aramco_main_tables.md (pages aramco_p12..16), maaden_main_tables.md (pages maaden_p11..16).
Metrics (micro-averaged over GT items; per model x document, plus overall):
  fig_recall     % of GT figures (data-column numbers, |value|, multiset) found anywhere in the output
  fig_sgn        same, but the sign must also be right (parentheses / minus preserved)
  row_recall     % of GT data rows whose full set of figures appears together on ONE output line / table row
  label_recall   % of GT row labels (Arabic) found in the output (fuzzy partial-ratio >= 85, normalized)
  num_prec       % of all numbers in the output that exist in GT (hallucination proxy; lower = more invented)
  CER / WER      doc-level, normalized text, order-sensitive - secondary (column-order flips inflate it)
  s/page         mean wall-clock seconds per page (from _timing.jsonl)
Usage: python eval2.py [--results DIR] [--md out.md] [--json out.json] [--per-table]
"""
import argparse, json, re, unicodedata
from collections import Counter
from pathlib import Path
from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein

BASE = Path(__file__).resolve().parent
GT_FILES = {"aramco": BASE / "aramco_main_tables.md", "maaden": BASE / "maaden_main_tables.md", "drilling": BASE / "drilling_main_tables.md"}
import os as _os
if _os.environ.get("EVAL_DOCS"):                          # restrict to a subset of documents, e.g. EVAL_DOCS=drilling
    GT_FILES = {k: v for k, v in GT_FILES.items() if k in _os.environ["EVAL_DOCS"].split(",")}
elif not _os.environ.get("EVAL_ALL_DOCS"):                 # default benchmark = the two original documents
    GT_FILES = {k: v for k, v in GT_FILES.items() if k in ("aramco", "maaden")}
# which pages carry which GT table (1-based table index within the GT file)
TABLE_PAGES = {
    "aramco": {1: ["aramco_p12"], 2: ["aramco_p13"], 3: ["aramco_p14"], 4: ["aramco_p15"], 5: ["aramco_p16"]},
    "maaden": {1: ["maaden_p11"], 2: ["maaden_p12"], 3: ["maaden_p13"], 4: ["maaden_p14"],
               5: ["maaden_p15", "maaden_p16"], 6: ["maaden_p16"]},
    "drilling": {1: ["drilling_p10"], 2: ["drilling_p10"], 3: ["drilling_p08", "drilling_p09"], 4: ["drilling_p11"],
                 5: ["drilling_p12", "drilling_p13"], 6: ["drilling_p13"]},
}
TABLE_NAMES = {1: "P&L", 2: "OCI", 3: "Bal.sheet", 4: "Equity", 5: "Cashflow", 6: "Non-cash"}

# ------------------------------------------------------------------ text / number normalization
DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹٬٫−–—", "0123456789" "0123456789" ",." "---")
NUM_RE = re.compile(r"(\()?(-?)(\d[\d,]*(?:\.\d+)?)(\))?")
AR_DIAC = re.compile(r"[ً-ْٰـ]")


AR_COMMA_BETWEEN_DIGITS = re.compile(r"(?<=\d)،(?=\d)")   # Arabic comma used as thousands/decimal separator

def norm_digits(t):
    t = unicodedata.normalize("NFKC", t).translate(DIGITS)
    return AR_COMMA_BETWEEN_DIGITS.sub(",", t)


DEC_COMMA = re.compile(r"(?<![\d,])(\d{1,3}),(\d{2})(?![\d,])")

def numbers(t, signed=False):
    """List of numeric values in text (Arabic-Indic digits supported, (x) = negative, '0,78' = 0.78)."""
    out = []
    for lead, minus, body, trail in NUM_RE.findall(DEC_COMMA.sub(r"\1.\2", norm_digits(t))):
        try:
            v = float(body.replace(",", ""))
        except ValueError:
            continue
        if signed and (minus or (lead and trail)):
            v = -v
        out.append(round(v, 2))
    return out


def norm_ar(t):
    t = norm_digits(t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = AR_DIAC.sub("", t)
    t = re.sub(r"[إأآٱ]", "ا", t).replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي")
    t = re.sub(r"[|*_#`\-—–\[\]{}\"'«»()]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def strip_tags(t):
    return re.sub(r"<[^>]+>", " ", t)


def extract_text(raw):
    """Model output -> plain text. Handles dots.ocr layout JSON (list of {bbox,category,text})."""
    s = raw.strip()
    s = re.sub(r"^```(?:json|markdown|md|html)?\s*|\s*```$", "", s)
    if s.startswith(("[", "{")):
        try:
            obj = json.loads(s)
            items = obj if isinstance(obj, list) else [obj]
            texts = [it.get("text", "") for it in items if isinstance(it, dict)]
            if texts:
                return "\n".join(t for t in texts if t)
        except Exception:
            pass
        # truncated JSON (generation hit the cap): salvage every closed "text": "..." field, plus the
        # unterminated last one (often the big table) - otherwise a capped page loses its whole table.
        def unesc(f):
            try:
                return json.loads('"' + f + '"')
            except Exception:
                f = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), f)
                return f.replace("\\n", "\n").replace('\\"', '"').replace("\\/", "/").replace("\\\\", "\\")
        pieces = []
        for m in re.finditer(r'"text"\s*:\s*"', s):
            rest = s[m.end():]
            end = re.search(r'(?<!\\)"', rest)
            pieces.append(unesc(rest[:end.start()] if end else rest))
        if pieces:
            return "\n".join(pieces)
    return s


def truncate_loops(t, win=200, span=12000, reps=3, step=200):
    """Cut a degenerate repetition loop: first point where the trailing 200 chars already occurred twice
    in the preceding 6000 chars; keep everything through the first occurrence. Applied to every model's
    output before scoring so precision/CER are comparable. Returns (text, was_cut)."""
    n = len(t)
    for i in range(win * reps, n, step):
        tail = t[i - win:i]; lo = max(0, i - span); body = t[lo:i - win]
        if body.count(tail) >= reps - 1:
            j1 = t.find(tail, lo, i - win)                 # first occurrence of the repeated window
            j2 = t.find(tail, j1 + 1, i - win + 1)         # second occurrence = start of the second copy
            return t[:j2 if j2 > j1 else j1 + win], True  # keep everything through the first full period
    return t, False


def lines_of(text):
    """Rows of content: one HTML <tr>...</tr> = one line (even if pretty-printed over many physical
    lines); otherwise physical lines. Tags are stripped."""
    t = re.sub(r"<tr\b[^>]*>.*?</tr\s*>", lambda m: "\n" + m.group(0).replace("\n", " ") + "\n", text, flags=re.I | re.S)
    t = re.sub(r"</tr\s*>", "\n", t, flags=re.I)
    t = re.sub(r"<br\s*/?>", " ", t, flags=re.I)
    return [strip_tags(l) for l in t.splitlines() if strip_tags(l).strip()]


# ------------------------------------------------------------------ GT parsing
def parse_gt(md):
    """-> list of tables: {header, rows:[{label, figs(signed list)}], allnums(list)}"""
    tables, cur = [], None
    for line in md.splitlines():
        s = line.strip()
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                continue
            if cur is None:
                cur = {"header": cells, "rows": [], "allnums": numbers(" ".join(cells))}
                tables.append(cur)
            else:
                cur["allnums"] += numbers(" ".join(cells))
                has_note = len(cur["header"]) > 1 and "إيضاح" in cur["header"][1]
                data = cells[2:] if has_note else cells[1:]
                figs = numbers(" ".join(data), signed=True)
                label = re.sub(r"[*_]", "", cells[0]).strip()
                if figs:
                    cur["rows"].append({"label": label, "figs": figs})
        else:
            cur = None
    return tables


def gt_text(md):
    """GT body as comparable text: table rows + section titles only (no preamble / author notes)."""
    keep = []
    for line in md.splitlines():
        s = line.strip()
        if s.startswith("|") and not re.fullmatch(r"[|:\- ]+", s):
            keep.append(s)
        elif s.startswith("#") and not s.startswith("# "):
            keep.append(re.sub(r"^#+\s*\d*\.?\s*", "", s))
    return "\n".join(keep)


# ------------------------------------------------------------------ scoring
def cer(ref, hyp):
    return Levenshtein.distance(ref, hyp) / max(1, len(ref))


def wer(ref, hyp):
    r, h = ref.split(), hyp.split()
    prev = list(range(len(h) + 1))
    for i, rw in enumerate(r, 1):
        cur = [i] + [0] * len(h)
        for j, hw in enumerate(h, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (rw != hw))
        prev = cur
    return prev[-1] / max(1, len(r))


def score_tables(tables, text):
    """Score a set of GT tables against one blob of model text. Returns dict of counts."""
    lines = lines_of(text)                      # tag-stripped, one table row per line
    line_nums = [Counter(numbers(l)) for l in lines]
    plain = "\n".join(lines)                    # numbers inside tags (bbox, colspan, border) don't count
    out_abs, out_sgn = Counter(numbers(plain)), Counter(numbers(plain, signed=True))
    norm_full = norm_ar(plain)
    gt_abs, gt_sgn, gt_all = Counter(), Counter(), Counter()
    rows_hit = rows_tot = lab_hit = lab_tot = 0
    for tb in tables:
        gt_all.update(tb["allnums"])
        for r in tb["rows"]:
            gt_sgn.update(r["figs"]); gt_abs.update(abs(v) for v in r["figs"])
            need = Counter(abs(v) for v in r["figs"])
            rows_tot += 1
            rows_hit += any(not (need - ln) for ln in line_nums)
            lab = norm_ar(r["label"])
            if len(lab) >= 4:
                lab_tot += 1
                lab_hit += fuzz.partial_ratio(lab, norm_full) >= 85
    return {
        "fig_hit": sum((gt_abs & out_abs).values()), "fig_tot": sum(gt_abs.values()),
        "sgn_hit": sum((gt_sgn & out_sgn).values()),
        "rows_hit": rows_hit, "rows_tot": rows_tot,
        "lab_hit": lab_hit, "lab_tot": lab_tot,
        "prec_hit": sum((gt_all & out_abs).values()), "prec_tot": sum(out_abs.values()),
    }


def add(a, b):
    return {k: a.get(k, 0) + b.get(k, 0) for k in set(a) | set(b)}


def pct(h, t):
    return h / t if t else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=str(BASE / "results"))
    ap.add_argument("--md", default="")
    ap.add_argument("--json", default="")
    ap.add_argument("--per-table", action="store_true")
    a = ap.parse_args()
    results = Path(a.results)

    GT = {d: parse_gt(f.read_text(encoding="utf-8")) for d, f in GT_FILES.items()}
    GTTXT = {d: norm_ar(gt_text(f.read_text(encoding="utf-8"))) for d, f in GT_FILES.items()}

    rows, per_table = [], []
    for mdir in sorted(p for p in results.iterdir() if p.is_dir()):
        model = mdir.name
        pages, cut_pages = {}, 0
        for p in mdir.glob("*.md"):
            # tag-stripped rows first (bbox/colspan attrs vanish -> repeated blocks become identical), then cut loops
            txt, cut = truncate_loops("\n".join(lines_of(extract_text(p.read_text(encoding="utf-8", errors="replace")))))
            pages[p.stem] = txt; cut_pages += cut
        if not any(v.strip() for v in pages.values()):
            continue                                  # model dir with no output yet (e.g. API retry loop)
        timing, capped = {}, {}
        tf = mdir / "_timing.jsonl"
        if tf.exists():
            for l in tf.read_text().splitlines():
                try:
                    j = json.loads(l); timing[j["page"]] = j["secs"]
                    capped[j["page"]] = j.get("finish") in ("length", "max_time")
                except Exception:
                    pass
        overall = {}
        n_pages_total = 0; secs_all = []
        for doc, tables in GT.items():
            doc_pages = sorted(k for k in pages if k.startswith(doc))
            if not doc_pages:
                continue
            expected = sorted({p for ps in TABLE_PAGES[doc].values() for p in ps})
            missing = [p for p in expected if p not in pages or not pages[p].strip()]
            full = "\n".join(pages[p] for p in doc_pages)
            c = score_tables(tables, full)
            c["cer"] = cer(GTTXT[doc], norm_ar(full)); c["wer"] = wer(GTTXT[doc], norm_ar(full))
            raw_full = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in mdir.glob(f"{doc}_*.md"))
            ai_d, we_d = len(re.findall(r"[٠-٩]", raw_full)), len(re.findall(r"[0-9]", raw_full))
            c["ai_share"] = ai_d / (ai_d + we_d) if (ai_d + we_d) else float("nan")
            secs = [timing[p] for p in doc_pages if p in timing]
            n_capped = sum(1 for p in doc_pages if capped.get(p))
            rows.append({"model": model, "doc": doc, "pages": f"{len(doc_pages)}/{len(expected)}", "looped": n_capped,
                         "missing": missing, "fig_recall": pct(c["fig_hit"], c["fig_tot"]),
                         "fig_sgn": pct(c["sgn_hit"], c["fig_tot"]), "row_recall": pct(c["rows_hit"], c["rows_tot"]),
                         "label_recall": pct(c["lab_hit"], c["lab_tot"]), "num_prec": pct(c["prec_hit"], c["prec_tot"]),
                         "cer": c["cer"], "wer": c["wer"], "ai_share": c.get("ai_share", float("nan")),
                         "s_page": sum(secs) / len(secs) if secs else float("nan")})
            overall = add(overall, {k: v for k, v in c.items() if k not in ("cer", "wer")})
            n_pages_total += len(doc_pages); secs_all += secs
            for ti, tb in enumerate(tables, 1):
                tp = TABLE_PAGES[doc].get(ti, [])
                blob = "\n".join(pages.get(p, "") for p in tp)
                tc = score_tables([tb], blob)
                per_table.append({"model": model, "doc": doc, "table": f"{doc[:2]}-{TABLE_NAMES.get(ti, ti)}",
                                  "row_recall": pct(tc["rows_hit"], tc["rows_tot"]),
                                  "fig_recall": pct(tc["fig_hit"], tc["fig_tot"])})
        if overall:
            rows.append({"model": model, "doc": "ALL", "pages": str(n_pages_total), "missing": [],
                         "looped": sum(1 for p in pages if capped.get(p)), "cut": cut_pages,
                         "fig_recall": pct(overall["fig_hit"], overall["fig_tot"]),
                         "fig_sgn": pct(overall["sgn_hit"], overall["fig_tot"]),
                         "row_recall": pct(overall["rows_hit"], overall["rows_tot"]),
                         "label_recall": pct(overall["lab_hit"], overall["lab_tot"]),
                         "num_prec": pct(overall["prec_hit"], overall["prec_tot"]),
                         "cer": float("nan"), "wer": float("nan"),
                         "s_page": sum(secs_all) / len(secs_all) if secs_all else float("nan")})

    def f(x, p=True):
        if x != x:
            return "  -  "
        return f"{x:6.1%}" if p else f"{x:6.3f}"

    hdr = f"{'model':<10} {'doc':<7} {'pages':>5} {'looped':>6} {'fig_rec':>7} {'fig_sgn':>7} {'row_rec':>7} {'label':>7} {'num_prec':>8} {'CER':>6} {'WER':>6} {'s/page':>7}"
    lines = [hdr, "-" * len(hdr)]
    for r in rows:
        lines.append(f"{r['model']:<10} {r['doc']:<7} {r['pages']:>5} {r.get('looped', 0):>6} {f(r['fig_recall'])} {f(r['fig_sgn'])} "
                     f"{f(r['row_recall'])} {f(r['label_recall'])} {f(r['num_prec']):>8} {f(r['cer'], False)} "
                     f"{f(r['wer'], False)} {r['s_page']:>7.0f}" + (f"   missing:{','.join(r['missing'])}" if r['missing'] else ""))
    print("\n".join(lines))
    if a.per_table and per_table:
        models = sorted({r["model"] for r in per_table})
        tabs = []
        for r in per_table:
            if r["table"] not in tabs:
                tabs.append(r["table"])
        print("\nrow_recall per statement:")
        print(f"{'model':<10} " + " ".join(f"{t:>11}" for t in tabs))
        for m in models:
            vals = {r["table"]: r["row_recall"] for r in per_table if r["model"] == m}
            print(f"{m:<10} " + " ".join(f"{f(vals.get(t, float('nan'))):>11}" for t in tabs))
    if a.md:
        md = ["| model | doc | pages | looped | fig recall | fig recall (signed) | row recall | label recall | num precision | CER | WER | s/page |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for r in rows:
            md.append(f"| {r['model']} | {r['doc']} | {r['pages']} | {r.get('looped', 0)} | {f(r['fig_recall'])} | {f(r['fig_sgn'])} | {f(r['row_recall'])} | "
                      f"{f(r['label_recall'])} | {f(r['num_prec'])} | {f(r['cer'], False)} | {f(r['wer'], False)} | {r['s_page']:.0f} |")
        Path(a.md).write_text("\n".join(md) + "\n", encoding="utf-8")
    if a.json:
        Path(a.json).write_text(json.dumps({"summary": rows, "per_table": per_table}, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
