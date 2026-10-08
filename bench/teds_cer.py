"""TEDS and label character error rate (CER) for every main configuration, on the test split and on all 32 filings.

TEDS (Zhong, ShafieiBavani and Jimeno Yepes, "Image-based table recognition: data, model, and evaluation", ECCV 2020):
1 - TED(T_gt, T_pred) / max(|T_gt|, |T_pred|), with tables as trees table > tr > td; inserting or deleting a node costs 1,
and renaming a td costs the normalized Levenshtein distance of the two cells' contents (TEDS) or nothing (TEDS-S, the
structure alone). Grids as in bench/structure_metrics.py: the ground truth has one row per ground-truth row (label |
notes | one cell per period); the prediction is every table the system wrote on the statement's pages, stacked, with its
cells normalized the same way (digits, signs and separators of figures; Arabic text by the benchmark's normalization) and
cells that span rows or columns expanded into the grid by the parser.
Adaptation, disclosed: the tree edit distance is computed under a row-to-row mapping (a row maps to a row, in order, or
is deleted or inserted with its cells), which bounds the exact distance from above, so the TEDS reported here is a lower
bound on the exact score; and each prediction is scored in both reading directions, keeping the better, as for GriTS.

Label CER: for every ground-truth row label of at least four characters that label recall finds (partial match of at
least 85 against the normalized output text of the filing's pages, as in tools/score.py), the Levenshtein distance
between the label and the best-matching window of that text, divided by the label's length; micro-averaged (total edits
over total characters). Label WER: the same in words (word-level Levenshtein distance over the label's words), on the
matched window widened to whole words. Labels that are not found are counted by label recall, not here.
Writes bench/TEDS_CER.md and bench/teds_cer_summary.json.   usage: python bench/teds_cer.py [--workers 8]
"""
import argparse
import json
import statistics
import sys
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein
from rapidfuzz.process import cdist

PAPER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PAPER / "tools")); sys.path.insert(0, str(PAPER / "bench")); sys.path.insert(0, str(PAPER / "bench" / "vm_scripts"))
import score  # noqa: E402
import analyze  # noqa: E402
import structure_metrics as SM  # noqa: E402

E = score.E
RESULTS = PAPER / "bench" / "results32"


def pred_rows(run, pages):
    """The system's table rows on these pages, normalized like the GriTS grids, without the padding to a common width."""
    out = []
    for r in SM.pred_grid(run, pages):
        while r and not r[-1]:
            r = r[:-1]
        out.append(r)
    return out


def ted_rows(G, P, content=True):
    """Tree edit distance between table > tr > td trees under a row-to-row mapping."""
    if content:
        gs = sorted({c for r in G for c in r}); ps = sorted({c for r in P for c in r})
        gi = {c: i for i, c in enumerate(gs)}; pi = {c: i for i, c in enumerate(ps)}
        M = cdist(gs, ps, scorer=Levenshtein.normalized_distance) if gs and ps else None
        sub = lambda a, b: 0.0 if a == b else float(M[gi[a], pi[b]])
    else:
        sub = lambda a, b: 0.0

    def cells(a, b):
        prev = list(range(len(b) + 1))
        for i, x in enumerate(a, 1):
            cur = [i] + [0] * len(b)
            for j, y in enumerate(b, 1):
                cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + sub(x, y))
            prev = cur
        return prev[-1]

    prev = [0.0] * (len(P) + 1)
    for j in range(1, len(P) + 1):
        prev[j] = prev[j - 1] + 1 + len(P[j - 1])
    for i in range(1, len(G) + 1):
        cur = [prev[0] + 1 + len(G[i - 1])] + [0.0] * len(P)
        for j in range(1, len(P) + 1):
            cur[j] = min(prev[j] + 1 + len(G[i - 1]), cur[j - 1] + 1 + len(P[j - 1]), prev[j - 1] + cells(G[i - 1], P[j - 1]))
        prev = cur
    return prev[-1]


def teds(G, P, content=True):
    n_g = 1 + len(G) + sum(map(len, G))
    best = 0.0
    for Q in (P, [list(reversed(r)) for r in P]):           # both reading directions of an Arabic table
        n_p = 1 + len(Q) + sum(map(len, Q))
        best = max(best, 1 - ted_rows(G, Q, content) / max(n_g, n_p))
    return best


def label_cer(tables, text):
    full = E.norm_ar("\n".join(E.lines_of(text)))
    edits = chars = found = total = wedits = words = 0
    for tb in tables:
        for r in tb["rows"]:
            lab = E.norm_ar(r["label"])
            if len(lab) < 4:
                continue
            total += 1
            al = fuzz.partial_ratio_alignment(lab, full)
            if al is None or al.score < 85:
                continue
            found += 1
            edits += Levenshtein.distance(lab, full[al.dest_start:al.dest_end]); chars += len(lab)
            a, b = al.dest_start, al.dest_end                 # WER: the same window, widened to whole words
            while a > 0 and not full[a - 1].isspace():
                a -= 1
            while b < len(full) and not full[b].isspace():
                b += 1
            wedits += Levenshtein.distance(lab.split(), full[a:b].split()); words += len(lab.split())
    return edits, chars, found, total, wedits, words


def run_system(args):
    cfg, system, setting = args
    run = SM.SEED0.get(cfg, cfg)
    gts = score.load_gt(str(PAPER / "gt"))
    texts = score.page_texts(RESULTS / run)
    rows = []
    for fid, gt in gts.items():
        tables = score.gtlib.to_eval_tables(gt)
        full = "\n".join(texts[p] for p in score.pages_for(fid, texts))
        e, c, f, t, we, w = label_cer(tables, full)
        for st in gt["statements"]:
            pages = [f"{fid}_p{p:02d}" for p in st["pages"]]
            G, P = SM.gt_grid(st), pred_rows(run, pages)
            rows.append(dict(filing=fid, statement=st["id"], teds=teds(G, P, True), teds_s=teds(G, P, False)))
        rows.append(dict(filing=fid, statement=None, cer_edits=e, cer_chars=c, labels_found=f, labels_total=t, wer_edits=we, wer_words=w))
    return cfg, system, setting, rows


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    systems = [(cfg, v[0], v[2]) for cfg, v in analyze.CONFIGS.items() if v[3] == "main" and analyze.complete(RESULTS / SM.SEED0.get(cfg, cfg))]
    with Pool(a.workers) as pool:
        res = pool.map(run_system, systems)
    inv = {r["filing_id"]: r for r in __import__("csv").DictReader(open(PAPER / "dataset_inventory.csv", encoding="utf-8-sig"))}
    split = {f: r["proposed_split"].split()[0].lower() for f, r in inv.items()}
    rr = json.loads((PAPER / "bench" / "results_summary.json").read_text())["tables"]
    rowrec = {sp: {r["config"]: r["row"] for r in rr[sp]} for sp in ("test", "all")}
    summary = []
    for cfg, system, setting, rows in res:
        rec = dict(config=cfg, system=system, setting=setting)
        for sp in ("test", "all"):
            st = [r for r in rows if r["statement"] and (sp == "all" or split[r["filing"]] == sp)]
            fl = [r for r in rows if r["statement"] is None and (sp == "all" or split[r["filing"]] == sp)]
            ch = sum(r["cer_chars"] for r in fl); wd = sum(r["wer_words"] for r in fl)
            rec[sp] = dict(teds=statistics.mean(r["teds"] for r in st), teds_s=statistics.mean(r["teds_s"] for r in st),
                           label_cer=sum(r["cer_edits"] for r in fl) / ch if ch else None,
                           label_wer=sum(r["wer_edits"] for r in fl) / wd if wd else None,
                           labels_found=sum(r["labels_found"] for r in fl), labels_total=sum(r["labels_total"] for r in fl),
                           row_recall=rowrec[sp].get(cfg))
        summary.append(rec)
    from scipy.stats import kendalltau, spearmanr
    corr = {}
    for sp in ("test", "all"):
        xs = [r[sp]["row_recall"] for r in summary]
        corr[sp] = {k: dict(spearman=spearmanr(xs, [r[sp][k] for r in summary]).statistic,
                            kendall=kendalltau(xs, [r[sp][k] for r in summary]).statistic) for k in ("teds", "teds_s")}
    name = lambda r: r["system"] + (" (pipeline)" if "adopted" in r["setting"] else " (out of the box)" if "out of the box" in r["setting"]
                                    else " (self-hosted)" if r["system"] == "Qwen3.8-27B" and "BF16" in r["setting"] else " (API)" if r["system"] == "Qwen3.8-27B" else "")
    pct = lambda x: "–" if x is None else f"{100 * x:.1f}"
    out = ["# TEDS and label character error rate", "", "Method in the header of `bench/teds_cer.py`. dots.mocr is shown for seed 0.", "",
           "| System | Row recall (test) | TEDS (test) | TEDS-S (test) | Label CER, found labels (test) | Label WER (test) | Labels found (test) | TEDS (32) | TEDS-S (32) | Label CER (32) | Label WER (32) |",
           "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in sorted(summary, key=lambda r: -(r["test"]["row_recall"] or 0)):
        te, al = r["test"], r["all"]
        out.append(f"| {name(r)} | {pct(te['row_recall'])}% | {pct(te['teds'])} | {pct(te['teds_s'])} | {pct(te['label_cer'])}% | "
                   f"{pct(te['label_wer'])}% | {te['labels_found']} of {te['labels_total']} | {pct(al['teds'])} | {pct(al['teds_s'])} | "
                   f"{pct(al['label_cer'])}% | {pct(al['label_wer'])}% |")
    out += ["", f"Rank agreement with row recall across the {len(summary)} configurations — " +
            "; ".join(f"{sp}: TEDS ρ = {c['teds']['spearman']:.2f}, τ = {c['teds']['kendall']:.2f}; TEDS-S ρ = {c['teds_s']['spearman']:.2f}, "
                      f"τ = {c['teds_s']['kendall']:.2f}" for sp, c in corr.items()) + ".", ""]
    (PAPER / "bench" / "TEDS_CER.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    json.dump(dict(summary=summary, correlation=corr, per_statement={cfg: rows for cfg, _, _, rows in res}),
              open(PAPER / "bench" / "teds_cer_summary.json", "w"), ensure_ascii=False, indent=1)
    print("\n".join(out))


if __name__ == "__main__":
    main()
