"""RQ2 on the 32-filing benchmark: what arithmetic verification repairs, and how well GT-free signals route the
remaining figures to review. No ground truth is used to compute any signal; the ground truth only scores them.

Figures: the non-zero cells in the data columns of the tables a system emitted, parsed exactly as the verification
step parses them (validate.py: label and note-reference columns dropped, text outside tables ignored), with
|value| >= 1000 or a decimal part and calendar years excluded, as in the pilot. A figure is correct when its absolute
value occurs among the ground-truth figures of the same filing (placement is not checked). Errors are classed as
  misread digit    – one digit substituted, inserted, deleted, or two neighbouring digits swapped, of a GT figure
  separator/scale  – a GT figure times or divided by 10..10,000 (a decimal or thousands separator misread)
  other            – anything else (several digits wrong, merged cells, invented values)
Signals per figure:
  anchored  – inside a printed total that reconciles in the output, or recurring elsewhere in the filing
  suspect   – in a total that does not reconcile, and not anchored
  engine    – the same value read on the same filing by an independent self-hosted engine
  repeat    – the same value in other readings by the same model (other seeds; for Chandra, the other input size)
Tiers, fixed in advance (the pilot rule without token probabilities, which step 2 adds):
  LOW = suspect, or neither anchored nor engine-agreed;  HIGH = anchored and engine-agreed;  MEDIUM = the rest.
Writes bench/CONFIDENCE.md, bench/confidence_summary.json, bench/figures/risk_coverage.{png,pdf}.
usage: python bench/confidence32.py
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PAPER / "tools"))
sys.path.insert(0, str(PAPER / "bench" / "vm_scripts"))
import score  # noqa: E402
import eval2  # noqa: E402
import validate  # noqa: E402

RESULTS = PAPER / "bench" / "results32"
MANIFEST = json.loads((PAPER / "bench" / "vm_scripts" / "pages32_manifest.json").read_text())
PRIMARY = {  # label -> (delivered output, pre-verification output, independent engine, repeat readings)
    "dots.mocr pipeline, seed 0": ("dots_mocr_clahe_s0_bm_ver", "dots_mocr_clahe_s0_bm", "chandra2_chandra_cap",
                                   ["dots_mocr_clahe_s1_bm_ver", "dots_mocr_clahe_s2_bm_ver"]),
    "dots.mocr pipeline, seed 1": ("dots_mocr_clahe_s1_bm_ver", "dots_mocr_clahe_s1_bm", "chandra2_chandra_cap",
                                   ["dots_mocr_clahe_s0_bm_ver", "dots_mocr_clahe_s2_bm_ver"]),
    "dots.mocr pipeline, seed 2": ("dots_mocr_clahe_s2_bm_ver", "dots_mocr_clahe_s2_bm", "chandra2_chandra_cap",
                                   ["dots_mocr_clahe_s0_bm_ver", "dots_mocr_clahe_s1_bm_ver"]),
    "Chandra OCR 2, own input size": ("chandra2_chandra_cap_ver", "chandra2_chandra_cap", "dots_mocr_clahe_s0_bm_ver",
                                      ["chandra2_plain"]),
}
TOKENS = {  # re-runs with BENCH_LOGPROBS=1: label -> (delivered output, directory holding <page>.tok.json, engine, repeats)
    "dots.mocr pipeline, seed 0 (token run)": ("dots_mocr_clahe_lp_s0_bm_ver", "dots_mocr_clahe_lp_s0", "chandra2_chandra_cap",
                                               ["dots_mocr_clahe_s1_bm_ver", "dots_mocr_clahe_s2_bm_ver"]),
    "Chandra OCR 2, own input size (token run)": ("chandra2_chandra_cap_lp_ver", "chandra2_chandra_cap_lp",
                                                  "dots_mocr_clahe_s0_bm_ver", ["chandra2_plain"]),
}
TAUS = (0.5, 0.8, 0.9, 0.95, 0.99, 0.995, 0.999)          # candidate token-probability thresholds, chosen on dev
VERIFY = {  # label -> (before, after)
    "dots.mocr pipeline, seed 0": ("dots_mocr_clahe_s0_bm", "dots_mocr_clahe_s0_bm_ver"),
    "dots.mocr pipeline, seed 1": ("dots_mocr_clahe_s1_bm", "dots_mocr_clahe_s1_bm_ver"),
    "dots.mocr pipeline, seed 2": ("dots_mocr_clahe_s2_bm", "dots_mocr_clahe_s2_bm_ver"),
    "Chandra OCR 2, own input size": ("chandra2_chandra_cap", "chandra2_chandra_cap_ver"),
    "Chandra OCR 2, 200 dpi page": ("chandra2_plain", "chandra2_plain_ver"),
}


def is_figure(v):
    if v in (None, 0.0) or v != v or abs(v) == float("inf"):     # a looping output can yield an endless digit run
        return False
    a = abs(v)
    return (a >= 1000 or a != int(a)) and not (a == int(a) and 1990 <= a <= 2035)


def pages_of(fid):
    return [f"{fid}_p{p:02d}" for p in MANIFEST[fid]]


def norm(v):
    """A ground-truth value as the shared number parser reads it from text (decimals rounded to two places), so both
    sides of every comparison go through the same normalisation."""
    return abs(eval2.numbers(repr(float(v)) if float(v) != int(float(v)) else str(int(v)))[0])


def gt_values(gt):
    return Counter(norm(v) for st in gt["statements"] for r in st["rows"]
                   for v in (r.get("values") or {}).values() if isinstance(v, (int, float)) and v != 0)


def error_class(v, G):
    if G[v] > 0:
        return None
    if v == int(v):
        s = str(int(v))
        near = {abs(x) for x in validate.digit_edits(v)}
        near |= {int(s[:i] + s[i + 1] + s[i] + s[i + 2:]) for i in range(len(s) - 1)}
        if any(x in G for x in near):
            return "misread digit"
    for k in (10, 100, 1000, 10000):
        if round(v * k, 2) in G or round(v / k, 2) in G:
            return "separator/scale"
    return "other"


def cell_signals(results_dir, pages):
    """Anchored / suspect status of every data cell, with validate.validate_doc's rules but without applying fixes."""
    docs = []
    for pg in pages:
        f = results_dir / f"{pg}.md"
        if not f.exists():
            continue
        text = eval2.extract_text(f.read_text(errors="replace"))
        for rows in validate.parse_tables(text):
            mat, width = validate.matrix(rows)
            if mat and width:
                docs.append({"page": pg, "mat": mat, "width": width, "rels": validate.relationships(mat, width)})
    freq = Counter(abs(v) for d in docs for _, vals in d["mat"] for v in vals if v not in (None, 0.0))
    cells = []
    for d in docs:
        mat, width = d["mat"], d["width"]
        anchored, in_broken = set(), set()
        for (t, k, e) in d["rels"]:
            status = {c: validate.block_status(mat, t, k, e, c) for c in range(width)}
            def informative(c):
                return mat[t][1][c] not in (None, 0.0) or any(mat[i][1][c] not in (None, 0.0) for i in range(k, e + 1))
            testable = [c for c, x in status.items() if x is not None and informative(c)]
            ok = [c for c in testable if abs(status[c]) <= 0.5]
            if not testable or len(ok) < max(1, len(testable) / 2.0):
                continue
            for c in testable:
                block = list(range(k, e + 1)) + [t]
                if abs(status[c]) <= 0.5:
                    anchored.update((i, c) for i in block)
                else:
                    in_broken.update((i, c) for i in block)
        for i, (_, vals) in enumerate(mat):
            for c, v in enumerate(vals):
                if v not in (None, 0.0) and freq[abs(v)] >= 2:
                    anchored.add((i, c))
        for i, (_, vals) in enumerate(mat):
            for c, v in enumerate(vals):
                if is_figure(v):
                    cells.append(dict(page=d["page"], value=abs(v), anchored=(i, c) in anchored,
                                      suspect=(i, c) in in_broken and (i, c) not in anchored))
    return cells


NUMTOK = __import__("re").compile(r"[(\-−]?\s?[\d٠-٩۰-۹][\d٠-٩۰-۹,٬.٫]*\)?")
SKIP = __import__("re").compile(r'"bbox"\s*:\s*\[[^\]]*\]|<[^>]*>')   # layout coordinates, HTML tags and attributes


def char_probs(toks, text):
    """Probability of the token that produced each character of the streamed text. Token strings are aligned to the text;
    a token whose string is empty (one byte of a multi-byte character such as an Arabic-Indic digit, as vLLM 0.17
    returns them) is attributed to the characters skipped before the next token that aligns."""
    import math
    probs = [None] * len(text); pos = 0; pending = []
    for t in toks:
        s_, p = t[1], math.exp(t[2])
        if not s_:
            pending.append(p); continue
        j = pos if text.startswith(s_, pos) else text.find(s_, pos, pos + len(s_) + 8)
        if j < 0:                                         # cannot place this token here: treat it like the empty ones
            pending.append(p); continue
        if j > pos and pending:
            q = min(pending)
            for k in range(pos, j):
                probs[k] = q
        for k in range(j, j + len(s_)):
            probs[k] = p
        pos = j + len(s_); pending = []
    if pending:
        q = min(pending)
        for k in range(pos, len(text)):
            probs[k] = q
    return probs


def token_index(tok_dir, pg):
    """{value: lowest token probability over the characters of any occurrence} for the numbers in the generated text of
    a page, ignoring bounding boxes and tag attributes. None when the page has no token file."""
    f = tok_dir / f"{pg}.tok.json"
    if not f.exists():
        return None
    text = (tok_dir / f"{pg}.md").read_text(errors="replace")
    probs = char_probs(json.loads(f.read_text()), text)
    skip = [(m.start(), m.end()) for m in SKIP.finditer(text)]
    out = {}
    for m in NUMTOK.finditer(text):
        if any(a <= m.start() < b for a, b in skip):
            continue
        vals = eval2.numbers(m.group(0))
        if len(vals) != 1 or not is_figure(vals[0]):
            continue
        ps = [probs[k] for k in range(m.start(), m.end()) if probs[k] is not None and not text[k].isspace()]
        if ps:
            v = abs(vals[0]); out[v] = min(out.get(v, 1.0), min(ps))
    return out


def value_pool(results_dir, pages):
    pool = set()
    for pg in pages:
        pool |= validate.second_reader_values(results_dir, pg)
    return pool


def tier(r):
    if r["suspect"] or (not r["anchored"] and not r["engine"]):
        return "LOW"
    return "HIGH" if r["anchored"] and r["engine"] else "MEDIUM"


def figure_rows(label, gts):
    if label in TOKENS:
        out_dir, tok_dir, engine, repeats = TOKENS[label]
    else:
        (out_dir, _, engine, repeats), tok_dir = PRIMARY[label], None
    rows = []
    for fid, gt in gts.items():
        pages = pages_of(fid)
        G = gt_values(gt)
        eng = value_pool(RESULTS / engine, pages)
        reps = [value_pool(RESULTS / r, pages) for r in repeats]
        tix = {pg: token_index(RESULTS / tok_dir, pg) for pg in pages} if tok_dir else {}
        for c in cell_signals(RESULTS / out_dir, pages):
            v = c["value"]
            err = error_class(v, G)
            ti = tix.get(c["page"])
            rows.append(dict(c, filing=fid, engine=v in eng, repeat=sum(v in p for p in reps), n_repeat=len(reps),
                             p_min=ti.get(v) if ti else None, correct=err is None, error=err))
    for r in rows:
        r["tier"] = tier(r)
    return rows


def risk_coverage(rows):
    """Accept figures from the most to the least confident; after each confidence group, the share accepted and the
    error rate among them. Order: not suspect > anchored > engine-agreed > more repeat agreements."""
    key = lambda r: (not r["suspect"], r["anchored"], r["engine"], r["repeat"])
    groups = defaultdict(list)
    for r in rows:
        groups[key(r)].append(r)
    pts, acc, wrong = [], 0, 0
    for k in sorted(groups, reverse=True):
        acc += len(groups[k]); wrong += sum(not r["correct"] for r in groups[k])
        pts.append((acc / len(rows), wrong / acc, k))
    return pts


def summarise(rows):
    n = len(rows); wrong = [r for r in rows if not r["correct"]]
    tiers = Counter(r["tier"] for r in rows); werr = Counter(r["tier"] for r in wrong)
    cls = Counter(r["error"] for r in wrong)
    pts = risk_coverage(rows)
    # accept everything above the highest-ranked wrong figure: the coverage at which every error is routed to review
    order = sorted(rows, key=lambda r: (not r["suspect"], r["anchored"], r["engine"], r["repeat"]), reverse=True)
    first_wrong = next((i for i, r in enumerate(order) if not r["correct"]), n)
    k0 = (not order[first_wrong]["suspect"], order[first_wrong]["anchored"], order[first_wrong]["engine"],
          order[first_wrong]["repeat"]) if first_wrong < n else None
    safe = sum(1 for r in order if (not r["suspect"], r["anchored"], r["engine"], r["repeat"]) > k0) if k0 else n
    return dict(figures=n, wrong=len(wrong), error_rate=len(wrong) / n if n else 0, error_classes=dict(cls),
                tiers={t: tiers[t] for t in ("HIGH", "MEDIUM", "LOW")},
                wrong_by_tier={t: werr[t] for t in ("HIGH", "MEDIUM", "LOW")},
                caught_by_low=werr["LOW"] / len(wrong) if wrong else None,
                caught_by_low_medium=(werr["LOW"] + werr["MEDIUM"]) / len(wrong) if wrong else None,
                coverage_all_caught=safe / n if n else 0,
                risk_coverage=[(round(c, 4), round(r, 5)) for c, r, _ in pts])


def gt_row_values(gt, page, label):
    """Values of the ground-truth row a repaired cell belongs to: best label match among the statements printed on
    that page (rapidfuzz partial ratio >= 80), else None."""
    from rapidfuzz import fuzz
    lab = validate.norm_label(label or "")
    if not lab.strip():
        return None
    pno = int(page.rsplit("_p", 1)[1])
    best, vals = 0, None
    for st in gt["statements"]:
        if pno not in st["pages"]:
            continue
        for r in st["rows"]:
            sc = fuzz.partial_ratio(lab, validate.norm_label(r.get("label_ar") or ""))
            if sc > best:
                best = sc
                vals = {norm(v) if isinstance(v, (int, float)) and v != 0 else 0.0 for v in (r.get("values") or {}).values()}
    return vals if best >= 80 else None


def auroc(rows):
    """Chance that a wrong figure has a lower token probability than a correct one (ties count half)."""
    w = sorted(r["p_min"] for r in rows if not r["correct"] and r["p_min"] is not None)
    c = sorted(r["p_min"] for r in rows if r["correct"] and r["p_min"] is not None)
    if not w or not c:
        return None
    import bisect
    return sum(len(c) - bisect.bisect_right(c, x) + 0.5 * (bisect.bisect_right(c, x) - bisect.bisect_left(c, x)) for x in w) / (len(w) * len(c))


def votes(r, tau):
    return int(r["anchored"]) + int(r["engine"]) + int(r["p_min"] is not None and r["p_min"] >= tau)


def vote_tier(r, tau):
    """2 of 3 signals: HIGH needs two of anchored / engine-agreed / token probability >= tau and no broken total."""
    if r["suspect"] or votes(r, tau) == 0:
        return "LOW"
    return "HIGH" if votes(r, tau) >= 2 else "MEDIUM"


def pilot_tier(r):
    """The pilot's rule with token probabilities: LOW also when any digit token is below 0.95."""
    if r["suspect"] or (not r["anchored"] and not r["engine"]) or (r["p_min"] is not None and r["p_min"] < 0.95):
        return "LOW"
    return "HIGH" if r["anchored"] and r["engine"] else "MEDIUM"


def tier_stats(rows, fn):
    n = len(rows); wrong = [r for r in rows if not r["correct"]]
    t = Counter(fn(r) for r in rows); w = Counter(fn(r) for r in wrong)
    return dict(figures=n, wrong=len(wrong), high=t["HIGH"] / n if n else 0, high_wrong=w["HIGH"],
                review=(t["MEDIUM"] + t["LOW"]) / n if n else 0,
                caught=(w["MEDIUM"] + w["LOW"]) / len(wrong) if wrong else None)


def token_analysis(label, splits):
    rows = {sp: figure_rows(label, gts) for sp, gts in splits.items()}
    cov = {sp: sum(r["p_min"] is not None for r in rs) / len(rs) for sp, rs in rows.items()}
    # threshold chosen on the development split: the lowest tau whose HIGH tier holds no wrong figure there
    tau = next((t for t in TAUS if tier_stats(rows["dev"], lambda r: vote_tier(r, t))["high_wrong"] == 0), None)
    res = dict(tau=tau, token_coverage=cov, auroc={sp: auroc(rs) for sp, rs in rows.items()})
    for sp, rs in rows.items():
        res[sp] = dict(two_signals=tier_stats(rs, tier), pilot=tier_stats(rs, pilot_tier),
                       votes=tier_stats(rs, lambda r: vote_tier(r, tau)) if tau is not None else None)
    res["high_wrong_examples"] = [dict(page=r["page"], value=r["value"], p_min=r["p_min"], error=r["error"])
                                  for r in rows["test"] if tau is not None and vote_tier(r, tau) == "HIGH" and not r["correct"]]
    return res


def verification(label, gts):
    before, after = VERIFY[label]
    counts = Counter(); fixes_out = []
    flags = 0
    for fid, gt in gts.items():
        G = gt_values(gt)
        rep, _ = validate.validate_doc(str(RESULTS / before), pages_of(fid))
        flags += len(rep["flags"])
        for f in rep["fixes"]:
            a, b = abs(f["from"]), abs(f["to"])
            # figures of 1,000 or more: against all figures of the filing (a chance match is very unlikely at that
            # size, and garbled labels can mislead a row match); smaller ones (per-share lines, units): against the
            # cell's own ground-truth row, found by its label, where a chance match elsewhere in the filing is likely
            row = gt_row_values(gt, f["page"], f["row"]) if max(a, b) < 1000 else None
            ok_a, ok_b = (a in row, b in row) if row is not None else (G[a] > 0, G[b] > 0)
            kind = ("repaired" if ok_b and not ok_a else "damaged" if ok_a and not ok_b
                    else "both right" if ok_a else "both wrong")
            counts[kind] += 1
            fixes_out.append(dict(filing=fid, page=f["page"], row=f["row"], old=f["from"], new=f["to"], rule=f["rule"], kind=kind))
    return dict(fixes=sum(counts.values()), **{k: counts[k] for k in ("repaired", "damaged", "both wrong", "both right")},
                flagged_totals=flags, detail=fixes_out)


def plot(curves, high_share, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams['pdf.fonttype'] = 42; plt.rcParams['ps.fonttype'] = 42  # TrueType, not Type 3 (embedded fonts)
    fig, ax = plt.subplots(figsize=(6.4, 4.0), dpi=150)
    styles = {"dots.mocr pipeline, seed 0": ("#1f5fa8", "-"), "Chandra OCR 2, own input size": ("#c0392b", "--")}
    for label, pts in curves.items():                   # one point per confidence group, most confident first
        xs = [100 * c for c, _ in pts]; ys = [100 * r for _, r in pts]
        col, ls = styles.get(label, ("#555", ":"))
        ax.plot(xs, ys, color=col, ls=ls, lw=2, marker="o", ms=4, label=label)
    h = 100 * min(high_share.values())
    ax.axvline(h, color="#888", lw=0.8, ls=":")
    ax.annotate(f"HIGH tier only: {h:.0f}% of figures\naccepted, no errors", xy=(h, 0), xytext=(h - 5.5, 0.30),
                fontsize=8, color="#444", arrowprops=dict(arrowstyle="->", color="#888", lw=0.8))
    ax.set_xlabel("Figures accepted without review (%)")
    ax.set_ylabel("Error rate among accepted figures (%)")
    ax.set_xlim(85, 100.5); ax.set_ylim(0, None)
    ax.grid(True, color="#e3e3e3", lw=0.6); ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.legend(frameon=False, loc="upper left", fontsize=8)
    # title in the caption: ax.set_title("Risk–coverage on the held-out test split (22 filings, about 5,000 figures each)", fontsize=9)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(path.with_suffix("." + ext))


def main():
    splits = {sp or "all": score.load_gt(str(PAPER / "gt"), sp) for sp in ("test", "dev", None)}
    summary = {"confidence": {}, "verification": {}}
    per_fig = {}
    for label in PRIMARY:
        summary["confidence"][label] = {}
        for sp, gts in splits.items():
            rows = figure_rows(label, gts)
            summary["confidence"][label][sp] = summarise(rows)
            if sp == "test":
                per_fig[label] = rows
        print("confidence:", label, flush=True)
    for label in VERIFY:
        summary["verification"][label] = {sp: verification(label, gts) for sp, gts in splits.items()}
        print("verification:", label, flush=True)
    summary["tokens"] = {}
    for label, (out_dir, tok_dir, _, _) in TOKENS.items():
        if (RESULTS / out_dir).exists() and any((RESULTS / tok_dir).glob("*.tok.json")):
            summary["tokens"][label] = token_analysis(label, splits)
            print("tokens:", label, flush=True)
    (PAPER / "bench" / "figures").mkdir(exist_ok=True)
    shown = ("dots.mocr pipeline, seed 0", "Chandra OCR 2, own input size")
    plot({k: summary["confidence"][k]["test"]["risk_coverage"] for k in shown},
         {k: summary["confidence"][k]["test"]["tiers"]["HIGH"] / summary["confidence"][k]["test"]["figures"] for k in shown},
         PAPER / "bench" / "figures" / "risk_coverage")
    pct = lambda x: "–" if x is None else f"{100 * x:.1f}%"
    out = ["# RQ2 — verification and confidence routing (32-filing benchmark)", "",
           "Signals use no ground truth; the approved ground truth only scores them. Definitions are in the header of "
           "`bench/confidence32.py`. Token probabilities, the third pilot signal, come from a separate re-run and are "
           "analysed in their own section below.", "",
           "## Arithmetic verification (automatic repairs)", "",
           "Each repair is one single-digit edit that makes a broken printed total reconcile, accepted only when it is the "
           "unique such edit. Scored against the ground truth: figures of 1,000 or more against all figures of the filing, "
           "smaller ones (per-share lines) against the cell's own row, found by its label. Repaired = wrong before, right "
           "after; damaged = the reverse.", "",
           "| Output | Split | Repairs | Repaired | Damaged | Both wrong | Both right | Totals flagged, not repaired |",
           "|---|---|---:|---:|---:|---:|---:|---:|"]
    for label, by in summary["verification"].items():
        for sp in ("test", "dev", "all"):
            v = by[sp]
            out.append(f"| {label} | {sp} | {v['fixes']} | {v['repaired']} | {v['damaged']} | {v['both wrong']} | "
                       f"{v['both right']} | {v['flagged_totals']} |")
    out += ["", "## Confidence tiers on the delivered output (test split, 22 filings)", "",
            "| Output | Figures | Wrong | Error rate | HIGH (wrong) | MEDIUM (wrong) | LOW (wrong) | Errors caught by reviewing LOW | …LOW + MEDIUM | Accepted with every error caught |",
            "|---|---:|---:|---:|---|---|---|---:|---:|---:|"]
    for label, by in summary["confidence"].items():
        s = by["test"]; t, w = s["tiers"], s["wrong_by_tier"]; n = s["figures"]
        out.append(f"| {label} | {n:,} | {s['wrong']} | {pct(s['error_rate'])} | "
                   f"{100 * t['HIGH'] / n:.1f}% ({w['HIGH']}) | {100 * t['MEDIUM'] / n:.1f}% ({w['MEDIUM']}) | "
                   f"{100 * t['LOW'] / n:.1f}% ({w['LOW']}) | {pct(s['caught_by_low'])} | {pct(s['caught_by_low_medium'])} | "
                   f"{pct(s['coverage_all_caught'])} |")
    out += ["", "Error classes (test split):", "", "| Output | Misread digit | Separator/scale | Other |", "|---|---:|---:|---:|"]
    for label, by in summary["confidence"].items():
        c = by["test"]["error_classes"]
        out.append(f"| {label} | {c.get('misread digit', 0)} | {c.get('separator/scale', 0)} | {c.get('other', 0)} |")
    out += ["", "## The same rule on the other splits", "",
            "| Output | Split | Figures | Wrong | Error rate | HIGH share | Wrong in HIGH | Errors caught by reviewing LOW + MEDIUM |",
            "|---|---|---:|---:|---:|---:|---:|---:|"]
    for label, by in summary["confidence"].items():
        for sp in ("dev", "all"):
            s_ = by[sp]; n = s_["figures"]
            out.append(f"| {label} | {sp} | {n:,} | {s_['wrong']} | {pct(s_['error_rate'])} | {100 * s_['tiers']['HIGH'] / n:.1f}% | "
                       f"{s_['wrong_by_tier']['HIGH']} | {pct(s_['caught_by_low_medium'])} |")
    if summary["tokens"]:
        out += ["", "## Adding token probabilities (step 2)", "",
                "The same outputs re-generated with token log-probabilities returned (a fresh run of the same configuration, "
                "since batching changes some outputs). A figure's token probability is the lowest probability among the tokens "
                "of its digits. Three rules on the held-out test split: the two-signal rule above; the pilot's rule (a digit "
                "token below 0.95 also sends a figure to LOW); and 2 of 3 signals (HIGH needs two of anchored, engine-agreed "
                "and token probability at or above a threshold chosen on the development split).", "",
                "| Output | Rule | Threshold | Figures | Wrong | Accepted (HIGH) | Wrong accepted | Sent to review | Errors caught |",
                "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
        for label, tr in summary["tokens"].items():
            t = tr["test"]
            for name, key, thr in (("two signals", "two_signals", "–"), ("pilot rule", "pilot", "0.95"),
                                   ("2 of 3 signals", "votes", tr["tau"])):
                st_ = t[key]
                if st_ is None:
                    out.append(f"| {label} | {name} | none safe on dev | | | | | | |")
                    continue
                out.append(f"| {label} | {name} | {thr} | {st_['figures']:,} | {st_['wrong']} | {100 * st_['high']:.1f}% | "
                           f"{st_['high_wrong']} | {100 * st_['review']:.1f}% | {pct(st_['caught'])} |")
        out += ["", "Separation by token probability alone (area under the ROC curve, wrong against correct figures; "
                "0.5 = no information) and the share of figures whose digits were found in the token stream:", "",
                "| Output | AUROC test | AUROC dev | Figures with token probabilities (test) |", "|---|---:|---:|---:|"]
        for label, tr in summary["tokens"].items():
            fmt = lambda x: "–" if x is None else f"{x:.3f}"
            out.append(f"| {label} | {fmt(tr['auroc']['test'])} | {fmt(tr['auroc']['dev'])} | {pct(tr['token_coverage']['test'])} |")
        out += ["", "**Reading.** Token probabilities separate wrong from correct figures only moderately, and the costliest "
                "misreads are confident ones: decimal-separator confusions on per-unit values (2.8374 read as 28,374) score "
                "above 0.99. The pilot's rule costs review time without catching anything the two structural signals miss. "
                "Promoting figures on token probability is unsafe: for dots.mocr no threshold kept the development split's "
                "errors out; for Chandra OCR 2 the development split holds only 2 errors, and the threshold chosen there let "
                "14 wrong figures through on the test split. On this benchmark, anchoring and engine agreement do the work; "
                "token probabilities are at most a tie-breaker inside the review queue."]
        ex = [(l, e) for l, tr in summary["tokens"].items() for e in tr["high_wrong_examples"]]
        out += ["", "Wrong figures accepted under 2 of 3 signals (test): " + ("none." if not ex else
                "; ".join(f"{e['page']} {e['value']:,.0f} (p={e['p_min']:.3f}, {e['error']})" for l, e in ex))]
    high_wrong = [(label, sp) for label, by in summary["confidence"].items() for sp in ("test", "dev", "all")
                  if by[sp]["wrong_by_tier"]["HIGH"]]
    out += ["", "Wrong figures in the HIGH tier: " + ("none, in any split or configuration." if not high_wrong else
            ", ".join(f"{l} ({sp})" for l, sp in high_wrong)), "",
            "![Risk–coverage](figures/risk_coverage.png)", "",
            "## Limitations", "",
            "- **Value-level scoring.** A figure counts as correct when its value occurs in the filing's ground truth; a right "
            "value in the wrong row or column, or a misread that happens to equal another figure of the filing, is not caught. "
            "Row recall in `RESULTS.md` covers placement.",
            "- **Omissions are out of scope here.** Per-figure confidence can only rank figures that were emitted. Dropped rows "
            "and columns are found by the structure check and by printed totals that no longer reconcile (the flagged totals above).",
            "- **Figure filter.** Figures of 1,000 or more, or with decimals (97.0% of the test split's non-zero ground-truth "
            "figures); small integers are left out because chance matches with note references and units are common.",
            "- **Repairs can hurt.** Three repairs across all configurations broke a correct figure: an earnings-per-share line "
            "(−1.8 → 0) pulled into a sum by dots.mocr seeds 1 and 2 on Herfy, and one wrong-cell repair by Chandra OCR 2 at "
            "200 dpi on Maadaniyah. Excluding per-share lines from sum checks would prevent the first; any such change should "
            "be tuned on the development split only.",
            "- **Engine agreement uses Chandra OCR 2 and dots.mocr as each other's second reader.** Both are self-hosted; a "
            "hosted second reader would defeat the purpose for sensitive documents.", ""]
    (PAPER / "bench" / "CONFIDENCE.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    json.dump({"summary": summary, "test_figures": per_fig}, open(PAPER / "bench" / "confidence_summary.json", "w"),
              ensure_ascii=False, indent=1, default=str)
    print("\n".join(out))


if __name__ == "__main__":
    main()
