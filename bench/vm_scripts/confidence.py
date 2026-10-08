"""Per-figure confidence from three GT-free signals, evaluated against the ground truth.
 1. token probability  (needs <page>.tok.json from BENCH_LOGPROBS=1 runs): product / min of digit-token probs, top-2 margin
 2. arithmetic anchoring (validate.py): figure in a satisfied sum relationship -> anchored; in a broken one -> suspect
 3. agreement with a second independent reading (other seed / prep / model)
Usage: python confidence.py <results_dir> [--second <dir>] [--docs maaden,aramco,drilling]"""
import sys, re, json, math, argparse
from pathlib import Path
from collections import Counter, defaultdict
sys.path.insert(0, "."); import eval2, validate, post_dots
PAGES = {"aramco": [f"aramco_p{n}" for n in range(12, 17)], "maaden": [f"maaden_p{n}" for n in range(11, 17)], "drilling": [f"drilling_p{n:02d}" for n in range(8, 14)]}
GTF = {"aramco": "aramco_main_tables.md", "maaden": "maaden_main_tables.md", "drilling": "drilling_main_tables.md"}
NUM = re.compile(r"[(\-−]?\s?[\d٠-٩۰-۹][\d٠-٩۰-۹,٬.]*\)?")
def page_text(d, pg):
    f = Path(d) / f"{pg}.md"
    if not f.exists(): return ""
    raw = f.read_text(errors="replace"); bl = post_dots.blocks_of(raw)
    return post_dots.render(bl) if bl else raw
def figures_in(text):
    """(value, start, end) for every number-like token with abs>=1000 or a decimal, in reading order."""
    out = []
    for m in NUM.finditer(text):
        vals = eval2.numbers(m.group(0))
        if len(vals) == 1 and (abs(vals[0]) >= 1000 or vals[0] != int(vals[0])) and not (1990 <= abs(vals[0]) <= 2035 and vals[0] == int(vals[0])):
            out.append((abs(vals[0]), m.start(), m.end()))
    return out
def token_conf(d, pg):
    """Map character spans of the raw output to token probabilities -> {(start,end): (prod_prob, min_prob, min_margin)}."""
    f = Path(d) / f"{pg}.tok.json"
    if not f.exists(): return None
    toks = json.loads(f.read_text()); raw = "".join(t[1] for t in toks)
    spans = []; pos = 0
    for tid, txt, lp, mx_ in toks: spans.append((pos, pos + len(txt), lp, mx_)); pos += len(txt)
    def conf(a, b):
        ps = [(lp, mx_) for s, e, lp, mx_ in spans if s < b and e > a]
        if not ps: return None
        return (math.exp(sum(lp for lp, _ in ps)), math.exp(min(lp for lp, _ in ps)), min(math.exp(lp) / math.exp(mx_) for lp, mx_ in ps))
    return raw, conf
def anchors(d, pages):
    """anchored values (cells in satisfied relationships under the structural-majority rule, or recurring across the
    document) and suspect values (unanchored cells of broken relationships), reusing validate_doc's logic."""
    rep, docs = validate.validate_doc(d, pages)
    anchored, suspect = set(), set()
    for t in docs:
        mat = t["mat"]
        for (i, c) in t["anchored"]:
            v = mat[i][1][c]
            if v not in (None, 0.0): anchored.add(abs(v))
        for (tt, k, e, c, diff) in t["broken"]:
            for i in list(range(k, e + 1)) + [tt]:
                if (i, c) in t["anchored"]: continue
                v = mat[i][1][c]
                if v not in (None, 0.0): suspect.add(abs(v))
    return anchored, suspect - anchored
def gt_multiset(doc):
    GT = eval2.parse_gt(open(GTF[doc]).read()); return Counter(abs(f) for tb in GT for r in tb["rows"] for f in r["figs"])
def run(d, second, docs):
    rows = []
    for doc in docs:
        gt = gt_multiset(doc); anc, sus = anchors(d, PAGES[doc])
        sec = Counter()
        if second:
            for pg in PAGES[doc]: sec.update(v for v, _, _ in figures_in(page_text(second, pg)))
        for pg in PAGES[doc]:
            text = page_text(d, pg); tc = token_conf(d, pg)
            for v, a, b in figures_in(text):
                rec = dict(doc=doc, page=pg, value=v, correct=gt[v] > 0, anchored=v in anc, suspect=v in sus, agreed=(sec[v] > 0) if second else None)
                if tc:
                    raw, conf = tc; i = raw.find(text[a:b])   # locate in raw output (band-merge reorders blocks, so search)
                    c = conf(i, i + (b - a)) if i >= 0 else None
                    rec.update(p_prod=c[0] if c else None, p_min=c[1] if c else None, margin=c[2] if c else None)
                rows.append(rec)
    return rows
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("results_dir"); ap.add_argument("--second", default=None); ap.add_argument("--docs", default="maaden,aramco,drilling")
    a = ap.parse_args(); rows = run(a.results_dir, a.second, a.docs.split(","))
    n = len(rows); wrong = [r for r in rows if not r["correct"]]
    print(f"{a.results_dir}: {n} emitted figures (>=1000 or decimal), {len(wrong)} not in GT")
    for sig, name in (("anchored", "arithmetically anchored"), ("suspect", "in a broken relationship"), ("agreed", "agreed by 2nd reading")):
        vals = [r[sig] for r in rows if r[sig] is not None]
        if vals:
            tp = sum(1 for r in rows if r[sig] and r["correct"]); fp = sum(1 for r in rows if r[sig] and not r["correct"])
            print(f"  {name:<28}: {sum(vals):>4} figures flagged; of these correct {tp}, not-in-GT {fp}   | not flagged & wrong: {sum(1 for r in rows if r[sig] is False and not r['correct'])}")
    if any(r.get("p_prod") is not None for r in rows):
        ok = sorted(r["p_min"] for r in rows if r["correct"] and r.get("p_min") is not None); bad = sorted(r["p_min"] for r in rows if not r["correct"] and r.get("p_min") is not None)
        import statistics as st
        print(f"  token min-prob: correct median {st.median(ok):.3f} (10th pct {ok[len(ok)//10]:.3f}) | not-in-GT median {st.median(bad):.3f}" if ok and bad else "  token probs present")
        # how many correct figures must be reviewed to catch every wrong one at the threshold = max wrong p_min
        if bad:
            thr = max(bad); print(f"  threshold p_min <= {thr:.3f} catches all not-in-GT figures and flags {sum(1 for r in rows if r['correct'] and r.get('p_min') is not None and r['p_min'] <= thr)} correct ones ({100*sum(1 for r in rows if r['correct'] and r.get('p_min') is not None and r['p_min'] <= thr)/max(1,len(ok)):.1f}%)")
    json.dump(rows, open(Path(a.results_dir).name + "_confidence.json", "w"), ensure_ascii=False)
    for r in wrong[:12]: print("   not-in-GT:", r["page"], r["value"], {k: r[k] for k in ("anchored", "suspect", "agreed", "p_min") if k in r})
