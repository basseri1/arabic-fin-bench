"""Score model outputs against the JSON ground truth, with the benchmark's own matching rules (eval2).

Outputs are <results>/<model>/<page>.md, where <page> is <filing_id>_p<NN> (legacy names such as aramco_p12 are
accepted through ALIASES). Row recall gets a 95% bootstrap interval, resampling whole filings.

usage: python score.py --results DIR [--gt paper/gt] [--split test] [--json out.json] [--boot 2000]
"""
import argparse
import csv
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gtlib  # noqa: E402

E = gtlib.eval2
ALIASES = {"aramco_FY2024": ["aramco"], "maaden_FY2024": ["maaden"], "arabian_drilling_FY2024": ["drilling"]}


def load_gt(gt_dirs, split=None):
    """gt_dirs: one directory or a comma-separated list; a filing found in several is taken from the first."""
    inv = {}
    p = gtlib.PAPER / "dataset_inventory.csv"
    if p.exists():
        inv = {r["filing_id"]: r for r in csv.DictReader(open(p, encoding="utf-8-sig"))}
    out = {}
    for gt_dir in str(gt_dirs).split(","):
        for f in sorted(Path(gt_dir).glob("*.json")):
            gt = gtlib.load(f)
            if gt["filing_id"] in out:
                continue
            label = (inv.get(gt["filing_id"], {}).get("proposed_split", "").split() or [""])[0].lower()
            if split and split.lower() != label:          # first word only: "Dev only (... keep out of test)" is dev
                continue
            out[gt["filing_id"]] = gt
    return out


def page_texts(mdir):
    pages = {}
    for p in mdir.glob("*.md"):
        raw = p.read_text(encoding="utf-8", errors="replace")
        txt, _ = E.truncate_loops("\n".join(E.lines_of(E.extract_text(raw))))
        pages[p.stem] = txt
    return pages


def pages_for(fid, pages):
    prefixes = [fid] + ALIASES.get(fid, [])
    return sorted(k for k in pages if any(k == pre or k.startswith(pre + "_p") for pre in prefixes))


def score_model(mdir, gts):
    pages = page_texts(mdir)
    total, per_stmt, per_filing = {}, [], {}
    for fid, gt in gts.items():
        mine = pages_for(fid, pages)
        if not mine:
            continue
        full = "\n".join(pages[p] for p in mine)
        tables = gtlib.to_eval_tables(gt)
        c = E.score_tables(tables, full)
        per_filing[fid] = c
        total = E.add(total, c)
        for st, tb in zip(gt["statements"], tables):
            sc = E.score_tables([tb], full)          # rows are matched independently, so these sum to the filing total
            per_stmt.append({"filing": fid, "statement": st["id"], "type": st["type"],
                             "rows_hit": sc["rows_hit"], "rows_tot": sc["rows_tot"]})
    return total, per_stmt, per_filing


def bootstrap(per_stmt, n=2000, seed=0):
    if not per_stmt:
        return float("nan"), float("nan")
    rng = random.Random(seed)
    vals = []
    for _ in range(n):
        s = [rng.choice(per_stmt) for _ in per_stmt]
        tot = sum(x["rows_tot"] for x in s)
        vals.append(sum(x["rows_hit"] for x in s) / tot if tot else float("nan"))
    vals.sort()
    return vals[int(0.025 * n)], vals[int(0.975 * n) - 1]


def bootstrap_filings(per_stmt, n=2000, seed=0):
    """95% interval for pooled row recall, resampling whole filings (a filing's statements share layout, print quality
    and often a failure, so they are not independent)."""
    if not per_stmt:
        return float("nan"), float("nan")
    by_f = {}
    for x in per_stmt:
        by_f.setdefault(x["filing"], []).append(x)
    groups = list(by_f.values())
    rng = random.Random(seed)
    vals = []
    for _ in range(n):
        s = [x for _ in groups for x in rng.choice(groups)]
        tot = sum(x["rows_tot"] for x in s)
        vals.append(sum(x["rows_hit"] for x in s) / tot if tot else float("nan"))
    vals.sort()
    return vals[int(0.025 * n)], vals[int(0.975 * n) - 1]


def metrics(c):
    return {"row_recall": E.pct(c["rows_hit"], c["rows_tot"]), "fig_recall": E.pct(c["fig_hit"], c["fig_tot"]),
            "fig_sgn": E.pct(c["sgn_hit"], c["fig_tot"]), "label_recall": E.pct(c["lab_hit"], c["lab_tot"]),
            "num_prec": E.pct(c["prec_hit"], c["prec_tot"]), "rows": c["rows_tot"], "figures": c["fig_tot"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True)
    ap.add_argument("--gt", default=f"{gtlib.PAPER / 'gt'},{gtlib.PAPER / 'drafts'}",
                    help="comma-separated GT dirs (default: verified gt/ first, then annotator drafts/)")
    ap.add_argument("--split", default=None, help="dev or test (from dataset_inventory.csv)")
    ap.add_argument("--json", default="")
    ap.add_argument("--boot", type=int, default=2000)
    a = ap.parse_args()
    gts = load_gt(a.gt, a.split)
    out = []
    for mdir in sorted(p for p in Path(a.results).iterdir() if p.is_dir()):
        total, per_stmt, per_filing = score_model(mdir, gts)
        if not total:
            continue
        m = metrics(total)
        m["row_ci95"] = bootstrap_filings(per_stmt, a.boot)
        m.update(model=mdir.name, filings=len(per_filing), statements=len(per_stmt))
        m["per_filing"] = {k: metrics(v) for k, v in per_filing.items()}
        out.append(m)
    f = lambda x: "  -  " if x != x else f"{x * 100:5.1f}%"
    print(f"{'model':34s} {'filings':>7s} {'rows':>5s} {'row':>7s} {'95% CI':>15s} {'fig':>7s} {'sign':>7s} {'label':>7s} {'prec':>7s}")
    for m in sorted(out, key=lambda m: -m["row_recall"]):
        lo, hi = m["row_ci95"]
        print(f"{m['model']:34s} {m['filings']:>7d} {m['rows']:>5d} {f(m['row_recall'])} {f(lo):>7s}–{f(hi).strip():<7s} "
              f"{f(m['fig_recall'])} {f(m['fig_sgn'])} {f(m['label_recall'])} {f(m['num_prec'])}")
    if a.json:
        Path(a.json).write_text(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
