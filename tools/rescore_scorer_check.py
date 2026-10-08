"""Re-score the human check of the fact scorer with the current scorer (bench/rq2_strict.py).

The check (scorer_check/key/key.json) recorded the scorer's verdict when the items were drawn. When the scorer changes,
as with the rule that a line printed without a label is stated by an output row without a label (2026-10-03), this
re-runs the scorer on each checked figure and writes the current verdict to scorer_check/key/rescored.json, leaving the
key unchanged. Each item is found again by its page, value and row label (the column header can change with the
parser: the HTML parser now honours rowspan, 2026-10-03); when an output repeats the same row, the figure with the same
header, then the same earlier verdict, is taken. `header_now` is the header as the current parser reads it. `unlabeled_line` marks items whose figure the
scorer now credits to a line printed without a label: tools/score_scorer_check.py then reads the checker's "no label"
for such an item as the right row, applying the same rule on both sides.
usage: python tools/rescore_scorer_check.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PAPER / "bench"))
import common_subset as CS  # noqa: E402
import rq2_strict as R  # noqa: E402

RUNS = {"Cohere Parse": CS.SYSTEMS["Cohere Parse"], "Mistral OCR": CS.SYSTEMS["Mistral OCR"],
        "dots.mocr": R.MAIN["dots.mocr pipeline, seed 0"][0], "Chandra OCR 2": R.MAIN["Chandra OCR 2, own input size"][0]}
GROUP = {"correct": "complete", "duplicate": "complete", "wrong row": "wrong context", "wrong column": "wrong context",
         "sign": "wrong context", "correct, row not stated": "unresolved", "column not stated": "unresolved",
         "correct, column not assessed": "unresolved"}


def main():
    key = json.load(open(PAPER / "scorer_check" / "key" / "key.json"))
    S = json.load(open(PAPER / "bench" / "rq2_strict_summary.json"))
    tr, tc = S["thresholds"]["row"], S["thresholds"]["col"]
    second = R.MAIN["dots.mocr pipeline, seed 0"][0]
    by = {}
    for it, k in key.items():
        by.setdefault((k["system"], k["filing"]), []).append(it)
    out, changes, cache = {}, Counter(), {}
    for (sysn, fid), its in sorted(by.items()):
        gt = json.load(open(PAPER / "gt" / f"{fid}.json"))
        res = R.analyse(RUNS[sysn], second, second, None, {fid: gt}, tr, tc, cache)
        for it in its:
            k = key[it]
            same = [c for c in res["cells"] if c["page"] == k["page"] and abs(c["value"] - abs(k["value"])) <= R.TOL
                    and c["label"] == k["label"]]
            assert same, it
            old = k["scorer"]["fact"]
            same.sort(key=lambda c: (c["header"] != k["header"], c["fact"] != old))   # same header first (it can change
            pick = next((c for c in same if c["fact"] == old), None) or \
                next((c for c in same if c.get("row_status") == "unlabeled line"), same[0])  # with the parser)
            new = pick["fact"]
            group = k["group"] if new == old else GROUP[new]
            out[it] = dict(fact=new, group=group, unlabeled_line=pick.get("row_status") == "unlabeled line",
                           header_changed=pick["header"] != k["header"], header_now=pick["header"])
            if new != old:
                changes[(old, new)] += 1
    (PAPER / "scorer_check" / "key" / "rescored.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{len(out)} items re-scored; changed verdicts: {dict(changes)}; on lines printed without a label: "
          f"{sum(v['unlabeled_line'] for v in out.values())}")


if __name__ == "__main__":
    main()
