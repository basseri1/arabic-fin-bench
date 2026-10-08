"""Failure taxonomy for the main configurations on all 32 filings, counted with fixed, automatic rules (no judgement
per case), so every count is reproducible and every category has concrete examples for the appendix.

Pages (158 statement pages):
  loop          – the output falls into a repetition loop (the scorer's loop rule: three identical 200-character windows),
                  in the saved text or, for self-hosted runs, when the runner stopped generation on that rule
  budget        – generation stopped at the output-token cap
  no figures    – fewer than 5 figures on a page that holds a statement
  skeleton      – at least 10 table rows but fewer than 5 figures (an empty table)
  unrelated     – at least 10 figures, and at least half of them neither in the filing's ground truth nor a
                  near-miss of it (not a one-digit misread, a separator/scale error or reversed digits): invented
                  content or heavy misreading
Statements (156, each scored on its own pages):
  omission      – at least 20% of the statement's figures appear nowhere in the output of its pages
  misplaced     – figures found (figure recall >= 95%) but rows broken (row recall < 80%)
  labels dropped  – figures mostly found (>= 50%), under 20% of the row labels found, and most output lines carrying
                    the statement's figures hold no Arabic words (the label column is missing)
  labels invented – the same, but those lines do hold Arabic words: labels written, not the printed ones
  reversed labels – at least 30% of the row labels found only with their letters in reverse order
Figures (values emitted on the statement pages, |value| >= 1000 or with decimals, years excluded):
  misread digit – one digit substituted, inserted, deleted, or two neighbours swapped, of a ground-truth figure
                  (substitutions also tallied by digit pair, e.g. 5 read as 0)
  separator     – a ground-truth figure times or divided by 10..10,000
  reversed digits – the digit string reversed equals a ground-truth figure
Digit script: figure recall on filings printed with Arabic-Indic digits against those printed with Western digits.
Writes bench/TAXONOMY.md and bench/taxonomy_summary.json.  usage: python bench/taxonomy.py
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PAPER / "tools")); sys.path.insert(0, str(PAPER / "bench")); sys.path.insert(0, str(PAPER / "bench" / "vm_scripts"))
import score  # noqa: E402
import analyze  # noqa: E402
import confidence32 as C  # noqa: E402
import validate  # noqa: E402
from rapidfuzz import fuzz  # noqa: E402

E = score.E
RESULTS = PAPER / "bench" / "results32"
SEED0 = {"dots_mocr_plain": "dots_mocr_plain_s0", "dots_mocr_clahe_bm_ver": "dots_mocr_clahe_s0_bm_ver"}
BUDGET = {"length", "max_tokens", "MAX_TOKENS"}
TABLE_LINE = re.compile(r"(\|.*\|.*\|)|(<tr\b)", re.I)


def page_raw(run, pg):
    f = RESULTS / run / f"{pg}.md"
    return f.read_text(encoding="utf-8", errors="replace") if f.exists() else ""


def page_plain(raw):
    return "\n".join(E.lines_of(E.extract_text(raw)))


def figures(text):
    return [abs(v) for v in E.numbers(text) if C.is_figure(v)]


def classify(v, G):
    """None if v is a ground-truth figure; else the error class, with the digit pair for one-digit substitutions."""
    if G[v] > 0:
        return None, None
    if v == int(v):
        s = str(int(v))
        for g in (x for x in G if x == int(x) and len(str(int(x))) == len(s)):
            gs = str(int(g))
            diff = [i for i in range(len(s)) if s[i] != gs[i]]
            if len(diff) == 1:
                return "misread digit", (gs[diff[0]], s[diff[0]])       # (printed, read)
        if s[::-1] != s and int(s[::-1]) in G:
            return "reversed digits", None
        near = {abs(x) for x in validate.digit_edits(v)} | {int(s[:i] + s[i + 1] + s[i] + s[i + 2:]) for i in range(len(s) - 1)}
        if any(x in G for x in near):
            return "misread digit", None
    for k in (10, 100, 1000, 10000):
        if round(v * k, 2) in G or round(v / k, 2) in G:
            return "separator", None
    return "other", None


def main():
    inv = {r["filing_id"]: r for r in __import__("csv").DictReader(open(PAPER / "dataset_inventory.csv", encoding="utf-8-sig"))}
    gts = score.load_gt(str(PAPER / "gt"))
    systems = [(cfg, *v) for cfg, v in analyze.CONFIGS.items() if v[3] == "main"]
    stmt_pages = {(fid, st["id"]): [f"{fid}_p{p:02d}" for p in st["pages"]] for fid, gt in gts.items() for st in gt["statements"]}
    pages_with_stmt = {p for ps in stmt_pages.values() for p in ps}
    all_pages = sorted({f"{fid}_p{p:02d}" for fid in gts for p in C.MANIFEST[fid]})
    Gf = {fid: C.gt_values(gt) for fid, gt in gts.items()}
    tables = {fid: score.gtlib.to_eval_tables(gt) for fid, gt in gts.items()}
    rows_out, examples, pairs_all = [], defaultdict(list), Counter()
    disp = lambda system, setting: system + (" (pipeline)" if "adopted" in setting else " (out of the box)" if "out of the box" in setting
                                             else " (self-hosted)" if system == "Qwen3.8-27B" and "BF16" in setting
                                             else " (API)" if system == "Qwen3.8-27B" else "")
    AR_WORD = re.compile(r"[\u0621-\u064A]{2,}")
    for cfg, system, how, setting, _ in systems:
        run = SEED0.get(cfg, cfg)
        d = RESULTS / run
        if not analyze.complete(d):
            continue
        fin = {}
        if (d / "_timing.jsonl").exists():
            for l in (d / "_timing.jsonl").read_text().splitlines():
                if l.strip():
                    r = json.loads(l); fin[r["page"]] = r.get("finish")
        # A self-hosted runner stops generation when the loop rule fires (finish = 'loop') and saves the text up to
        # that point, which the text rule below may no longer flag; count those stops too. Pages the pipeline's
        # structure retry replaced were delivered from a retry whose finish reason was not recorded: text rule only.
        retries = RESULTS / re.sub(r"(_bm)?(_ver)?$", "", run) / "_retries.json"
        if retries.exists():
            for r in json.loads(retries.read_text()):
                if isinstance(r.get("chosen"), int) or str(r.get("chosen", "")).startswith("most figures"):
                    fin.pop(r["page"], None)
        pc = Counter(); sc = Counter(); fc = Counter(); pairs = Counter(); emitted = 0
        dn = disp(system, setting)
        ex = lambda cat, what: examples[cat].append(f"{dn}: {what}") if sum(1 for e in examples[cat] if e.startswith(dn + ":")) < 2 else None
        # pages
        for pg in all_pages:
            fid = pg.rsplit("_p", 1)[0]
            raw = page_raw(run, pg); plain = page_plain(raw)
            _, cut = E.truncate_loops(plain)
            txt, _ = E.truncate_loops(plain)
            figs = figures(txt)
            if cut or fin.get(pg) == "loop":
                pc["loop"] += 1; ex("loop", pg)
            if fin.get(pg) in BUDGET:
                pc["budget"] += 1; ex("budget", pg)
            if pg in pages_with_stmt and len(figs) < 5:
                pc["no figures"] += 1; ex("no figures", pg)
                if sum(1 for l in raw.splitlines() if TABLE_LINE.search(l)) >= 10:
                    pc["skeleton"] += 1; ex("skeleton", pg)
            classes = [classify(v, Gf[fid]) for v in figs]
            emitted += len(figs)
            for (c, pair) in classes:
                if c in ("misread digit", "separator", "reversed digits"):
                    fc[c] += 1
                if pair:
                    pairs[pair] += 1
            if len(figs) >= 10 and sum(c == "other" for c, _ in classes) >= 0.5 * len(figs):
                pc["unrelated"] += 1; ex("unrelated", pg)
        # statements
        texts = {pg: E.truncate_loops(page_plain(page_raw(run, pg)))[0] for pg in all_pages}
        ai_hit = ai_tot = we_hit = we_tot = 0
        for fid, gt in gts.items():
            for st, tb in zip(gt["statements"], tables[fid]):
                blob = "\n".join(texts.get(p, "") for p in stmt_pages[(fid, st["id"])])
                c = E.score_tables([tb], blob)
                fr = c["fig_hit"] / c["fig_tot"] if c["fig_tot"] else 1.0
                rr = c["rows_hit"] / c["rows_tot"] if c["rows_tot"] else 1.0
                lr = c["lab_hit"] / c["lab_tot"] if c["lab_tot"] else 1.0
                if gt.get("digits") == "arabic-indic":
                    ai_hit += c["fig_hit"]; ai_tot += c["fig_tot"]
                elif gt.get("digits") == "western":
                    we_hit += c["fig_hit"]; we_tot += c["fig_tot"]
                need = [abs(v) for r in tb["rows"] for v in r["figs"] if C.is_figure(v)]
                out = Counter(figures(blob))
                if need and sum(1 for v in need if out[v] == 0) >= 0.2 * len(need):
                    sc["omission"] += 1; ex("omission", f"{fid} {st['id']} ({st['type']})")
                if fr >= 0.95 and rr < 0.8:
                    sc["misplaced"] += 1; ex("misplaced", f"{fid} {st['id']} ({st['type']})")
                if c["lab_tot"] >= 5 and fr >= 0.5 and lr < 0.2:
                    gtv = {abs(v) for r in tb["rows"] for v in r["figs"] if C.is_figure(v)}
                    carrying = [l for l in blob.split("\n") if any(abs(v) in gtv for v in E.numbers(l))]
                    worded = sum(1 for l in carrying if AR_WORD.search(l))
                    kind = "labels dropped" if carrying and worded < 0.5 * len(carrying) else "labels invented"
                    sc[kind] += 1; ex(kind, f"{fid} {st['id']}")
                norm = E.norm_ar(blob); labs = [E.norm_ar(r["label"]) for r in tb["rows"]]
                labs = [l for l in labs if len(l) >= 6]
                if labs:
                    rev = sum(1 for l in labs if fuzz.partial_ratio(l, norm) < 85 and fuzz.partial_ratio(l[::-1], norm) >= 85)
                    if rev >= 0.3 * len(labs):
                        sc["reversed labels"] += 1; ex("reversed labels", f"{fid} {st['id']}")
        pairs_all.update(pairs)
        rows_out.append(dict(system=system, setting=setting, how=how, run=run, pages=dict(pc), statements=dict(sc), figures=dict(fc),
                             emitted=emitted, pairs=[(f"{a}→{b}", n) for (a, b), n in pairs.most_common(4)],
                             recall_arabic_indic=ai_hit / ai_tot if ai_tot else None, recall_western=we_hit / we_tot if we_tot else None))
        print("taxonomy:", system, setting[:30], flush=True)
    n_pages, n_stmts = len(all_pages), len(stmt_pages)
    order = {r["system"] + r["setting"]: i for i, r in enumerate(sorted(rows_out, key=lambda r: -(r["recall_arabic_indic"] or 0)))}
    rows_out.sort(key=lambda r: order[r["system"] + r["setting"]])
    pct = lambda x: "–" if x is None else f"{100 * x:.1f}%"
    name = lambda r: r["system"] + (" (pipeline)" if "adopted" in r["setting"] else " (out of the box)" if "out of the box" in r["setting"]
                                    else " (self-hosted)" if r["system"] == "Qwen3.8-27B" and "BF16" in r["setting"] else " (API)" if r["system"] == "Qwen3.8-27B" else "")
    out = ["# Failure taxonomy (all 32 filings)", "",
           "Counted with fixed, automatic rules; definitions in the header of `bench/taxonomy.py`. dots.mocr is shown for seed 0. "
           f"Totals: {n_pages} statement pages, {n_stmts} statements.", "",
           "## Output-level failures (pages)", "",
           "| System | Loop | Output cap hit | No figures | of which empty table | Unrelated figures |", "|---|---:|---:|---:|---:|---:|"]
    for r in rows_out:
        p = r["pages"]
        out.append(f"| {name(r)} | {p.get('loop', 0)} | {p.get('budget', 0)} | {p.get('no figures', 0)} | {p.get('skeleton', 0)} | {p.get('unrelated', 0)} |")
    out += ["", "## Structure failures (statements)", "",
            "| System | Omission (≥20% of figures missing) | Misplaced rows | Labels dropped | Labels invented | Reversed labels |", "|---|---:|---:|---:|---:|---:|"]
    for r in rows_out:
        s = r["statements"]
        out.append(f"| {name(r)} | {s.get('omission', 0)} | {s.get('misplaced', 0)} | {s.get('labels dropped', 0)} | {s.get('labels invented', 0)} | {s.get('reversed labels', 0)} |")
    out += ["", "## Reading errors (figures) and digit script", "",
            "Counts of emitted figures; rates are per 1,000 emitted figures. Digit pairs are (printed → read), Western digits shown.", "",
            "| System | Emitted figures | One-digit misreads | per 1,000 | Separator/scale | Reversed digits | Top digit confusions | Figure recall: Arabic-Indic filings | Western-digit filings |",
            "|---|---:|---:|---:|---:|---:|---|---:|---:|"]
    for r in rows_out:
        f = r["figures"]; m = f.get("misread digit", 0)
        out.append(f"| {name(r)} | {r['emitted']:,} | {m} | {1000 * m / r['emitted'] if r['emitted'] else 0:.1f} | {f.get('separator', 0)} | "
                   f"{f.get('reversed digits', 0)} | {', '.join(f'{p} ({n})' for p, n in r['pairs']) or '–'} | "
                   f"{pct(r['recall_arabic_indic'])} | {pct(r['recall_western'])} |")
    tot_sub = sum(pairs_all.values())
    out += ["", f"Across all systems, one-digit substitutions by digit pair (printed → read): "
            + ", ".join(f"{a}→{b} {n} ({100 * n / tot_sub:.0f}%)" for (a, b), n in pairs_all.most_common(8)) + ".", "",
            "## Examples (up to two per system and category)", ""]
    for cat, exs in examples.items():
        out.append(f"- **{cat}**: " + "; ".join(exs[:8]) + (" …" if len(exs) > 8 else ""))
    (PAPER / "bench" / "TAXONOMY.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    json.dump(dict(rows=rows_out, examples=examples, digit_pairs=[(f"{a}→{b}", n) for (a, b), n in pairs_all.most_common()]),
              open(PAPER / "bench" / "taxonomy_summary.json", "w"), ensure_ascii=False, indent=1)
    print("\n".join(out))


if __name__ == "__main__":
    main()
