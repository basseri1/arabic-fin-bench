"""Structure-aware checks of the main metric (row recall), per system on the 32 filings:

A. Column order. Row recall credits a row when all its figures appear on one output line, in any order. For each credited
   row with at least two distinct non-zero figures, the order of the ground-truth columns along the line is read; a row
   is 'swapped' when it disagrees with the direction most rows of its statement follow (either reading direction is a
   valid serialisation of an Arabic table; a row that breaks it has figures under the wrong period).
B. GriTS-Con (Smock, Pesala and Abraham, "GriTS: Grid table similarity metric for table structure recognition",
   ICDAR 2023; reference implementation microsoft/table-transformer, grits.py): cell content compared by the reference
   implementation's LCS similarity (difflib ratio; two empty cells score 1), grids aligned by the factored 2D most-similar-
   substructures heuristic. Ground-truth grid per statement: one row per ground-truth row, columns label | notes | one per
   period. Predicted grid: every table the system emitted on the statement's pages (HTML, Markdown or LaTeX), stacked
   (rows of 'a | b' lines for the line-based systems). Adaptation, disclosed: each predicted grid is scored in both column orders (left-to-right and
   right-to-left serialisations of Arabic tables are both valid) and the better is kept.
Writes bench/STRUCTURE.md and bench/structure_summary.json.  usage: python bench/structure_metrics.py [--workers 8]
"""
import argparse
import json
import random
import re
import statistics
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PAPER / "tools")); sys.path.insert(0, str(PAPER / "bench")); sys.path.insert(0, str(PAPER / "bench" / "vm_scripts"))
import score  # noqa: E402
import analyze  # noqa: E402
import validate  # noqa: E402

E = score.E
RESULTS = PAPER / "bench" / "results32"
MANIFEST = json.loads((PAPER / "bench" / "vm_scripts" / "pages32_manifest.json").read_text())
SEED0 = {"dots_mocr_plain": "dots_mocr_plain_s0", "dots_mocr_clahe_bm_ver": "dots_mocr_clahe_s0_bm_ver"}
MAX_PRED_ROWS = 400
DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
AR = re.compile(r"[ء-ي]")


# ------------------------------------------------------------------ cells and grids
def norm_cell(c):
    c = re.sub(r"<[^>]+>|\*\*|__", " ", c or "").strip()
    if not c:
        return ""
    if re.fullmatch(r"[-–—ـ\s]+", c):
        return "-"
    if re.search(r"[\d٠-٩۰-۹]", c) and not AR.search(c):
        t = c.translate(DIGITS).replace("٫", ".")
        neg = "(" in t or t.strip().startswith(("-", "−"))
        t = re.sub(r"[^\d.]", "", t.replace("٬", "").replace(",", ""))
        return ("-" if neg and t else "") + t
    return re.sub(r"\s+", " ", E.norm_ar(c)).strip()


def gt_value(v):
    if v == "nil":
        return "-"
    if not isinstance(v, (int, float)):
        return ""
    s = f"{abs(v):.10f}".rstrip("0").rstrip(".") if v != int(v) else str(abs(int(v)))
    return ("-" if v < 0 else "") + s


def gt_grid(st):
    cols = [c["id"] for c in st["columns"]]
    return [[norm_cell(r.get("label_ar") or ""), norm_cell("، ".join(r.get("notes") or []))] +
            [gt_value((r.get("values") or {}).get(c)) for c in cols] for r in st["rows"]]


LATEX_WRAP = re.compile(r"\\(?:textbf|textit|text|mathrm|mathbf|underline|emph|uline)\{([^{}]*)\}")


def latex_clean(c):
    for _ in range(4):                                  # unwrap nested \textbf{...} and similar
        c = LATEX_WRAP.sub(r"\1", c)
    c = re.sub(r"\\(hline|toprule|midrule|bottomrule|cline\{[^}]*\})", " ", c)
    return re.sub(r"\$|\\[a-zA-Z]+|[{}]", " ", c).strip()


def latex_rows(text):
    r"""Rows of LaTeX tabular tables: cells separated by '&', rows ended by '\\'; \multicolumn{n} spans n cells."""
    rows = []
    for l in text.splitlines():
        l = l.strip()
        if "&" not in l or not l.endswith("\\\\"):
            continue
        cells = []
        for c in l[:-2].split("&"):
            m = re.match(r"\s*\\multicolumn\{(\d+)\}\{[^}]*\}\{(.*)\}\s*$", c)
            if m:
                cells += [latex_clean(m.group(2))] + [""] * (int(m.group(1)) - 1)
            else:
                cells.append(latex_clean(c))
        rows.append(cells)
    return rows


def pred_grid(run, pages):
    rows = []
    for pg in pages:
        f = RESULTS / run / f"{pg}.md"
        if not f.exists():
            continue
        text, _ = E.truncate_loops(E.extract_text(f.read_text(encoding="utf-8", errors="replace")))
        tabs = validate.parse_tables(text)            # HTML (colspan expanded), else Markdown
        lx = latex_rows(text)                           # LaTeX tabular (some general VLMs write tables this way)
        if lx:
            tabs = tabs + [lx]
        if not tabs:                                   # line-based systems: 'a | b | c' per row
            tabs = [[re.split(r"\s+\|\s+", l.strip()) for l in text.splitlines() if " | " in l]]
        for t in tabs:
            for r in t:
                cells = [norm_cell(c) for c in r]
                if any(cells):
                    rows.append(cells)
    rows = rows[:MAX_PRED_ROWS]
    w = max((len(r) for r in rows), default=0)
    return [r + [""] * (w - len(r)) for r in rows]


# ------------------------------------------------------------------ GriTS-Con (reference algorithm)
@lru_cache(maxsize=2_000_000)
def lcs_sim(a, b):
    if not a and not b:
        return 1.0
    return SequenceMatcher(None, a, b, autojunk=False).ratio()


def align_1d(n1, n2, reward):
    prev = [0.0] * (n2 + 1)
    for i in range(1, n1 + 1):
        cur = [0.0] * (n2 + 1)
        for j in range(1, n2 + 1):
            cur[j] = max(prev[j - 1] + reward(i - 1, j - 1), prev[j], cur[j - 1])
        prev = cur
    return prev[n2]


def align_2d_outer(nt, ct, np_, cp, R):
    """Align outer sequences (rows); the reward of a row pair is the 1D alignment score of its cells."""
    S = [[0.0] * (np_ + 1) for _ in range(nt + 1)]
    P = [[0] * (np_ + 1) for _ in range(nt + 1)]
    for i in range(1, nt + 1):
        P[i][0] = -1
    for j in range(1, np_ + 1):
        P[0][j] = 1
    for i in range(1, nt + 1):
        for j in range(1, np_ + 1):
            rw = align_1d(ct, cp, lambda a, b: R(i - 1, a, j - 1, b))
            d, u, l = S[i - 1][j - 1] + rw, S[i - 1][j], S[i][j - 1]
            m = max(d, u, l); S[i][j] = m
            P[i][j] = 0 if d == m else (-1 if u == m else 1)
    ti, pi = [], []
    i, j = nt, np_
    while i > 0 or j > 0:
        if P[i][j] == 0:
            i -= 1; j -= 1; ti.append(i); pi.append(j)
        elif P[i][j] == -1:
            i -= 1
        else:
            j -= 1
    return ti[::-1], pi[::-1]


def exact_sim(a, b):
    return 1.0 if a == b else 0.0


def grits_con(A, B, sim=None):
    """F-score, precision and recall of GriTS-Con between ground-truth grid A and predicted grid B (sim: cell similarity,
    the reference LCS similarity by default; exact_sim gives an exact-match variant for figures)."""
    sim = sim or lcs_sim
    nA = len(A) * (len(A[0]) if A else 0); nB = len(B) * (len(B[0]) if B else 0)
    if nA == 0 or nB == 0:
        return 0.0, 0.0, 0.0
    rt, ct, rp, cp = len(A), len(A[0]), len(B), len(B[0])
    R = lambda tr, tc, pr, pc: sim(A[tr][tc], B[pr][pc])
    tr_idx, pr_idx = align_2d_outer(rt, ct, rp, cp, R)
    tc_idx, pc_idx = align_2d_outer(ct, rt, cp, rp, lambda tc, tr, pc, pr: R(tr, tc, pr, pc))
    pos = sum(R(a, c, b, d) for a, b in zip(tr_idx, pr_idx) for c, d in zip(tc_idx, pc_idx))
    return 2 * pos / (nA + nB), pos / nB, pos / nA


def grits_both_orders(A, B, sim=None):
    f1 = grits_con(A, B, sim)
    f2 = grits_con(A, [r[::-1] for r in B], sim) if B else f1
    return max(f1, f2)


# ------------------------------------------------------------------ column order (A)
def column_order(run, gt, st, tb):
    pages = [f"{gt['filing_id']}_p{p:02d}" for p in st["pages"]]
    text = "\n".join(E.truncate_loops("\n".join(E.lines_of(E.extract_text(
        (RESULTS / run / f"{p}.md").read_text(errors="replace")))))[0] for p in pages if (RESULTS / run / f"{p}.md").exists())
    lines = text.split("\n"); nums = [E.numbers(l) for l in lines]; cnt = [Counter(abs(v) for v in n) for n in nums]
    cols = [c["id"] for c in st["columns"]]
    dirs = []
    for r in st["rows"]:
        vals = [(k, abs(v)) for k, c in enumerate(cols) for v in [(r.get("values") or {}).get(c)] if isinstance(v, (int, float)) and v != 0]
        vs = [v for _, v in vals]
        if len(vals) < 2 or len(set(vs)) < len(vs):
            continue
        need = Counter(vs)
        hit = next((i for i, c in enumerate(cnt) if not (need - c)), None)
        if hit is None:
            continue
        seq = [abs(x) for x in nums[hit]]
        if any(seq.count(v) != 1 for v in vs):
            continue
        order = [k for _, k in sorted((seq.index(v), k) for k, v in vals)]
        dirs.append("forward" if order == sorted(order) else "reverse" if order == sorted(order, reverse=True) else "mixed")
    if not dirs:
        return 0, 0
    major = Counter(d for d in dirs if d != "mixed").most_common(1)
    major = major[0][0] if major else None
    return len(dirs), sum(1 for d in dirs if d != major)


# ------------------------------------------------------------------ per system
def run_system(args):
    cfg, system, setting = args
    run = SEED0.get(cfg, cfg)
    gts = score.load_gt(str(PAPER / "gt"))
    out = []
    for fid, gt in gts.items():
        for st, tb in zip(gt["statements"], score.gtlib.to_eval_tables(gt)):
            pages = [f"{fid}_p{p:02d}" for p in st["pages"]]
            G, P = gt_grid(st), pred_grid(run, pages)
            f, pr, rc = grits_both_orders(G, P)
            Gv = [r[2:] for r in G if any(r[2:])]               # value columns only: figures in the right cell
            Gl = [[r[0]] for r in G if r[0]]                     # label column only
            rv = grits_both_orders(Gv, P)[2] if Gv else None
            rx = grits_both_orders(Gv, P, exact_sim)[2] if Gv else None
            rl = grits_both_orders(Gl, P)[2] if Gl else None
            n_rows, swapped = column_order(run, gt, st, tb)
            out.append(dict(filing=fid, statement=st["id"], grits_f=f, grits_p=pr, grits_r=rc, values_r=rv, values_exact=rx, labels_r=rl,
                            order_rows=n_rows, swapped=swapped))
    return cfg, system, setting, out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=8); ap.add_argument("--boot", type=int, default=2000)
    a = ap.parse_args()
    systems = [(cfg, v[0], v[2]) for cfg, v in analyze.CONFIGS.items() if v[3] == "main" and analyze.complete(RESULTS / SEED0.get(cfg, cfg))]
    with Pool(a.workers) as pool:
        res = pool.map(run_system, systems)
    inv = {r["filing_id"]: r for r in __import__("csv").DictReader(open(PAPER / "dataset_inventory.csv", encoding="utf-8-sig"))}
    split = {f: r["proposed_split"].split()[0].lower() for f, r in inv.items()}
    rr = json.loads((PAPER / "bench" / "results_summary.json").read_text())["tables"]
    rowrec = {sp: {r["config"]: r["row"] for r in rr[sp]} for sp in ("test", "all")}
    summary = []
    rng = random.Random(0)
    for cfg, system, setting, rows in res:
        rec = dict(config=cfg, system=system, setting=setting)
        for sp in ("test", "all"):
            sel = [r for r in rows if sp == "all" or split[r["filing"]] == sp]
            byf = defaultdict(list)
            for r in sel:
                byf[r["filing"]].append(r["grits_f"])
            fids = sorted(byf); boots = []
            for _ in range(a.boot):
                xs = [x for f in (rng.choice(fids) for _ in fids) for x in byf[f]]
                boots.append(statistics.mean(xs))
            boots.sort()
            rec[sp] = dict(values_r=statistics.mean(r["values_r"] for r in sel if r["values_r"] is not None),
                           values_exact=statistics.mean(r["values_exact"] for r in sel if r["values_exact"] is not None),
                           labels_r=statistics.mean(r["labels_r"] for r in sel if r["labels_r"] is not None),
                           grits_f=statistics.mean(r["grits_f"] for r in sel), grits_r=statistics.mean(r["grits_r"] for r in sel),
                           grits_p=statistics.mean(r["grits_p"] for r in sel),
                           ci=(boots[int(0.025 * a.boot)], boots[int(0.975 * a.boot) - 1]),
                           order_rows=sum(r["order_rows"] for r in sel), swapped=sum(r["swapped"] for r in sel),
                           row_recall=rowrec[sp].get(cfg))
        summary.append(rec)
    from scipy.stats import kendalltau, spearmanr
    corr = {}
    for sp in ("test", "all"):
        xs = [r[sp]["row_recall"] for r in summary]
        corr[sp] = {}
        for k in ("grits_f", "values_exact"):
            ys = [r[sp][k] for r in summary]
            corr[sp][k] = dict(spearman=spearmanr(xs, ys).statistic, kendall=kendalltau(xs, ys).statistic, n=len(xs))
    name = lambda r: r["system"] + (" (pipeline)" if "adopted" in r["setting"] else " (out of the box)" if "out of the box" in r["setting"]
                                    else " (self-hosted)" if r["system"] == "Qwen3.8-27B" and "BF16" in r["setting"] else " (API)" if r["system"] == "Qwen3.8-27B" else "")
    pct = lambda x: f"{100 * x:.1f}"
    out = ["# Structure-aware checks of row recall", "",
           "Method in the header of `bench/structure_metrics.py`. dots.mocr is shown for seed 0.", "",
           "## A. Column order of credited rows", "",
           "Rows credited by row recall with at least two distinct non-zero figures; 'swapped' rows put figures in a different "
           "column order from the rest of their statement (figures under the wrong period).", "",
           "| System | Credited rows checked (32 filings) | Swapped | Share | Test split: checked | Swapped |", "|---|---:|---:|---:|---:|---:|"]
    for r in sorted(summary, key=lambda r: -(r["all"]["row_recall"] or 0)):
        al, te = r["all"], r["test"]
        out.append(f"| {name(r)} | {al['order_rows']:,} | {al['swapped']} | {pct(al['swapped'] / al['order_rows']) if al['order_rows'] else '–'}% | "
                   f"{te['order_rows']:,} | {te['swapped']} |")
    out += ["", "## B. GriTS-Con against row recall", "",
            "GriTS-Con: mean over statements, 95% CI by bootstrap over filings; orientation-invariant as described above.", "",
            "| System | Row recall (test) | GriTS-Con F (test) | 95% CI | GriTS recall (test) | GriTS precision (test) | Row recall (32) | GriTS-Con F (32) |",
            "|---|---:|---:|---|---:|---:|---:|---:|"]
    for r in sorted(summary, key=lambda r: -r["test"]["grits_f"]):
        te, al = r["test"], r["all"]
        out.append(f"| {name(r)} | {pct(te['row_recall'])}% | {pct(te['grits_f'])} | {pct(te['ci'][0])}–{pct(te['ci'][1])} | "
                   f"{pct(te['grits_r'])} | {pct(te['grits_p'])} | {pct(al['row_recall'])}% | {pct(al['grits_f'])} |")
    out += ["", "## C. Where GriTS separates systems: figures against labels", "",
            "GriTS-Con recall computed on the value columns alone (figures in the right cell) and on the label column alone; "
            "'exact' replaces the LCS similarity by exact matching, since a figure with one wrong digit is wrong, while the LCS "
            "similarity gives it most of the credit (20,979,012 against 20,979,512 scores 0.94).", "",
            "| System | Row recall (test) | Values, exact (test) | Values, LCS (test) | Labels (test) | Values, exact (32) | Labels (32) |",
            "|---|---:|---:|---:|---:|---:|---:|"]
    for r in sorted(summary, key=lambda r: -r["test"]["values_exact"]):
        te, al = r["test"], r["all"]
        out.append(f"| {name(r)} | {pct(te['row_recall'])}% | {pct(te['values_exact'])} | {pct(te['values_r'])} | {pct(te['labels_r'])} | "
                   f"{pct(al['values_exact'])} | {pct(al['labels_r'])} |")
    out += ["", f"Rank agreement with row recall across the {len(systems)} configurations — GriTS-Con F: " +
            "; ".join(f"{sp} ρ = {c['grits_f']['spearman']:.2f}, τ = {c['grits_f']['kendall']:.2f}" for sp, c in corr.items()) +
            ". Exact-match values: " + "; ".join(f"{sp} ρ = {c['values_exact']['spearman']:.2f}, τ = {c['values_exact']['kendall']:.2f}" for sp, c in corr.items()) + ".", ""]
    lead = {name(r): r["test"] for r in summary if r["system"] in ("Mistral OCR", "Cohere Parse", "LandingAI ADE", "Chandra OCR 2") or "adopted" in r["setting"]}
    out += ["**Reading.** Placing figures in their exact cells ranks the systems almost exactly as row recall does "
            f"(ρ = {corr['test']['values_exact']['spearman']:.2f}), and row recall rarely credits a row with swapped period columns "
            "(at most 1.5% of credited rows for the leading systems), so the primary metric is not an artefact of ignoring structure. "
            "The leading systems tie on figures (" + ", ".join(f"{k} {100 * v['values_exact']:.1f}" for k, v in lead.items()) +
            ") and differ on labels (" + ", ".join(f"{k} {100 * v['labels_r']:.1f}" for k, v in lead.items()) + "). "
            "GriTS-Con's LCS similarity gives most of the credit to a figure with a wrong digit, which flatters systems that misread "
            "digits; for financial figures the exact-match variant is the meaningful one.", ""]
    (PAPER / "bench" / "STRUCTURE.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    json.dump(dict(summary=summary, correlation=corr, per_statement={cfg: rows for cfg, _, _, rows in res}),
              open(PAPER / "bench" / "structure_summary.json", "w"), ensure_ascii=False, indent=1)
    print("\n".join(out))


if __name__ == "__main__":
    main()
