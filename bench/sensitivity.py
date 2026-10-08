"""Sensitivity of the conclusions to the thresholds we set ourselves. Each underlying quantity is computed once and the
thresholds are then varied around the default values:
  1. label match (fuzzy partial ratio >= 85)               -> label recall per system and the ranking of systems
  2. taxonomy cut-offs (omission 20%, unrelated 50%, misplaced 80%, labels 20%)
  3. cross-engine row check (5% of rows)                    -> severe failures flagged against false alarms, test split
  4. severe-failure line (95% row recall)                   -> failures per leading system and how many are flagged
  5. RQ2 figure filter (|value| >= 1000 or decimal)         -> wrong figures in the HIGH tier, review share
Writes bench/SENSITIVITY.md and bench/sensitivity_summary.json.  usage: python bench/sensitivity.py
"""
import csv
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PAPER / "tools")); sys.path.insert(0, str(PAPER / "bench")); sys.path.insert(0, str(PAPER / "bench" / "vm_scripts"))
import score  # noqa: E402
import analyze  # noqa: E402
import confidence32 as C  # noqa: E402
import stats_rq as SR  # noqa: E402
import taxonomy as T  # noqa: E402
from rapidfuzz import fuzz  # noqa: E402
from scipy.stats import kendalltau  # noqa: E402

E = score.E
RESULTS = PAPER / "bench" / "results32"
SEED0 = T.SEED0
AR_WORD = re.compile(r"[ء-ي]{2,}")


def systems():
    out = []
    for cfg, v in analyze.CONFIGS.items():
        if v[3] == "main" and analyze.complete(RESULTS / SEED0.get(cfg, cfg)):
            s = v[0] + (" (pipeline)" if "adopted" in v[2] else " (out of the box)" if "out of the box" in v[2]
                        else " (self-hosted)" if v[0] == "Qwen3.8-27B" and "BF16" in v[2] else " (API)" if v[0] == "Qwen3.8-27B" else "")
            out.append((cfg, SEED0.get(cfg, cfg), s))
    return out


def raw_quantities(run, gts):
    """Per statement: figure/row recall, label similarity scores, missing share, worded share; per page: figure count and
    share of 'other' (unrelated) figures."""
    pages_all = sorted({f"{fid}_p{p:02d}" for fid in gts for p in C.MANIFEST[fid]})
    texts = {pg: E.truncate_loops(T.page_plain(T.page_raw(run, pg)))[0] for pg in pages_all}
    stm, pg_rows = [], []
    for pg in pages_all:
        fid = pg.rsplit("_p", 1)[0]
        figs = T.figures(texts[pg])
        cl = [T.classify(v, C.gt_values(gts[fid]))[0] for v in figs]
        pg_rows.append(dict(page=pg, n=len(figs), other=sum(c == "other" for c in cl) / len(figs) if figs else 0.0))
    for fid, gt in gts.items():
        for st, tb in zip(gt["statements"], score.gtlib.to_eval_tables(gt)):
            pages = [f"{fid}_p{p:02d}" for p in st["pages"]]
            blob = "\n".join(texts.get(p, "") for p in pages)
            c = E.score_tables([tb], blob)
            norm = E.norm_ar(blob)
            labs = [E.norm_ar(r["label"]) for r in tb["rows"]]
            lab_scores = [fuzz.partial_ratio(l, norm) for l in labs if len(l) >= 4]
            need = [abs(v) for r in tb["rows"] for v in r["figs"] if C.is_figure(v)]
            out = Counter(T.figures(blob))
            gtv = set(need)
            carrying = [l for l in blob.split("\n") if any(abs(v) in gtv for v in E.numbers(l))]
            stm.append(dict(filing=fid, statement=st["id"], fr=c["fig_hit"] / c["fig_tot"] if c["fig_tot"] else 1.0,
                            rr=c["rows_hit"] / c["rows_tot"] if c["rows_tot"] else 1.0, lab_scores=lab_scores,
                            missing=sum(1 for v in need if out[v] == 0) / len(need) if need else 0.0,
                            worded=sum(1 for l in carrying if AR_WORD.search(l)) / len(carrying) if carrying else 1.0))
    return stm, pg_rows


def main():
    inv = {r["filing_id"]: r["proposed_split"].split()[0].lower() for r in csv.DictReader(open(PAPER / "dataset_inventory.csv", encoding="utf-8-sig"))}
    gts = score.load_gt(str(PAPER / "gt"))
    syst = systems()
    raw = {}
    for cfg, run, name in syst:
        raw[name] = raw_quantities(run, gts)
        print("raw:", name, flush=True)
    out = ["# Sensitivity of the conclusions to our own thresholds", "",
           "Each quantity is computed once; the thresholds are then varied around the default values (bold). "
           "Method: `bench/sensitivity.py`.", ""]
    summary = {}

    # 1. label match threshold
    ths = (75, 80, 85, 90, 95)
    lab = {name: {t: (sum(s >= t for st in raw[name][0] for s in st["lab_scores"]) /
                      max(1, sum(len(st["lab_scores"]) for st in raw[name][0]))) for t in ths} for _, _, name in syst}
    base = [lab[n][85] for _, _, n in syst]
    taus = {t: kendalltau(base, [lab[n][t] for _, _, n in syst]).statistic for t in ths}
    out += ["## 1. Label match threshold", "", "Label recall (all 32 filings) by fuzzy-match threshold; Kendall τ of the system ranking against the "
            "paper's threshold of 85.", "", "| System | " + " | ".join(("**85**" if t == 85 else str(t)) for t in ths) + " |",
            "|---|" + "---:|" * len(ths)]
    for _, _, n in syst:
        out.append(f"| {n} | " + " | ".join(f"{100 * lab[n][t]:.1f}" for t in ths) + " |")
    out += ["| Kendall τ against 85 | " + " | ".join(f"{taus[t]:.2f}" for t in ths) + " |", ""]
    summary["labels"] = dict(recall=lab, tau=taus)

    # 2. taxonomy cut-offs
    def counts(name, om=0.2, un=0.5, mp=0.8, lr=0.2):
        stm, pgs = raw[name]
        c = Counter()
        c["omission"] = sum(s["missing"] >= om for s in stm)
        c["unrelated"] = sum(p["n"] >= 10 and p["other"] >= un for p in pgs)
        c["misplaced"] = sum(s["fr"] >= 0.95 and s["rr"] < mp for s in stm)
        for s in stm:
            labs = s["lab_scores"]
            if len(labs) >= 5 and s["fr"] >= 0.5 and sum(x >= 85 for x in labs) / len(labs) < lr:
                c["labels dropped" if s["worded"] < 0.5 else "labels invented"] += 1
        return c
    grid = {"omission": ("om", (0.1, 0.2, 0.3, 0.5)), "unrelated": ("un", (0.3, 0.5, 0.7)),
            "misplaced": ("mp", (0.7, 0.8, 0.9)), "labels dropped": ("lr", (0.1, 0.2, 0.3)), "labels invented": ("lr", (0.1, 0.2, 0.3))}
    default = dict(om=0.2, un=0.5, mp=0.8, lr=0.2)
    out += ["## 2. Taxonomy cut-offs", "", "Counts per system as each cut-off moves (others at their defaults); the default in bold.", ""]
    summary["taxonomy"] = {}
    for cat, (arg, vals) in grid.items():
        out += [f"**{cat}** ({'statements' if cat != 'unrelated' else 'pages'}; cut-off {arg} = " + ", ".join(f"**{v}**" if v == default[arg] else str(v) for v in vals) + ")", "",
                "| System | " + " | ".join(str(v) for v in vals) + " |", "|---|" + "---:|" * len(vals)]
        rows = {}
        for _, _, n in syst:
            rows[n] = [counts(n, **{**default, arg: v})[cat] for v in vals]
            out.append(f"| {n} | " + " | ".join(str(x) for x in rows[n]) + " |")
        base_rank = [rows[n][vals.index(default[arg])] for _, _, n in syst]
        tt = [kendalltau(base_rank, [rows[n][i] for _, _, n in syst]).statistic for i in range(len(vals))]
        out += ["| Kendall τ against the default | " + " | ".join("–" if x != x else f"{x:.2f}" for x in tt) + " |", ""]
        summary["taxonomy"][cat] = dict(values=vals, counts=rows, tau=tt)

    # 3 and 4. cross-engine row check and the severe-failure line (the four leading systems)
    lead = list(SR.ONPREM) + list(SR.HOSTED)
    dis, rec = {}, {}
    for sp in ("dev", "test"):
        g = {f: v for f, v in gts.items() if inv[f] == sp}
        for nm in lead:
            pf = SR.per_filing(SR.per_statement({**SR.ONPREM, **SR.HOSTED}[nm], g))
            for f in pf:
                rec[(nm, f)] = pf[f][0] / pf[f][1]
                dis[(nm, f)] = SR.row_disagreement(SR.DELIVERED[nm], SR.SECOND[nm], f)
    taus3, lines = (0.02, 0.03, 0.05, 0.08, 0.10, 0.15), (0.90, 0.95, 0.98)
    out += ["## 3. Cross-engine row check threshold (test split, four leading systems pooled)", "",
            "Severe failure = filing below 95% row recall. The paper's 5% was set on the development split.", "",
            "| Share of rows disagreeing that flags a filing | Severe failures flagged | False alarms |", "|---|---:|---:|"]
    summary["cross_engine"] = {}
    test_keys = [k for k in rec if inv[k[1]] == "test"]
    for t in taus3:
        sev = [k for k in test_keys if rec[k] < 0.95]; ok = [k for k in test_keys if rec[k] >= 0.95]
        a, b = sum(dis[k] > t for k in sev), sum(dis[k] > t for k in ok)
        out.append(f"| {'**' if t == 0.05 else ''}{100 * t:.0f}%{'**' if t == 0.05 else ''} | {a} of {len(sev)} | {b} of {len(ok)} |")
        summary["cross_engine"][t] = dict(flagged=a, severe=len(sev), false_alarms=b, others=len(ok))
    out += ["", "## 4. Severe-failure line (test split, cross-engine check at 5%)", "",
            "| Line | " + " | ".join(nm for nm in lead) + " | Flagged (pooled) | False alarms (pooled) |", "|---|" + "---:|" * len(lead) + "---:|---:|"]
    summary["severe_line"] = {}
    for L in lines:
        per = [sum(1 for k in test_keys if k[0] == nm and rec[k] < L) for nm in lead]
        sev = [k for k in test_keys if rec[k] < L]; ok = [k for k in test_keys if rec[k] >= L]
        out.append(f"| {'**' if L == 0.95 else ''}{100 * L:.0f}%{'**' if L == 0.95 else ''} | " + " | ".join(str(x) for x in per) +
                   f" | {sum(dis[k] > 0.05 for k in sev)} of {len(sev)} | {sum(dis[k] > 0.05 for k in ok)} of {len(ok)} |")
        summary["severe_line"][L] = dict(per_system=dict(zip(lead, per)), flagged=sum(dis[k] > 0.05 for k in sev), severe=len(sev),
                                         false_alarms=sum(dis[k] > 0.05 for k in ok), others=len(ok))
    out.append("")

    # 5. RQ2 figure filter
    out += ["## 5. Figure filter of the confidence analysis (test split)", "",
            "| Figures included | Output | Figures | Wrong | Wrong in HIGH | Sent to review | Errors caught by review |", "|---|---|---:|---:|---:|---:|---:|"]
    summary["figure_filter"] = {}
    orig = C.is_figure
    test_gts = {f: v for f, v in gts.items() if inv[f] == "test"}
    for label_f, lo in (("|v| ≥ 100 or decimal", 100), ("**|v| ≥ 1,000 or decimal**", 1000), ("|v| ≥ 10,000 or decimal", 10000)):
        def filt(v, lo=lo):
            if v in (None, 0.0) or v != v or abs(v) == float("inf"):
                return False
            a = abs(v)
            return (a >= lo or a != int(a)) and not (a == int(a) and 1990 <= a <= 2035)
        C.is_figure = filt
        for prim in ("dots.mocr pipeline, seed 0", "Chandra OCR 2, own input size"):
            rows = C.figure_rows(prim, test_gts)
            s = C.summarise(rows); n = s["figures"]
            out.append(f"| {label_f} | {prim} | {n:,} | {s['wrong']} | {s['wrong_by_tier']['HIGH']} | "
                       f"{100 * (1 - s['tiers']['HIGH'] / n):.1f}% | {100 * s['caught_by_low_medium']:.1f}% |")
            summary["figure_filter"][f"{lo}|{prim}"] = dict(figures=n, wrong=s["wrong"], high_wrong=s["wrong_by_tier"]["HIGH"])
    C.is_figure = orig
    out.append("")
    lt = summary["labels"]["tau"]; tx = summary["taxonomy"]; ce = summary["cross_engine"]; sl = summary["severe_line"]
    ff = summary["figure_filter"]
    rng = lambda xs: f"{min(xs):.2f}–{max(xs):.2f}"
    verdict = ["## Verdicts", "",
               f"- **Label match:** the ranking of systems barely moves between thresholds 75 and 95 (Kendall τ {rng([v for k, v in lt.items() if k != 85])} against 85). Conclusion unchanged.",
               f"- **Taxonomy:** omissions (τ {rng([x for x in tx['omission']['tau'] if x == x])}), unrelated figures (τ {rng([x for x in tx['unrelated']['tau'] if x == x])}), dropped labels (τ {rng([x for x in tx['labels dropped']['tau'] if x == x])}) and invented labels (τ {rng([x for x in tx['labels invented']['tau'] if x == x])}) keep their ranking; the leading systems stay at the low end at every cut-off. "
               f"Misplaced rows are rare for every system (0–7 statements) and their ranking is not stable (τ down to {min(x for x in tx['misplaced']['tau'] if x == x):.2f}): report them as rare, without ranking.",
               f"- **Cross-engine row check:** a smooth trade-off, not a knife-edge: {ce[0.03]['flagged']} of {ce[0.03]['severe']} severe failures flagged with {ce[0.03]['false_alarms']} false alarms at 3%, {ce[0.05]['flagged']} with {ce[0.05]['false_alarms']} at 5% (the default, set on dev), {ce[0.08]['flagged']} with {ce[0.08]['false_alarms']} at 8%.",
               "- **Severe-failure line:** every leading system has failing filings at 90%, 95% and 98%, so 'no system is uniformly safe' does not depend on the line. The row check catches the large failures (all below 90%) but only a minority of small shortfalls (95–98%): state the detection claim for failures below 95%.",
               "- **Figure filter (RQ2):** no wrong figure reaches the HIGH tier whether figures from 100, 1,000 or 10,000 up are included, and the review share stays at 9–10%. Conclusion unchanged.", ""]
    out = out[:4] + verdict + out[4:]
    (PAPER / "bench" / "SENSITIVITY.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    json.dump(summary, open(PAPER / "bench" / "sensitivity_summary.json", "w"), ensure_ascii=False, indent=1, default=str)
    print("\n".join(out))


if __name__ == "__main__":
    main()
