"""Facts on a common assessable subset: every system scored against the same ground-truth cells.

The fact-level shares in RQ2_STRICT.md are shares of each system's own emitted figures, so systems that emit different
figures, or whose figures fall in equity matrices (where columns are not assessed), are not compared on the same base.
Here eligibility is fixed from the source and the ground truth alone, before any output is read:

  eligible = in-scope ground-truth figures (the RQ2 figure filter) in statements whose columns are reporting periods,
             on the held-out test split. Equity matrices are excluded for every system, because the scorer does not
             resolve their component columns.

Every eligible cell then gets one outcome per system, one to one:
  complete    an emitted figure states this cell's row and period and has its signed value (as in rq2_strict);
  unresolved  the value is emitted but the output states no row label or no period that can be matched;
  misplaced   the value is emitted under another row or period;
  sign / misread / omitted   the value is emitted with the wrong sign, or not emitted at all (a misread figure and
              an omitted one look the same from the cell's side).
Omissions and unresolved cases stay in the denominator: an unresolved case is not counted as correct.
Emitted figures are attributed to cells by value, one to one within a filing, preferring the statement the output's
row resolves to, then the statement on the figure's page.

Component accuracies, as FinCriticalED reports accuracy per fact type: on the same eligible cells, value accuracy (the
signed value is emitted), line-item accuracy (emitted under the right row), period accuracy (emitted under the right
period) and fact accuracy (all three, = complete). Statement level, as its page-level critical errors: a statement is
fully right when every eligible figure is a complete fact, and has a critical error when at least one figure is
misplaced, has the wrong sign, or is misread or omitted (unresolved figures alone are not critical errors).

Writes bench/COMMON_SUBSET.md and bench/common_subset_summary.json.   usage: python bench/common_subset.py
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PAPER / "bench"))
import rq2_strict as R  # noqa: E402

C = R.C
SYSTEMS = {"Cohere Parse": "cohere_parse_plain", "Mistral OCR": "mistral_ocr_plain", "LandingAI ADE": "landingai_ade_plain",
           "dots.mocr pipeline, seed 0": R.MAIN["dots.mocr pipeline, seed 0"][0],
           "dots.mocr pipeline, seed 1": R.MAIN["dots.mocr pipeline, seed 1"][0],
           "dots.mocr pipeline, seed 2": R.MAIN["dots.mocr pipeline, seed 2"][0],
           "Chandra OCR 2, own input size": R.MAIN["Chandra OCR 2, own input size"][0]}
UNRESOLVED = {"correct, row not stated", "column not stated", "correct, column not assessed"}


def side_of(k, c):
    """Which part of the context fails for an unresolved or misplaced cell: 'row' (line item) or 'column' (period).
    Unresolved: the output states no row label (row) or no matchable period (column). Misplaced: the figure is placed
    under another row (row, also when the column is wrong too) or only under another period (column)."""
    f = c["fact"]
    if f == "correct, row not stated" or f == "wrong row":
        return "row"
    if f in ("column not stated", "correct, column not assessed", "wrong column"):
        return "column"
    ctx = tuple(c.get("ctx") or ())                         # credited to another cell: compare that cell with this one
    return "row" if len(ctx) >= 2 and tuple(ctx[:2]) != tuple(k[:2]) else "column"
MISPLACED = {"wrong row", "wrong column", "duplicate", "correct"}       # correct/duplicate here: credited to another cell


def eligible_cells(gt):
    sts, gtc = R.gt_index(gt)
    cells = {k: v for k, v in gtc.items() if v is not None and C.is_figure(v) and sts[k[0]]["periodic"]}
    return sts, gtc, cells


def outcomes(res, gts, assign=None):
    """Outcome counts per filing; with a list as `assign`, also one record per eligible cell (tools/make_agent_check.py)."""
    by_f = defaultdict(list)
    for c in res["cells"]:
        by_f[c["filing"]].append(c)
    out = Counter()
    per_filing = {}
    for fid, gt in gts.items():
        sts, gtc, elig = eligible_cells(gt)
        emitted = by_f.get(fid, [])
        credited = {c["ctx"]: c for c in emitted if c["fact"] == "correct"}
        used = {id(c) for c in emitted if c["fact"] == "correct"}
        res_f = Counter()
        rest = []
        stmt = defaultdict(list)                               # (statement) -> outcomes of its eligible cells

        def comp(k, c, value_ok):
            si, rid, cid = k
            item = value_ok and tuple(c.get("row_key") or ()) == (si, rid)
            period = value_ok and (si, cid) in {tuple(x) for x in (c.get("claimed") or [])}
            res_f["value"] += value_ok; res_f["item"] += item; res_f["period"] += period

        for k in elig:
            if k in credited:
                res_f["complete"] += 1
                comp(k, credited[k], True)
                if assign is not None:
                    assign.append(dict(filing=fid, k=k, outcome="complete", side=None, cell=credited[k]))
                stmt[k[0]].append("complete")
            else:
                rest.append(k)

        def page_sts(c):
            return {st["i"] for st in sts if R.page_no(c["page"]) in st["pages"]}

        def pick(k, pool):
            si = k[0]
            ranked = sorted(pool, key=lambda c: (0 if (c.get("row_key") or (None,))[0] == si else 1 if si in page_sts(c) else 2))
            return ranked[0] if ranked else None

        for k in rest:
            v = elig[k]
            same = [c for c in emitted if id(c) not in used and abs(c["signed"] - v) <= R.TOL]
            c = pick(k, same)
            if c is not None:
                used.add(id(c))
                o = "unresolved" if c["fact"] in UNRESOLVED else "misplaced" if c["fact"] in MISPLACED else "other"
                res_f[o] += 1
                res_f[f"{o}: {side_of(k, c)}"] += 1                  # row side (line item) or column side (period)
                if assign is not None:
                    assign.append(dict(filing=fid, k=k, outcome=o, side=side_of(k, c), cell=c))
                comp(k, c, True)
                stmt[k[0]].append(o)
                continue
            opp = [c for c in emitted if id(c) not in used and abs(abs(c["signed"]) - abs(v)) <= R.TOL]
            c = pick(k, opp)
            if c is not None:
                used.add(id(c)); res_f["sign"] += 1; stmt[k[0]].append("sign")
            else:
                res_f["misread or omitted"] += 1; stmt[k[0]].append("misread or omitted")
        for si, os_ in stmt.items():
            res_f["statements"] += 1
            res_f["statements fully right"] += all(o == "complete" for o in os_)
            res_f["statements with a critical error"] += any(o in ("misplaced", "other", "sign", "misread or omitted") for o in os_)
        res_f["eligible"] = len(elig)
        res_f["in_scope_all"] = sum(1 for kk, vv in gtc.items() if vv is not None and C.is_figure(vv))
        per_filing[fid] = dict(res_f)
        out.update(res_f)
    return out, per_filing


def main():
    S = json.load(open(PAPER / "bench" / "rq2_strict_summary.json"))
    tr, tc = S["thresholds"]["row"], S["thresholds"]["col"]
    test = R.score.load_gt(str(PAPER / "gt"), "test")
    cache, summary = {}, {"eligibility": "in-scope ground-truth figures in statements whose columns are periods (test split)",
                          "systems": {}}
    second = R.MAIN["dots.mocr pipeline, seed 0"][0]
    for name, run in SYSTEMS.items():
        res = R.analyse(run, second, second, None, test, tr, tc, cache)
        o, pf = outcomes(res, test)
        n = o["eligible"]
        rec_all = len({(c["filing"], c["ctx"]) for c in res["cells"] if c["fact"] == "correct"}) / res["gt_scope"]
        ns = o["statements"]
        summary["systems"][name] = dict(eligible=n, in_scope_all=o["in_scope_all"], counts={k: o[k] for k in
                                        ("complete", "unresolved", "misplaced", "sign", "misread or omitted", "other")},
                                        shares={k: o[k] / n for k in ("complete", "unresolved", "misplaced", "sign", "misread or omitted", "other")},
                                        sides={k: o[k] / n for k in ("unresolved: row", "unresolved: column", "misplaced: row", "misplaced: column")},
                                        accuracy=dict(value=o["value"] / n, line_item=o["item"] / n, period=o["period"] / n, fact=o["complete"] / n),
                                        statements=dict(n=ns, fully_right=o["statements fully right"] / ns,
                                                        critical_error=o["statements with a critical error"] / ns),
                                        recovered_all=rec_all, per_filing=pf)
        print(name, {k: f"{100 * v:.1f}" for k, v in summary["systems"][name]["shares"].items()}, f"all {100 * rec_all:.1f}", flush=True)
    any_sys = next(iter(summary["systems"].values()))
    summary["eligible"], summary["in_scope_all"] = any_sys["eligible"], any_sys["in_scope_all"]
    (PAPER / "bench" / "common_subset_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    pct = lambda x: f"{100 * x:.1f}%"
    md = ["# Facts on a common assessable subset", "", "Method: header of `bench/common_subset.py`.", "",
          f"Eligible: {summary['eligible']:,} of the {summary['in_scope_all']:,} in-scope ground-truth figures of the test split "
          "(statements whose columns are periods; equity matrices excluded for every system). Each eligible cell has one outcome "
          "per system; the shares below have the same denominator for every system.", "",
          "| System | Value accuracy | Line-item accuracy | Period accuracy | Fact accuracy (complete) | Unresolved | Misplaced | Wrong sign | Misread or omitted | Statements fully right | Statements with a critical error | Recovered as complete facts, all in-scope figures |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for name, x in summary["systems"].items():
        s, acc, st = x["shares"], x["accuracy"], x["statements"]
        md.append(f"| {name} | {pct(acc['value'])} | {pct(acc['line_item'])} | {pct(acc['period'])} | {pct(acc['fact'])} | "
                  f"{pct(s['unresolved'])} | {pct(s['misplaced'] + s['other'])} | {pct(s['sign'])} | {pct(s['misread or omitted'])} | "
                  f"{pct(st['fully_right'])} | {pct(st['critical_error'])} | {pct(x['recovered_all'])} |")
    md += ["", f"Statements with eligible figures: {next(iter(summary['systems'].values()))['statements']['n']}."]
    (PAPER / "bench" / "COMMON_SUBSET.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
