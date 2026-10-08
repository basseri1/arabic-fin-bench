"""Compare the five AI test annotators of agent_check with each other and with the fact scorer.

Each annotator judged, blind, the row (same line / duplicate line / another line / no label), whether a reader of the
output would place the figure under the ground-truth line (yes / no), and the period (same / another / no period) of
120 figures drawn by tools/make_agent_check.py, mostly from the scorer's largest error cells. A class follows from the
row and the period in the scorer's own order (period missing, period wrong, row missing, row wrong, else complete; a
duplicate line counts as the right line), so that it compares with the classes of Table 10. The scorer's period status
is read from its verdict (column not stated, wrong column, or a value found in the claimed column). A table without a
header inherits the periods of the previous table of the same width on its page in the scorer, which the annotators did
not see, so periods are also compared on the items whose figure column has a header of its own.

1. Agreement among the annotators: Fleiss' kappa over all five, pairwise Cohen's kappa, unanimity, and each annotator's
   agreement with the majority of the other four.
2. Consensus (at least three of five) against the scorer's verdicts in agent_check/key/key.json, per question and per
   stratum (system x outcome: side), with exact 95% intervals; and, for the scorer's row-side errors, the share a reader
   could still place from the surrounding rows.
Writes agent_check/results/AGENT_CHECK.md and agent_check/results/summary.json.
usage: python tools/score_agent_check.py
"""
import itertools
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PAPER / "tools"))
from score_scorer_check import cp, kappa  # noqa: E402

ROW = ("same line", "duplicate line", "another line", "no label")
READER = ("yes", "no")
PERIOD = ("same period", "another period", "no period")
CLASSES = ("complete", "misplaced: row", "misplaced: period", "unresolved: row", "unresolved: period")
QUESTIONS = {"row": ROW, "reader": READER, "period": PERIOD, "class": CLASSES}
ALIASES = {"same": "same line", "duplicate": "duplicate line", "another": "another line", "different line": "another line",
           "nolabel": "no label", "none": "no label", "same year": "same period", "another year": "another period",
           "no header": "no period", "true": "yes", "false": "no"}


def norm(x, allowed):
    x = " ".join(str(x or "").strip().lower().replace("_", " ").split())
    x = ALIASES.get(x, x)
    return x if x in allowed else None


def klass(row, period):
    if row is None or period is None:
        return None
    if period == "no period":
        return "unresolved: period"
    if period == "another period":
        return "misplaced: period"
    if row == "no label":
        return "unresolved: row"
    if row == "another line":
        return "misplaced: row"
    return "complete"


def scorer_period(k):
    return {"column not stated": "no period", "wrong column": "another period"}.get(k["fact"], "same period")


def header_flags():
    """Items whose figure column has no header text in the packet (the scorer may have inherited one)."""
    import re
    txt = (PAPER / "agent_check" / "packet" / "packet.md").read_text(encoding="utf-8")
    flags = {}
    for blk in re.split(r"\n(?=## E\d{3}\n)", txt):
        m = re.match(r"## (E\d{3})", blk)
        if m:
            flags[m.group(1)] = "(header of the figure's column: «—»)" in blk
    return flags


def scorer_class(k):
    return "complete" if k["outcome"] == "complete" else f"{k['outcome']}: {'period' if k['side'] == 'column' else k['side']}"


def fleiss(table, cats):
    """table: per item, the list of labels from all raters (items with any missing label are skipped)."""
    rows = [t for t in table if all(x is not None for x in t)]
    if not rows:
        return float("nan"), 0
    n = len(rows[0])
    counts = [Counter(t) for t in rows]
    P = [(sum(c[j] ** 2 for j in cats) - n) / (n * (n - 1)) for c in counts]
    pj = [sum(c[j] for c in counts) / (len(rows) * n) for j in cats]
    pe = sum(p * p for p in pj)
    pbar = sum(P) / len(P)
    return ((pbar - pe) / (1 - pe) if pe < 1 else 1.0), len(rows)


def majority(labels, need=3):
    c = Counter(x for x in labels if x is not None)
    if not c:
        return None
    lab, m = c.most_common(1)[0]
    return lab if m >= need and list(c.values()).count(m) == 1 else None


def pct(a, b):
    return f"{100 * a / b:.1f}%" if b else "–"


def main():
    key = json.load(open(PAPER / "agent_check" / "key" / "key.json", encoding="utf-8"))
    items = sorted(key)
    ann, problems = {}, []
    for f in sorted((PAPER / "agent_check" / "returned").glob("annotator_*.json")):
        a = f.stem.split("_", 1)[1]
        try:
            data = json.load(open(f, encoding="utf-8"))
        except json.JSONDecodeError as e:
            problems.append(f"{f.name}: not valid JSON ({e})"); continue
        got = {}
        for e in data.get("items", []):
            it = e.get("item")
            if it not in key:
                problems.append(f"{a}: unknown item {it}"); continue
            r, rd, p = norm(e.get("row"), ROW), norm(e.get("reader"), READER), norm(e.get("period"), PERIOD)
            for q, raw, v in (("row", e.get("row"), r), ("reader", e.get("reader"), rd), ("period", e.get("period"), p)):
                if v is None:
                    problems.append(f"{a} {it}: {q} = {raw!r} not recognised")
            got[it] = dict(row=r, reader=rd, period=p, **{"class": klass(r, p)},
                           confidence=str(e.get("confidence") or "").strip().lower(), note=str(e.get("note") or "").strip())
        missing = [it for it in items if it not in got]
        if missing:
            problems.append(f"{a}: {len(missing)} items missing ({', '.join(missing[:5])}{'…' if len(missing) > 5 else ''})")
        ann[a] = got
    A = sorted(ann)
    val = lambda a, it, q: ann[a].get(it, {}).get(q)
    out = ["# Five AI test annotators against the fact scorer", "",
           "Written by `tools/score_agent_check.py`. Packet and sampling: `tools/make_agent_check.py`. The annotators are AI "
           "agents (models below); they saw what each system wrote and the ground-truth line and period, not the scorer's "
           "verdicts. This tests the scorer and the annotation protocol; it is not a human check.", "",
           f"Annotators: {', '.join(A)}. Items: {len(items)}."]
    models = {"A1": "Opus 5.5", "A2": "Opus 5.5 (second run)", "A3": "Sonnet 5.5", "A4": "Fable 5.1", "A5": "Haiku 4.5"}
    out += ["", "| Annotator | Model | Items answered | Low confidence |", "|---|---|---:|---:|"]
    for a in A:
        out.append(f"| {a} | {models.get(a, '?')} | {len(ann[a])} | {sum(1 for v in ann[a].values() if v['confidence'] == 'low')} |")
    if problems:
        out += ["", "Problems in the returned files:", ""] + [f"- {p}" for p in problems[:40]]
    summary = dict(annotators=A, items=len(items), agreement={}, scorer={})

    # ---------------------------------------------------------------- 1. agreement among the annotators
    out += ["", "## 1. Agreement among the annotators", "",
            "| Question | Fleiss' kappa (all) | Items | Unanimous | Mean pairwise agreement | Kappa A1–A2 (same model) | Mean kappa, cross-model pairs |",
            "|---|---:|---:|---:|---:|---:|---:|"]
    loo = defaultdict(dict)
    for q, cats in QUESTIONS.items():
        table = [[val(a, it, q) for a in A] for it in items]
        fk, n = fleiss(table, cats)
        full = [t for t in table if all(x is not None for x in t)]
        unan = sum(len(set(t)) == 1 for t in full)
        pairs = {}
        for a, b in itertools.combinations(A, 2):
            pr = [(val(a, it, q), val(b, it, q)) for it in items if val(a, it, q) is not None and val(b, it, q) is not None]
            pairs[(a, b)] = (sum(x == y for x, y in pr) / len(pr), kappa(pr)) if pr else (float("nan"), float("nan"))
        same = pairs.get(("A1", "A2"), (float("nan"),) * 2)[1]
        cross = [k for (a, b), (_, k) in pairs.items() if (a, b) != ("A1", "A2")]
        out.append(f"| {q} | {fk:.3f} | {n} | {pct(unan, len(full))} | {100 * sum(p for p, _ in pairs.values()) / len(pairs):.1f}% | "
                   f"{same:.3f} | {sum(cross) / len(cross):.3f} |")
        for a in A:
            others = [b for b in A if b != a]
            pr = [(val(a, it, q), majority([val(b, it, q) for b in others])) for it in items]
            pr = [(x, y) for x, y in pr if x is not None and y is not None]
            loo[a][q] = sum(x == y for x, y in pr) / len(pr) if pr else float("nan")
        summary["agreement"][q] = dict(fleiss=fk, n=n, unanimous=unan / len(full) if full else None,
                                       pairwise={f"{a}-{b}": dict(agreement=p, kappa=k) for (a, b), (p, k) in pairs.items()})
    out += ["", "Each annotator's agreement with the majority (at least three) of the other four:", "",
            "| Annotator | " + " | ".join(QUESTIONS) + " |", "|---|" + "---:|" * len(QUESTIONS)]
    for a in A:
        out.append(f"| {a} | " + " | ".join(f"{100 * loo[a][q]:.1f}%" for q in QUESTIONS) + " |")
    summary["leave_one_out"] = loo
    worst = min(A, key=lambda a: loo[a]["class"])
    rest = [a for a in A if a != worst]
    fk4, _ = fleiss([[val(a, it, "class") for a in rest] for it in items], CLASSES)
    out += ["", f"Fleiss' kappa for the class without the least consistent annotator ({worst}): {fk4:.3f}."]
    summary["agreement"]["class_without_" + worst] = fk4

    # ---------------------------------------------------------------- 2. consensus against the scorer
    cons = {it: {q: majority([val(a, it, q) for a in A]) for q in QUESTIONS} for it in items}
    nocons = [it for it in items if cons[it]["class"] is None]
    out += ["", "## 2. Consensus against the scorer", "",
            f"Consensus: the answer of at least three of the five annotators. No consensus on the class: {len(nocons)} items.", ""]
    conf = Counter((scorer_class(key[it]), cons[it]["class"]) for it in items if cons[it]["class"] is not None)
    out += ["Class (rows: scorer, columns: consensus):", "",
            "| Scorer \\ Consensus | " + " | ".join(CLASSES) + " | n | agree |", "|---|" + "---:|" * (len(CLASSES) + 2)]
    for s in CLASSES:
        tot = sum(conf[(s, c)] for c in CLASSES)
        if tot:
            out.append(f"| {s} | " + " | ".join(str(conf[(s, c)]) for c in CLASSES) + f" | {tot} | {pct(conf[(s, s)], tot)} |")
    agree = sum(conf[(s, s)] for s in CLASSES)
    ncls = sum(conf.values())
    out += ["", f"Agreement on the class: {agree} of {ncls} ({pct(agree, ncls)}); Cohen's kappa scorer vs consensus "
            f"{kappa([(scorer_class(key[it]), cons[it]['class']) for it in items if cons[it]['class'] is not None]):.3f}."]
    summary["scorer"]["class"] = dict(agree=agree, n=ncls, confusion={f"{a} | {b}": n for (a, b), n in conf.items()})

    nohead = header_flags()
    srow = {it: key[it]["scorer_row"] for it in items}
    sper = {it: scorer_period(key[it]) for it in items}
    for q, sv, cats, sel, title in (("row", srow, ROW, items, "Row"),
                                    ("period", sper, PERIOD, items, "Period, all items"),
                                    ("period", sper, PERIOD, [it for it in items if not nohead[it]],
                                     "Period, items whose figure column has a header of its own"),
                                    ("period", sper, PERIOD, [it for it in items if nohead[it]],
                                     "Period, items whose figure column has no header (the scorer may inherit one)")):
        cq = Counter((sv[it], cons[it][q]) for it in sel if cons[it][q] is not None)
        scats = sorted({sv[it] for it in sel}, key=lambda x: cats.index(x) if x in cats else 9)
        ok = sum(cq[(c, c)] for c in cats)
        n = sum(cq.values())
        out += ["", f"{title} (rows: scorer, columns: consensus; agreement {ok} of {n}, {pct(ok, n)}):", "",
                "| Scorer \\ Consensus | " + " | ".join(cats) + " | n |", "|---|" + "---:|" * (len(cats) + 1)]
        for s in scats:
            out.append(f"| {s} | " + " | ".join(str(cq[(s, c)]) for c in cats) + f" | {sum(cq[(s, c)] for c in cats)} |")
        summary["scorer"][title] = dict(agree=ok, n=n)

    out += ["", "### By stratum", "",
            "Confirmed: the consensus class equals the scorer's. For the scorer's row-side errors, *row problem confirmed* "
            "counts items whose consensus row answer is a row problem (no label or another line, whatever the period); "
            "*reader could place it* counts items whose consensus says a reader of the output would place the figure under the "
            "right line.", "",
            "| System | Scorer verdict | n | Confirmed (95% CI) | Row problem confirmed | Reader could place it | No consensus |",
            "|---|---|---:|---:|---:|---:|---:|"]
    strata = defaultdict(list)
    for it in items:
        strata[(key[it]["system"], scorer_class(key[it]))].append(it)
    pop = json.load(open(PAPER / "bench" / "common_subset_summary.json"))["systems"]
    weighted = defaultdict(lambda: [0.0, 0.0, 0.0])
    summary["scorer"]["strata"] = {}
    for (sysn, sc), its in sorted(strata.items(), key=lambda x: (x[0][1] != "unresolved: row", x[0][1], x[0][0])):
        dec = [it for it in its if cons[it]["class"] is not None]
        ok = sum(cons[it]["class"] == sc for it in dec)
        lo, hi = cp(ok, len(dec)) if dec else (float("nan"), float("nan"))
        rdec = [it for it in its if cons[it]["row"] is not None]
        rowside = sum(cons[it]["row"] in ("no label", "another line") for it in rdec)
        readers = [it for it in its if cons[it]["reader"] is not None]
        rd = sum(cons[it]["reader"] == "yes" for it in readers)
        is_row = sc in ("unresolved: row", "misplaced: row")
        out.append(f"| {sysn} | {sc} | {len(its)} | {ok}/{len(dec)} ({pct(ok, len(dec))}; {100 * lo:.0f}–{100 * hi:.0f}%) | "
                   f"{f'{rowside}/{len(rdec)}' if is_row else '–'} | {f'{rd}/{len(readers)}' if is_row else '–'} | {len(its) - len(dec)} |")
        summary["scorer"]["strata"][f"{sysn} | {sc}"] = dict(n=len(its), decided=len(dec), confirmed=ok, ci=[lo, hi],
                                                            row_problem=rowside, reader_yes=rd, reader_n=len(readers))
        if is_row and rdec:
            N = round(pop[sysn]["sides"][sc] * pop[sysn]["eligible"])
            w = weighted[sysn]
            w[0] += N; w[1] += N * rowside / len(rdec); w[2] += N * (rd / len(readers) if readers else 0)
    out += ["", "Row-side errors of each system on the common base, weighted by the size of its two row-side strata:", "",
            "| System | Row-side figures (scorer) | Share with a row problem (consensus) | Share a reader could place |",
            "|---|---:|---:|---:|"]
    for sysn, (N, r, rd) in weighted.items():
        out.append(f"| {sysn} | {N:.0f} | {pct(r, N)} | {pct(rd, N)} |")
    summary["scorer"]["row_side_weighted"] = {s: dict(n=N, row_problem=r / N, reader=rd / N) for s, (N, r, rd) in weighted.items()}

    out += ["", "## 3. Items without consensus or where the consensus differs from the scorer", "",
            "| Item | System | Scorer | Consensus | Votes (class) | Notes |", "|---|---|---|---|---|---|"]
    for it in items:
        sc, cc = scorer_class(key[it]), cons[it]["class"]
        if cc == sc:
            continue
        votes = Counter(val(a, it, "class") for a in A)
        notes = " / ".join(f"{a}: {ann[a][it]['note'][:90]}" for a in A if it in ann[a] and ann[a][it]["note"])
        out.append(f"| {it} | {key[it]['system'].split(',')[0]} | {sc} | {cc or 'none'} | "
                   + ", ".join(f"{k} {v}" for k, v in votes.most_common()) + f" | {notes.replace('|', '/')} |")
    res = PAPER / "agent_check" / "results"
    res.mkdir(parents=True, exist_ok=True)
    (res / "AGENT_CHECK.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    (res / "summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
