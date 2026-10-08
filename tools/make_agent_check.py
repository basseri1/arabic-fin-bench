"""Packet for five AI test annotators: a blind check of the fact scorer on the cells where it fails most often.

On the common base of Table 10 (test split, statements whose columns are periods), the scorer's unresolved and misplaced
figures fall almost all on the row side. This draws a stratified sample of them, with period-side cases and complete
facts as controls, and writes for each figure what the system wrote (the header rows of its table and the rows around
the figure, exactly as written) beside the ground-truth line and period. The annotators judge the row and the period
separately and do not see the scorer's verdicts; tools/score_agent_check.py compares them with each other and with the
scorer. The annotators are AI agents, so this tests the scorer and the annotation protocol; it is not a human check.

Strata are (system, outcome, side), sampled without replacement with at most PER_FILING figures per filing in a stratum.
Writes agent_check/packet/packet.md (no verdicts), agent_check/key/key.json (the scorer's verdicts) and
agent_check/key/population.json (the row status of every unresolved row-side figure).   usage: python tools/make_agent_check.py
"""
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PAPER / "bench"))
import common_subset as CS  # noqa: E402
import rq2_strict as R  # noqa: E402

SEED = 20261003
PER_FILING = 3
ABOVE, BELOW, HEAD = 3, 3, 4                   # output rows shown above and below the figure; header rows shown
STRATA = [                                     # (system, outcome, side, n): the largest error cells, then controls
    ("dots.mocr pipeline, seed 0", "unresolved", "row", 25),
    ("Chandra OCR 2, own input size", "misplaced", "row", 20),
    ("Chandra OCR 2, own input size", "unresolved", "row", 15),
    ("Mistral OCR", "misplaced", "row", 15),
    ("Mistral OCR", "unresolved", "row", 10),
    ("Cohere Parse", "unresolved", "row", 5),
    ("Chandra OCR 2, own input size", "unresolved", "column", 8),
    ("Mistral OCR", "unresolved", "column", 3),
    ("Mistral OCR", "misplaced", "column", 2),
    ("Cohere Parse", "misplaced", "column", 2),
    ("Cohere Parse", "complete", None, 4),
    ("Mistral OCR", "complete", None, 4),
    ("dots.mocr pipeline, seed 0", "complete", None, 4),
    ("Chandra OCR 2, own input size", "complete", None, 3),
]
SYSTEMS = sorted({s for s, *_ in STRATA})
TYPES = {"financial_position": "statement of financial position", "profit_loss": "statement of profit or loss",
         "comprehensive_income": "statement of comprehensive income", "cash_flows": "statement of cash flows",
         "changes_in_equity": "statement of changes in equity"}

INSTRUCTIONS = """# Placement check: test annotation of {n} figures

You are one of five independent annotators. Each item below is one figure that a document-reading system wrote into a
table when it read a page of an Arabic financial statement. Your task is to say whether the system put the figure under
the right line item (row) and the right period (column). Each item gives you:

- **Output**: what the system wrote, exactly. First the header rows of its table, then the rows around the figure.
  Cells are separated by ` | `; the row holding the figure is marked `►` and the figure itself `⟦like this⟧`.
  `(header of the figure's column)` repeats the header cells above the figure, joined.
- **Ground truth**: the printed line (line item) and the period under which this figure is printed in the filing, with
  the line's section and the printed lines just above and below it, and any other printed lines in the filing that carry
  the same value.

The figure's value is right in every item; judge only where it was put. Answer four questions per item:

1. `row`: does the label of the system's row holding the figure (the `►` row) name the ground-truth line?
   - `same line`: it names that line. Spelling differences, a missing or extra word, a note number, Western or
     Arabic-Indic digits, or OCR noise do not matter if a reader would identify the line unambiguously.
   - `duplicate line`: it names another line that the ground truth lists as carrying the same value in the same
     period, so the figure is also right where it is.
   - `another line`: it names a different line, including the line just above or below (labels shifted by one row).
   - `no label`: the row has no label, or its label is too fragmentary or generic to identify any line (only a note
     number, or a bare "total" where several totals exist).
   Judge the `►` row's own label here. A label on a separate row above does not count for this question.
2. `reader`: from the system's output alone, would a careful reader place this figure under the ground-truth line?
   `yes` if the `►` row's label names it, or if a label-only row directly above (a row with no figures of its own)
   clearly carries the rest or the whole of this row's label, as when a long label wraps onto two rows; otherwise `no`.
3. `period`: does the header of the figure's column name the ground-truth period?
   - `same period`: it names that period. The year is enough when the statement's columns differ by year; when they
     differ by span (three, six or nine months) or by date within a year, the header must name the right one. If the
     header cells are shifted against the data columns (a year row with one cell too few) but a reader can assign the
     years to the columns holding figures in order, judge by that assignment.
   - `another period`: it names a different period.
   - `no period`: the header names no period (it is empty, or gives only a currency, a unit or a note number).
4. `confidence`: `high`, `medium` or `low`.

Add a short `note` when you answer `another line` (name the line the label names, as printed) or when the item is
unclear; otherwise leave it empty.

Rules: judge every item yourself, by reading it. Do not write code to decide, do not open any other file in the
repository, do not run scripts, and do not look at other annotators' answers. Write your answers as one UTF-8 JSON file:

```json
{{"annotator": "<your id>", "items": [
  {{"item": "E001", "row": "same line", "reader": "yes", "period": "same period", "confidence": "high", "note": ""}},
  ...
]}}
```

with one entry for each of the {n} items, in order, using exactly the answer strings above.

"""


def cell_text(x):
    return " ".join(str(x or "").split())


def raw_row(d, ri, mark=None):
    cells = [cell_text(x) for x in d["grid"][ri]]
    if mark is not None:
        cells[mark] = f"⟦{cells[mark]}⟧"
    while cells and not cells[-1]:
        cells.pop()
    return " | ".join(cells) if cells else "(empty row)"


def gt_lines(st):
    """Ground-truth rows of a statement in order, each with its nearest section heading."""
    out, section = [], ""
    for r in st["rows"]:
        if r.get("kind") == "section":
            section = r.get("label_ar", "")
            continue
        out.append(dict(id=r["id"], label=r.get("label_ar", ""), section=section))
    return out


def period_text(col):
    return f"«{col.get('label', '')}» (period ending {col.get('period', '?')})"


def scorer_view(k, cell):
    """The scorer's row and period status for this ground-truth cell, from the figure it attributed to it."""
    rk = tuple(cell.get("row_key") or ())
    row = "same line" if rk and rk[:2] == tuple(k[:2]) else "another line" if rk else "no label"
    claimed = {tuple(x) for x in (cell.get("claimed") or [])}
    period = "same period" if (k[0], k[2]) in claimed else "another period" if claimed else "no period"
    return row, period


def main():
    S = json.load(open(PAPER / "bench" / "rq2_strict_summary.json"))
    tr, tc = S["thresholds"]["row"], S["thresholds"]["col"]
    test = R.score.load_gt(str(PAPER / "gt"), "test")
    second = R.MAIN["dots.mocr pipeline, seed 0"][0]
    summary = json.load(open(PAPER / "bench" / "common_subset_summary.json"))["systems"]
    cache, recs, population = {}, {}, {}
    for name in SYSTEMS:
        run = CS.SYSTEMS[name]
        res = R.analyse(run, second, second, None, test, tr, tc, cache)
        assign = []
        o, _ = CS.outcomes(res, test, assign)
        for key in ("complete", "unresolved", "misplaced"):          # the records reproduce Table 10
            assert o[key] == summary[name]["counts"][key], (name, key)
        for a in assign:
            a["run"] = run
        recs[name] = assign
        population[name] = dict(Counter(a["cell"].get("row_status") for a in assign
                                        if a["outcome"] == "unresolved" and a["side"] == "row"))
        print(name, len(assign), "records; unresolved row by row status:", population[name], flush=True)

    rng = random.Random(SEED)
    picked = []
    for name, outcome, side, n in STRATA:
        pool = [a for a in recs[name] if a["outcome"] == outcome and a["side"] == side]
        rng.shuffle(pool)
        per, take = Counter(), []
        for cap in (PER_FILING, 10 ** 6):                             # relax the cap only if the stratum is too small
            for a in pool:
                if len(take) == n:
                    break
                if a not in take and per[a["filing"]] < cap:
                    take.append(a); per[a["filing"]] += 1
        assert len(take) == n, (name, outcome, side, len(pool))
        picked += [(name, a) for a in take]
    rng.shuffle(picked)                                                # interleave the strata

    gts = {fid: test[fid] for fid in test}
    lines, key = [INSTRUCTIONS.format(n=len(picked))], {}
    for idx, (name, a) in enumerate(picked, 1):
        item = f"E{idx:03d}"
        fid, k, c = a["filing"], a["k"], a["cell"]
        gt = gts[fid]
        si, rid, cid = k
        st = gt["statements"][si]
        gl = gt_lines(st)
        pos = next(i for i, r in enumerate(gl) if r["id"] == rid)
        col = next(x for x in st["columns"] if x["id"] == cid)
        sts, gtc = R.gt_index(gt)
        value = gtc[k]
        same = []
        for (s2, r2, c2), v2 in gtc.items():
            if (s2, r2, c2) != k and v2 is not None and abs(v2 - value) <= R.TOL:
                st2 = gt["statements"][s2]
                lab = next((r.get("label_ar", "") for r in st2["rows"] if r["id"] == r2), "")
                col2 = next(x for x in st2["columns"] if x["id"] == c2)
                where = "same statement" if s2 == si else TYPES.get(st2["type"], st2["type"])
                same.append(f"«{lab}», {period_text(col2)} [{where}]")
        d = cache[(a["run"], fid)][c["doc"]]
        ri, j = d["raw"][c["i"]], d["cols"][c["c"]]
        first = d["first"]
        out_page = R.page_no(c["page"])
        page_st = [x for x in gt["statements"] if out_page in x.get("pages", [])]
        L = [f"## {item}", "",
             f"Statement: {TYPES.get(st['type'], st['type'])}, «{st.get('title_ar', '')}» (filing {fid}, "
             f"printed on page {', '.join(map(str, st.get('pages', [])))}; the output table is from page {out_page}"
             + ("" if any(x["id"] == st["id"] for x in page_st) else
                f", which holds {', '.join(TYPES.get(x['type'], x['type']) for x in page_st) or 'no transcribed statement'}") + ")",
             "", "Output:", "```"]
        for r in range(max(0, first - HEAD), first):
            L.append("  header: " + raw_row(d, r))
        if first == 0:
            L.append("  header: (none: the table starts with figures)")
        lo, hi = max(first, ri - ABOVE), min(len(d["grid"]), ri + BELOW + 1)
        if lo > first:
            L.append(f"  … ({lo - first} rows not shown)")
        for r in range(lo, hi):
            L.append(("► " if r == ri else "  ") + raw_row(d, r, j if r == ri else None))
        if hi < len(d["grid"]):
            L.append(f"  … ({len(d['grid']) - hi} rows not shown)")
        L += ["```", f"(header of the figure's column: «{cell_text(d['header'][c['c']]) or '—'}»)", "",
              "Ground truth:",
              f"- line: «{gl[pos]['label']}»" + (f" (section «{gl[pos]['section']}»)" if gl[pos]["section"] else ""),
              f"- printed line above: «{gl[pos - 1]['label']}»" if pos > 0 else "- printed line above: (none; first line)",
              f"- printed line below: «{gl[pos + 1]['label']}»" if pos + 1 < len(gl) else "- printed line below: (none; last line)",
              f"- period: {period_text(col)}; the statement's columns: " + "; ".join(period_text(x) for x in st["columns"]),
              "- same value elsewhere in the filing: " + ("; ".join(same[:4]) + (f"; and {len(same) - 4} more" if len(same) > 4 else "")
                                                          if same else "none"), ""]
        lines += L
        srow, sper = scorer_view(k, c)
        key[item] = dict(system=name, outcome=a["outcome"], side=a["side"], filing=fid, k=list(k), value=value,
                         fact=c["fact"], row_status=c.get("row_status"), scorer_row=srow, scorer_period=sper,
                         stype=st["type"], page=c["page"], cross_page=not any(x["id"] == st["id"] for x in page_st),
                         duplicates=len(same))
    for sub in ("packet", "key", "returned", "results"):
        (PAPER / "agent_check" / sub).mkdir(parents=True, exist_ok=True)
    (PAPER / "agent_check" / "packet" / "packet.md").write_text("\n".join(lines), encoding="utf-8")
    (PAPER / "agent_check" / "key" / "key.json").write_text(json.dumps(key, ensure_ascii=False, indent=1), encoding="utf-8")
    (PAPER / "agent_check" / "key" / "population.json").write_text(json.dumps(population, indent=1), encoding="utf-8")
    print(f"wrote {len(key)} items;", Counter((v["system"], v["outcome"], v["side"]) for v in key.values()))
    print("cross-page items:", sum(v["cross_page"] for v in key.values()), "| with duplicates:", sum(v["duplicates"] > 0 for v in key.values()))


if __name__ == "__main__":
    main()
