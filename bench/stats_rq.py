"""Inferential statistics for the research questions (held-out test split unless stated).

RQ1 — non-inferiority of on-premises systems against hosted services on row recall. For each pair (leading on-premises
      configuration A, leading hosted service B) the difference A − B is estimated on the same statements and
      bootstrapped by FILING (the 22 held-out filings are the resampling units, because errors cluster within a filing).
      A is non-inferior at margin δ when the one-sided 95% lower bound of A − B lies above −δ. The smallest margin each
      comparison passes is reported, and the statement-level interval is shown for contrast.
RQ2 — upper bounds on the error rate among automatically accepted figures: with k wrong among n accepted, the exact
      one-sided 95% Clopper–Pearson bound (k = 0: 1 − 0.05^(1/n), about 3/n). Figures are treated as independent,
      which clustering within filings makes optimistic; the filing count is reported alongside.
Writes bench/STATS.md and bench/stats_summary.json.  usage: python bench/stats_rq.py [--boot 10000]
"""
import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PAPER / "tools"))
import score  # noqa: E402

RESULTS = PAPER / "bench" / "results32"
DELTA = 0.02                                   # non-inferiority margin: 2 points of row recall
ONPREM = {"dots.mocr adopted pipeline (3 seeds)": [f"dots_mocr_clahe_s{s}_bm_ver" for s in (0, 1, 2)],
          "Chandra OCR 2 (own input size)": ["chandra2_chandra_cap"]}
HOSTED = {"Mistral OCR": ["mistral_ocr_plain"], "Cohere Parse": ["cohere_parse_plain"], "LandingAI ADE": ["landingai_ade_plain"]}
# nace.ai Parse (added 9 Oct 2026) is a commercial service but not a leading one (85.9% row recall in its best mode), so it is
# left out of the leading-five statistics (non-inferiority, severe failures, row-check flags).


def per_statement(runs, gts):
    """{(filing, statement): (mean rows hit over runs, rows)} — seeds averaged, as in the main table."""
    acc = defaultdict(list); tot = {}
    for run in runs:
        _, ps, _ = score.score_model(RESULTS / run, gts)
        for s in ps:
            acc[(s["filing"], s["statement"])].append(s["rows_hit"]); tot[(s["filing"], s["statement"])] = s["rows_tot"]
    return {k: (sum(v) / len(v), tot[k]) for k, v in acc.items()}


def recall(keys, S):
    h = sum(S[k][0] for k in keys); t = sum(S[k][1] for k in keys)
    return h / t if t else float("nan")


def boot_diff(A, B, unit, n, seed=0):
    """Bootstrap A − B in row recall; unit = 'filing' (cluster) or 'statement'."""
    keys = sorted(set(A) & set(B))
    groups = defaultdict(list)
    for k in keys:
        groups[k[0] if unit == "filing" else k].append(k)
    ids = sorted(groups); rng = random.Random(seed); out = []
    for _ in range(n):
        ks = [k for g in (rng.choice(ids) for _ in ids) for k in groups[g]]
        out.append(recall(ks, A) - recall(ks, B))
    out.sort()
    return dict(diff=recall(keys, A) - recall(keys, B), lo95_one_sided=out[int(0.05 * n)],
                ci95=(out[int(0.025 * n)], out[int(0.975 * n) - 1]), units=len(ids))


DELIVERED = {  # output whose printed totals are checked for each system (after verification where the pipeline has it)
    "dots.mocr adopted pipeline (3 seeds)": "dots_mocr_clahe_s0_bm_ver", "Chandra OCR 2 (own input size)": "chandra2_chandra_cap_ver",
    "Mistral OCR": "mistral_ocr_plain", "Cohere Parse": "cohere_parse_plain", "LandingAI ADE": "landingai_ade_plain"}


def per_filing(S):
    f = defaultdict(lambda: [0.0, 0])
    for (fid, _), (h, t) in S.items():
        f[fid][0] += h; f[fid][1] += t
    return {k: (h, t) for k, (h, t) in f.items()}


def flagged_totals(run, fid):
    """Printed totals that still do not reconcile in a system's output for one filing (validate.py, no ground truth)."""
    sys.path.insert(0, str(PAPER / "bench" / "vm_scripts"))
    import validate
    manifest = json.loads((PAPER / "bench" / "vm_scripts" / "pages32_manifest.json").read_text())
    rep, _ = validate.validate_doc(str(RESULTS / run), [f"{fid}_p{p:02d}" for p in manifest[fid]])
    return len(rep["flags"]), rep["stats"]["relationships"]


SECOND = {  # second, self-hosted reader used for the cross-engine row check of each system's delivered output
    "dots.mocr adopted pipeline (3 seeds)": "chandra2_chandra_cap", "Chandra OCR 2 (own input size)": "dots_mocr_clahe_s0_bm_ver",
    "Mistral OCR": "dots_mocr_clahe_s0_bm_ver", "Cohere Parse": "dots_mocr_clahe_s0_bm_ver",
    "LandingAI ADE": "dots_mocr_clahe_s0_bm_ver"}
TAU_ROWS = 0.05     # filing flagged when more than 5% of the second reader's rows are not found as a row of the output;
                    # set on the development split, where it flags every severe failure of both self-hosted engines


def row_tuples(run, fid):
    """Rows (lines with >= 2 figures) of a system's output for one filing, as multisets of figure values."""
    sys.path.insert(0, str(PAPER / "bench"))
    from collections import Counter
    import confidence32 as C
    out = []
    for pg in C.pages_of(fid):
        f = RESULTS / run / f"{pg}.md"
        if not f.exists():
            continue
        txt, _ = score.E.truncate_loops("\n".join(score.E.lines_of(score.E.extract_text(f.read_text(errors="replace")))))
        for line in txt.split("\n"):
            vals = [abs(v) for v in score.E.numbers(line) if C.is_figure(v)]
            if len(vals) >= 2:
                out.append(Counter(vals))
    return out


def row_disagreement(run, second, fid):
    """Share of the second reader's rows whose figures do not all appear together on one row of the output."""
    P, Q = row_tuples(run, fid), row_tuples(second, fid)
    return sum(1 for q in Q if not any(not (q - x) for x in P)) / len(Q) if Q else 0.0


def cross_engine_check(split):
    gts = score.load_gt(str(PAPER / "gt"), split)
    runs = {**ONPREM, **HOSTED}; res = {}
    for name in runs:
        pf = per_filing(per_statement(runs[name], gts))
        rows = [(f, pf[f][0] / pf[f][1], row_disagreement(DELIVERED[name], SECOND[name], f)) for f in sorted(pf)]
        sev = [r for r in rows if r[1] < 0.95]; ok = [r for r in rows if r[1] >= 0.95]
        res[name] = dict(severe=len(sev), severe_flagged=sum(d > TAU_ROWS for _, _, d in sev), other=len(ok),
                         other_flagged=sum(d > TAU_ROWS for _, _, d in ok),
                         missed=[dict(filing=f, recall=rr, disagreement=d) for f, rr, d in sev if d <= TAU_ROWS])
    return res


def filing_level(S):
    """Distribution of per-filing row recall, paired ties, and whether severe failures raise flags."""
    PF = {name: per_filing(v) for name, v in S.items()}
    fids = sorted(next(iter(PF.values())))
    dist = {}
    for name, pf in PF.items():
        rr = {f: h / t for f, (h, t) in pf.items()}
        severe = sorted(f for f in fids if rr[f] < 0.95)
        flags = {f: flagged_totals(DELIVERED[name], f) for f in severe}
        dist[name] = dict(at_least_99=sum(rr[f] >= 0.99 for f in fids), between=sum(0.95 <= rr[f] < 0.99 for f in fids),
                          severe=[dict(filing=f, recall=rr[f], flagged_totals=flags[f][0], checked_totals=flags[f][1]) for f in severe],
                          worst=min(rr.values()))
    pairs = []
    for an in ONPREM:
        for bn in HOSTED:
            a, b = PF[an], PF[bn]
            d = [a[f][0] - b[f][0] for f in fids]            # rows hit, on-premises minus hosted
            pairs.append(dict(onprem=an, hosted=bn, better=sum(x > 1 for x in d), tie=sum(abs(x) <= 1 for x in d),
                              worse=sum(x < -1 for x in d)))
    return dict(filings=len(fids), distribution=dist, pairs=pairs)


def cp_upper(k, n, alpha=0.05):
    """Exact one-sided Clopper–Pearson upper bound for k events in n trials."""
    if n == 0:
        return float("nan")
    if k == 0:
        return 1 - alpha ** (1 / n)
    lo, hi = k / n, 1.0                         # bisection on P(X <= k | p) = alpha
    from math import comb
    cdf = lambda p: sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if cdf(mid) > alpha else (lo, mid)
    return hi


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--boot", type=int, default=10000); a = ap.parse_args()
    gts = score.load_gt(str(PAPER / "gt"), "test")
    S = {name: per_statement(runs, gts) for name, runs in {**ONPREM, **HOSTED}.items()}
    rq1 = []
    for an in ONPREM:
        for bn in HOSTED:
            f = boot_diff(S[an], S[bn], "filing", a.boot); s = boot_diff(S[an], S[bn], "statement", a.boot)
            rq1.append(dict(onprem=an, hosted=bn, recall_a=recall(sorted(S[an]), S[an]), recall_b=recall(sorted(S[bn]), S[bn]),
                            filing=f, statement=s, noninferior=f["lo95_one_sided"] > -DELTA,
                            smallest_margin=max(0.0, -f["lo95_one_sided"])))
            print("RQ1", an, "vs", bn, flush=True)
    fl = filing_level(S)
    xc = {sp: cross_engine_check(sp) for sp in ("dev", "test")}
    conf = json.loads((PAPER / "bench" / "confidence_summary.json").read_text())["summary"]["confidence"]
    rq2 = []
    for label, by in conf.items():
        for sp in ("test", "all"):
            s = by[sp]; n = s["tiers"]["HIGH"]; k = s["wrong_by_tier"]["HIGH"]
            rq2.append(dict(output=label, split=sp, accepted=n, wrong_accepted=k, review_share=1 - n / s["figures"],
                            upper95=cp_upper(k, n), filings=22 if sp == "test" else 32))
    pct = lambda x, d=1: f"{100 * x:.{d}f}"
    out = ["# Inferential statistics for the research questions", "",
           "Held-out test split: 22 filings, 107 statements. Scripts: `bench/stats_rq.py`.", "",
           "## RQ1 — Are the leading on-premises systems non-inferior to the leading hosted services?", "",
           f"Row recall difference (on-premises − hosted) on the same statements; filing-level bootstrap ({a.boot:,} "
           f"resamples of the 22 filings). Non-inferior at a margin of {100 * DELTA:.0f} points when the one-sided 95% "
           "lower bound exceeds −2 points. The margin was set after the main results were known; the smallest margin "
           "each comparison passes is given so that readers can apply their own.", "",
           "| On-premises | Hosted | Row recall (on-prem / hosted) | Difference | 95% CI, by filing | One-sided 95% lower bound | Non-inferior at 2 points | Smallest margin passed | 95% CI, by statement (for contrast) |",
           "|---|---|---|---:|---|---:|---|---:|---|"]
    for r in rq1:
        f, s = r["filing"], r["statement"]
        out.append(f"| {r['onprem']} | {r['hosted']} | {pct(r['recall_a'])}% / {pct(r['recall_b'])}% | {pct(f['diff'], 2)} | "
                   f"{pct(f['ci95'][0], 2)} to {pct(f['ci95'][1], 2)} | {pct(f['lo95_one_sided'], 2)} | "
                   f"{'yes' if r['noninferior'] else 'no'} | {pct(r['smallest_margin'], 2)} points | "
                   f"{pct(s['ci95'][0], 2)} to {pct(s['ci95'][1], 2)} |")
    out += ["", "Differences and bounds are in points of row recall.", "",
            "### Where the differences come from", "",
            f"Row recall per filing on the {fl['filings']} held-out filings. A severe failure is a filing below 95% row recall; "
            "flagged totals are printed totals that still do not reconcile in the system's own output, computed without "
            "ground truth (the arithmetic check works on any output, hosted or not).", "",
            "| System | Filings at 99% or more | 95–99% | Below 95% (severe) | Worst filing | Severe failures with at least one flagged total |",
            "|---|---:|---:|---:|---:|---:|"]
    for name, dd in fl["distribution"].items():
        sev = dd["severe"]
        out.append(f"| {name} | {dd['at_least_99']} | {dd['between']} | {len(sev)} | {pct(dd['worst'])}% | "
                   f"{sum(x['flagged_totals'] > 0 for x in sev)} of {len(sev)} |")
    out += ["", "Severe failures: " + "; ".join(f"{name}: " + ", ".join(f"{x['filing']} {pct(x['recall'])}% "
            f"({x['flagged_totals']} flagged of {x['checked_totals']} checked totals)" for x in dd["severe"])
            for name, dd in fl["distribution"].items() if dd["severe"]) + ".", "",
            "Paired by filing (a tie is a difference of at most one row):", "",
            "| On-premises | Hosted | On-premises better | Tie | Hosted better |", "|---|---|---:|---:|---:|"]
    for r in fl["pairs"]:
        out.append(f"| {r['onprem']} | {r['hosted']} | {r['better']} | {r['tie']} | {r['worse']} |")
    out += ["", "### Flagging severe failures without ground truth", "",
            "Cross-engine row check: a filing is flagged when more than 5% of the rows read by a second, self-hosted engine "
            "(Chandra OCR 2 for dots.mocr; the dots.mocr pipeline for every other system) do not appear as a row of the "
            "system's output. The 5% threshold was set on the development split, where it flags every severe failure of both "
            "self-hosted engines. A flag can also mean the second engine failed; either way the filing goes to review.", "",
            "| System | Split | Severe failures flagged | Other filings flagged (false alarms) |", "|---|---|---:|---:|"]
    for sp in ("dev", "test"):
        for name, r in xc[sp].items():
            out.append(f"| {name} | {sp} | {r['severe_flagged']} of {r['severe']} | {r['other_flagged']} of {r['other']} |")
    missed = [(name, m) for name, r in xc["test"].items() for m in r["missed"]]
    out += ["", "Severe failures not flagged on the test split: " + ("none." if not missed else
            "; ".join(f"{n}: {m['filing']} ({100 * m['recall']:.1f}% row recall, {100 * m['disagreement']:.1f}% rows disagreeing)" for n, m in missed) + "."),
            "",
            "## RQ2 — How low is the error rate among automatically accepted figures?", "",
            "HIGH tier = anchored in a reconciling printed total and read identically by the other self-hosted engine "
            "(`bench/CONFIDENCE.md`). Exact one-sided 95% upper bound on the error rate among accepted figures; figures "
            "are treated as independent, which clustering within filings makes optimistic.", "",
            "| Output | Split | Accepted figures | Wrong among accepted | Sent to review | 95% upper bound on error rate among accepted |",
            "|---|---|---:|---:|---:|---:|"]
    for r in rq2:
        out.append(f"| {r['output']} | {r['split']} | {r['accepted']:,} | {r['wrong_accepted']} | {pct(r['review_share'])}% | "
                   f"{pct(r['upper95'], 3)}% |")
    (PAPER / "bench" / "STATS.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    json.dump(dict(delta=DELTA, rq1=rq1, rq1_filings=fl, cross_engine=xc, rq2=rq2), open(PAPER / "bench" / "stats_summary.json", "w"), indent=1)
    print("\n".join(out))


if __name__ == "__main__":
    main()
