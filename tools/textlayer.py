"""Cross-check a transcription against the digits stored in the PDF's text layer (filings that have one).

Digits are read from each character's position on the page, not from the stored text order, so text layers that
store numbers reversed (e.g. "13" for 31) still give the printed number. Signs are not compared (parentheses are
unreliable in text layers); the arithmetic checks cover signs.

Reports, per statement:
  not in text layer - transcribed figures absent from the statement's pages: likely misreads
  not transcribed   - text-layer figures (4+ digits) not used by the transcription: possibly missed rows or misreads

usage: python textlayer.py paper/drafts/FILING_ID.json   (or a gt/*.json)
"""
import re
import sys
from collections import Counter
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gtlib  # noqa: E402

DIGITS = "0123456789٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹"
TO_ASCII = str.maketrans(DIGITS, "0123456789" * 3)
SEPS = ",.٫٬،"


def page_tokens(page):
    """Numbers on the page, each as the set of values it can mean (a lone "." or "٫" before three digits is either
    a thousands separator or a decimal point, depending on the filing). Digits are ordered left to right as printed."""
    chars, out = [], []
    for b in page.get_text("rawdict")["blocks"]:
        for l in b.get("lines", []):
            for s in l["spans"]:
                if len(s["chars"]) > 1 and len({round(c["bbox"][0], 1) for c in s["chars"]}) == 1:
                    # glyph positions are missing (e.g. rotated pages): read runs in stored order, both directions
                    text = "".join(c["c"] for c in s["chars"])
                    for run in re.findall(r"[%s][%s%s]*" % (DIGITS, DIGITS, re.escape(SEPS)), text):
                        cands = parse(run) | parse(run[::-1])
                        if cands:
                            out.append(cands)
                    continue
                for ch in s["chars"]:
                    if ch["c"] in DIGITS or ch["c"] in SEPS:
                        x0, y0, x1, y1 = ch["bbox"]
                        chars.append((round(ch["origin"][1]), x0, x1, ch["c"], s["size"]))
    lines = {}
    for y, x0, x1, c, size in chars:                     # group by baseline, tolerant to 2pt jitter
        key = next((k for k in lines if abs(k - y) <= 2), y)
        lines.setdefault(key, []).append((x0, x1, c, size))
    for chs in lines.values():
        chs.sort()
        tok, last_x1 = "", None
        for x0, x1, c, size in chs + [(1e9, 1e9, " ", 0)]:
            if last_x1 is not None and x0 - last_x1 > max(1.5, 0.3 * size):
                cands = parse(tok)
                if cands:
                    out.append(cands)
                tok = ""
            tok += c
            last_x1 = x1
    return out


def page_numbers(page):
    """Counter of each number's first reading (kept for quick inspection)."""
    return Counter(sorted(c, key=lambda v: -v)[0] for c in page_tokens(page))


def parse(tok):
    t = tok.translate(TO_ASCII).strip(SEPS)
    if not t or not any(ch.isdigit() for ch in t):
        return set()
    parts = re.split(r"[,.٫٬،]", t)
    seps = re.findall(r"[,.٫٬،]", t)
    if len(parts) == 1:
        return {int(t)}
    whole = int("".join(parts))
    if all(len(p) == 3 for p in parts[1:]):
        if len(parts) > 2 or seps[0] in ",٬،":
            return {whole}
        return {whole, float(f"{parts[0]}.{parts[1]}")}
    if len(parts) == 2:
        return {float(f"{parts[0]}.{parts[1]}")}
    if all(len(p) == 3 for p in parts[1:-1]) and len(parts[-1]) in (1, 2, 4):
        return {float("".join(parts[:-1]) + "." + parts[-1])}   # 2,555,56 -> 2555.56 (last separator is decimal)
    return set()


def check(gt):
    """-> (per-statement misses, filing-level figures on the statement pages that no statement uses)."""
    doc = fitz.open(gtlib.PAPER / "filings" / f"{gt['filing_id']}.pdf")
    toks, index, used = {}, {}, set()
    for st in gt["statements"]:
        for p in st["pages"]:
            if p not in toks:
                toks[p] = page_tokens(doc[p - 1])
                for i, cands in enumerate(toks[p]):
                    for v in cands:
                        index.setdefault((p, v), []).append(i)
    report = []
    for st in gt["statements"]:
        if not any(toks[p] for p in st["pages"]):
            report.append((st, None))
            continue
        missing = []
        for r in st["rows"]:
            for cid, v in (r.get("values") or {}).items():
                if not isinstance(v, (int, float)):
                    continue
                a = abs(v)
                a = int(a) if float(a).is_integer() else a
                hit = next(((p, i) for p in st["pages"] for i in index.get((p, a), []) if (p, i) not in used), None)
                if hit:
                    used.add(hit)
                else:
                    missing.append((r["id"], cid, r.get("label_ar", ""), v))
        report.append((st, missing))
    extra = Counter()
    for p, ts in toks.items():
        for i, cands in enumerate(ts):
            v = max(cands)
            if (p, i) not in used and isinstance(v, int) and v >= 1000 and not 1990 <= v <= 2035:
                extra[v] += 1
    return report, sorted(extra.items())


if __name__ == "__main__":
    gt = gtlib.load(sys.argv[1])
    total = miss = 0
    report, extra = check(gt)
    for st, missing in report:
        n = sum(isinstance(v, (int, float)) for r in st["rows"] for v in (r.get("values") or {}).values())
        total += n
        if missing is None:
            print(f"{st['id']} {st['type']} p{st['pages']}: no text layer")
            continue
        miss += len(missing)
        print(f"{st['id']} {st['type']} p{st['pages']}: {n} figures, {len(missing)} not in text layer")
        for rid, cid, label, v in missing:
            print(f"    not in text layer  {rid}/{cid}  {gtlib.fmt_value(v):>16}  {label}")
    for v, k in sorted(extra):
        print(f"    on the pages but not transcribed  {v:>16,}" + (f"  x{k}" if k > 1 else ""))
    print(f"total: {total} figures, {miss} not found in the text layer, {sum(k for _, k in extra)} page figures unused")
