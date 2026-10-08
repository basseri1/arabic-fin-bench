#!/usr/bin/env python
"""Render the benchmark report (REPORT.html) from results/ + eval2 output.
Usage: python make_report.py  -> writes results/summary.json, results/summary.md, REPORT.html"""
import json, re, subprocess, sys, html, os
from pathlib import Path
BASE = Path(__file__).resolve().parent
RES = BASE / "results"
subprocess.run([sys.executable, str(BASE / "eval2.py"), "--json", str(RES / "summary.json"), "--md", str(RES / "summary.md")],
               check=True, capture_output=True)
S = json.loads((RES / "summary.json").read_text())
rows, per_table = S["summary"], S["per_table"]
RES_ENH = BASE / "results_enh"          # CLAHE-only pass (all models)
RES_ENH2X = BASE / "results_enh2x"      # CLAHE + 2x upscale (hosted models; local runs were unsafe in memory)
enh_rows, enh2x_rows = [], []
for res_dir, holder in ((RES_ENH, enh_rows), (RES_ENH2X, enh2x_rows)):
    if res_dir.exists() and any(p.is_dir() for p in res_dir.iterdir()):
        subprocess.run([sys.executable, str(BASE / "eval2.py"), "--results", str(res_dir), "--json", str(res_dir / "summary.json")], check=True, capture_output=True)
        holder.extend(json.loads((res_dir / "summary.json").read_text())["summary"])

INFO = {  # display name, kind, params, decoding, prompt mode
 "mistral_ocr": ("Mistral OCR (latest)", "hosted API", "—", "API default", "document → markdown"),
 "dots_mocr":   ("dots.mocr", "local · MLX bf16", "3.0B", "T=0.1 (official parser)", "layout-all JSON, HTML tables"),
 "dots_ocr":    ("dots.ocr", "local · MLX bf16", "3.0B", "T=0.1 (official parser)", "layout-all JSON, HTML tables"),
 "qari4b":      ("Qari-OCR 0.4 (Qwen3-VL-4B + LoRA, merged)", "local · MLX bf16", "4.4B", "greedy", "“Free OCR.” (plain text)"),
 "qari2b":      ("Qari-OCR 0.3 (Qwen2-VL-2B)", "local · MLX bf16", "2.2B", "greedy", "card prompt (plain text)"),
 "chandra2":    ("Chandra-OCR 2 (Qwen3.5)", "local · MLX bf16", "5.3B", "greedy", "ocr_layout → HTML blocks"),
 "chandra1":    ("Chandra 1 (Qwen3-VL-8B)", "local · MLX bf16", "8.8B", "greedy", "ocr_layout → HTML blocks"),
 "surya2":      ("Surya OCR 2", "local · llama.cpp (Metal)", "0.65B", "pipeline default", "full-page recognition → HTML blocks"),
 "legalocr":    ("Arabic Legal Documents OCR 1.0 (Gemma-3-4B)", "local · MLX bf16", "4.3B", "greedy", "“Extract details to JSON.” + card preprocessing (grayscale, 1024px)"),
 "ain":         ("AIN-7B (Qwen2-VL-7B) — partial, killed at 8/11", "local · MLX bf16", "8.3B", "greedy", "instruction → Markdown"),
 "nanonets":    ("Nanonets-OCR2-3B (Qwen2.5-VL-3B)", "local · MLX bf16", "3.8B", "greedy", "card financial-docs prompt → HTML tables"),
 "nextocr":     ("Next OCR 8B (Qwen3-VL-8B finetune)", "local · MLX bf16", "8.8B", "greedy", "card system prompt + instruction → Markdown"),
 "persar2b":    ("Qwen3-VL-2B Persian-Arabic OCR (line-level)", "local · MLX bf16 + PaddleOCR det", "2.1B", "greedy", "detect lines → crop → recognize → rows by geometry"),
 "paddle_ar":   ("PaddleOCR classical Arabic", "local · CPU · PP-OCRv5 det + Arabic rec", "~10M", "pipeline default", "lines → rows by geometry"),

 "xcuros":      ("XCurOS 1.2-8B (Qwen3-VL-8B)", "local · MLX bf16", "8.8B", "greedy", "instruction → Markdown"),
 "glm":         ("GLM-OCR — “Text Recognition:”", "local · MLX bf16", "1.1B", "greedy", "whole page"),
 "glm_table":   ("GLM-OCR — “Table Recognition:”", "local · MLX bf16", "1.1B", "greedy", "whole page"),
 "lfm25vl":     ("LFM2.5-VL-1.6B", "local · MLX bf16", "1.6B", "T=0.1, min_p 0.15, rep 1.05 (docs)", "instruction → Markdown"),
 "paddle":      ("PaddleOCR-VL (0.9B) pipeline", "local · Paddle CPU", "0.9B", "pipeline default", "layout + VL recognition"),
 "north":       ("North-Micro-Vision-Instruct", "local · MLX bf16", "2.5B", "greedy", "instruction → Markdown"),
 "aya8b":       ("Aya Vision 8B", "local · MLX bf16", "8.6B", "T=0.3 (card)", "instruction → Markdown"),
 "qwen38_27b":  ("Qwen3.8-27B (OpenRouter, thinking off)", "hosted API", "27B", "T=0, reasoning disabled", "instruction → Markdown"),
 "qwen38_27b_think": ("Qwen3.8-27B (OpenRouter, thinking on)", "hosted API", "27B", "T=0, ~100–175 hidden reasoning tokens/page", "instruction → Markdown"),
 "qwen36_27b":  ("Qwen3.6-27B (OpenRouter, thinking off)", "hosted API", "27B", "T=0, reasoning disabled", "instruction → Markdown"),
 "qwen3vl_32b": ("Qwen3-VL-32B-Instruct (OpenRouter)", "hosted API", "32B", "T=0", "instruction → Markdown"),
 "nemotron12b_vl": ("Nemotron Nano 12B v2 VL (OpenRouter, free)", "hosted API", "12B", "T=0", "instruction → Markdown"),
 "ernie45_vl":   ("ERNIE 4.5 VL 424B-A47B (OpenRouter)", "hosted API", "424B MoE", "T=0", "instruction → Markdown"),
 "aya32b_api":   ("Aya Vision 32B (Cohere API)", "hosted API", "32B", "T=0.3 (docs)", "instruction → Markdown"),
 "cmda_vision":  ("Command A Vision (Cohere API)", "hosted API", "112B", "T=0", "instruction → Markdown"),
}
ORDER_TABLES = ["ar-P&L","ar-OCI","ar-Bal.sheet","ar-Equity","ar-Cashflow","ma-P&L","ma-OCI","ma-Bal.sheet","ma-Equity","ma-Cashflow","ma-Non-cash"]
TABLE_LABEL = {"P&L":"P&L","OCI":"OCI","Bal.sheet":"Balance","Equity":"Equity","Cashflow":"Cash flow","Non-cash":"Non-cash"}

def pct(x): return "—" if x != x else f"{x*100:.0f}%"
def pct1(x): return "—" if x != x else f"{x*100:.1f}%"

overall = {r["model"]: r for r in rows if r["doc"] == "ALL"}
BEST_ENH = {}   # model -> (row_recall, label) for the best complete enhanced run
for label, rws in (("CLAHE", enh_rows), ("CLAHE+2×", enh2x_rows)):
    for r in rws:
        if r["doc"] == "ALL" and r["pages"] == "11" and r["row_recall"] == r["row_recall"]:
            if r["model"] not in BEST_ENH or r["row_recall"] > BEST_ENH[r["model"]][0]:
                BEST_ENH[r["model"]] = (r["row_recall"], label, r["fig_recall"])
bydoc = {(r["model"], r["doc"]): r for r in rows if r["doc"] != "ALL"}
ENH_ONLY = {}
for r in enh_rows:
    if r["doc"] == "ALL" and r["pages"] == "11" and r["model"] not in overall:
        ENH_ONLY[r["model"]] = dict(r, _enh_only=True)
overall.update(ENH_ONLY)
models = sorted(overall, key=lambda m: (-(overall[m]["row_recall"] if overall[m]["row_recall"] == overall[m]["row_recall"] else -1), m))
probes = {}
for m in overall:
    f = RES / m / "_digit_probe.json"
    if f.exists():
        probes[m] = json.loads(f.read_text())["summary"]
NARR = json.loads((BASE / "report_narrative.json").read_text()) if (BASE / "report_narrative.json").exists() else {}

def esc(s): return html.escape(str(s))

# ---------- ranked bars: one row per model, all measured variants as parallel bars
VAL = {}
try:
    for r in json.loads((BASE / "results_val" / "summary.json").read_text()):
        VAL[r["run"]] = r
except Exception:
    pass
VAL_MAP = {("chandra2","plain"):"Chandra-2 plain", ("chandra2","CLAHE"):"Chandra-2 CLAHE", ("chandra2","CLAHE+2×"):"Chandra-2 CLAHE+2x",
           ("mistral_ocr","plain"):"Mistral plain", ("mistral_ocr","CLAHE"):"Mistral CLAHE", ("mistral_ocr","CLAHE+2×"):"Mistral CLAHE+2x",
           ("dots_mocr","plain"):"dots.mocr plain", ("dots_mocr","CLAHE"):"dots.mocr CLAHE", ("surya2","plain"):"Surya-2 plain", ("qwen36_27b","CLAHE"):"Qwen3.6 CLAHE"}
ENH_ALL = {r["model"]: r for r in enh_rows if r["doc"] == "ALL" and r["pages"] == "11"}
ENH2X_ALL = {r["model"]: r for r in enh2x_rows if r["doc"] == "ALL" and r["pages"] == "11"}

def decisions_section():
    """dots.mocr pipeline-decision analysis (decisions.json from decisions.py)."""
    import subprocess, sys as _sys
    try: subprocess.run([_sys.executable, "decisions.py"], cwd=str(BASE), capture_output=True, timeout=600)
    except Exception: pass
    f = BASE / "decisions.json"
    if not f.exists(): return ""
    D = json.loads(f.read_text())
    chip = {"KEEP": "good", "DROP": "bad", "neutral": "", "baseline": "", "noise": ""}
    rows = []
    for r in D["rows"]:
        d = r["decision"]; cls = chip.get(d, "")
        rows.append(f"<tr><th scope=row>{esc(r['step'])}</th><td>{esc(r['stage'])}</td><td class=num>{r['raw_rows']} → <b>{r['bm_rows']}</b></td><td class=num>{r['bm_figs']}</td>"
                    f"<td class=num><span class='delta {('good' if r['delta_rows']>0 else 'bad' if r['delta_rows']<0 else '')}'>{r['delta_rows']:+d}</span></td><td class=num>{'' if r['s_page'] is None else round(r['s_page'])}</td>"
                    f"<td><span class='delta {cls}'>{esc(d)}</span></td><td class=small>{esc(r['note'])}</td></tr>")
    c_rows = []
    order = ["dots_mocr_clahe", "dots_mocr_clahe_bm", "dots_mocr_clahe_bm_ver", "dots_mocr_plain", "dots_mocr_plain_bm", "dots_mocr_plain_bm_ver",
             "dots_mocr_clahe_pad_bm_ver", "dots_mocr_redfree_clahe_pad_bm_ver"]
    label = {"dots_mocr_clahe": "CLAHE → dots.mocr (raw)", "dots_mocr_clahe_bm": "+ band-merge", "dots_mocr_clahe_bm_ver": "+ verification (= final pipeline)",
             "dots_mocr_plain": "plain → dots.mocr + retry (raw)", "dots_mocr_plain_bm": "plain + band-merge", "dots_mocr_plain_bm_ver": "plain + verification",
             "dots_mocr_clahe_pad_bm_ver": "CLAHE + padding, full chain", "dots_mocr_redfree_clahe_pad_bm_ver": "red-free + CLAHE + padding, full chain"}
    for k in order:
        v = D["stage_c"].get(k)
        if not v: continue
        cells = "".join(f"<td class=num>{v[doc]['row']:.1f}%</td>" if doc in v else "<td class=na>–</td>" for doc in ("aramco", "maaden", "drilling"))
        c_rows.append(f"<tr><th scope=row>{esc(label.get(k, k))}</th>{cells}</tr>")
    return f"""
<h2>dots.mocr pipeline — enhancement decisions</h2>
<p class="prose">Goal: the most accurate dots.mocr pipeline on all three filings, treating every candidate pre-/post-processing step as an include-or-drop decision rather than an ablation. Steps were first scored on the Ma'aden scans (the only pages where dots still errs), <em>with the band-merge post-processing in the loop</em> because it is itself a kept step; a repeatability run (three sampling seeds) set the noise floor; kept steps were combined (greedy forward selection + all-kept); and the surviving configurations were validated end-to-end on all 17 pages of the three companies with the retry check and arithmetic verification in place.</p>
<div class="findings">
<div class="finding"><h4>The real risk is a silent structural failure, not digit noise</h4><p>Same CLAHE pages, three sampling seeds: 174 · <b>131</b> · 174 of 175 rows. The outlier emitted the whole balance sheet with the 2024 column missing — perfectly plausible output without ground truth. The plain 200-dpi run (130) had failed the same way, so part of CLAHE's apparent gain for dots was a sampling path, not legibility. A GT-free <b>structure check</b> (value columns per table vs period headers on the page; table structure present when a page is full of numbers) flags exactly these pages and no good page; flagged pages are re-run with another seed. Kept.</p></div>
<div class="finding"><h4>Band-merge rescues the model's layout flips</h4><p>Cropping made dots write p16 as 157 line-level text blocks (144/175 raw); the geometry-aware row join brings it back to 172 and fixes the EPS row everywhere (+1 row on every variant). Kept. The crops themselves still lose a row or two elsewhere and are dropped; blue-ink removal flips the cash-flow pages (138) although its mask touches no text pixel.</p></div>
<div class="finding"><h4>Image tweaks are within noise; prompt and resolution are not</h4><p>Padding, red-ink removal, CLAHE strength and tile size move the score by at most one row or figure and trade one row for another across companies (padding: +1 Ma'aden figure, −1 Aramco row). 150 dpi (−51), grayscale without CLAHE (−45) and dots' plain-text prompt (−117) are real losses. Greedy T = 0 is −1 and not adopted: the official T 0.1 with seed 0 plus the retry check is both better and now robust.</p></div>
</div>
<h3>Candidate steps (Ma'aden, 175 rows / 367 figures; scored after band-merge)</h3>
<div class="tablewrap"><table><thead><tr><th>step</th><th>stage</th><th>rows raw → band-merged</th><th>figs</th><th>Δ rows vs CLAHE</th><th>s/page</th><th>decision</th><th>note</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>
<div class="legend">stage A = image preparation &amp; decoding · B = page cleaning (ink removal, header/footer/signature crops from three layout detectors) · B2 = combinations · noise = repeatability of the baseline with other sampling seeds</div>
<h3>Validation on all three companies (17 pages, 428 rows) — row recall</h3>
<div class="tablewrap"><table><thead><tr><th>configuration</th><th>Aramco (digital)</th><th>Ma'aden (scan)</th><th>Arabian Drilling (scan)</th></tr></thead><tbody>{"".join(c_rows)}</tbody></table></div>
<p class="prose"><b>Does CLAHE survive the retry step?</b> Plain 200-dpi pages with the same retry/band-merge/verification chain: the structure check caught the balance-sheet column drop (seed 1 failed the check too, seed 2 passed) and the run ends at 99.3% of all rows — still two Ma'aden equity rows short of CLAHE's 99.8%. So CLAHE is kept on evidence, not on the sampling lottery.</p>
<p class="prose"><b>Adopted pipeline:</b> render at 200 dpi → grayscale + CLAHE (clip 2, tile 8) → dots.mocr with its own layout prompt and decoding (T 0.1, seed 0) → structure check, re-run flagged pages with seeds 1–3 → band-merge of text blocks into rows → arithmetic verification. 427/428 rows (99.8%) and 99.7% of figures across the three filings; the one miss is the Ma'aden balance-sheet total crossed by a signature. Not adopted: padding, red/blue ink removal, crops (any detector), resolution changes, sharpening, T = 0, plain-text prompt.</p>
"""

def variants_for(m):
    o = overall[m]; out = []
    if not o.get("_enh_only"): out.append(("plain", o["row_recall"], o["fig_recall"], "v-plain"))
    if m in ENH_ALL: out.append(("CLAHE", ENH_ALL[m]["row_recall"], ENH_ALL[m]["fig_recall"], "v-clahe"))
    if m in ENH2X_ALL: out.append(("CLAHE+2×", ENH2X_ALL[m]["row_recall"], ENH2X_ALL[m]["fig_recall"], "v-2x"))
    for (mm, var), run in VAL_MAP.items():
        if mm == m and run in VAL:
            out.append((f"{var} + verification", VAL[run]["rows_after"] / 319, VAL[run]["figs_after"] / 943, "v-ver"))
    return out
bars = []
for m in models:
    o = overall[m]; name, kind, params, dec, mode = INFO.get(m, (m, "", "", "", ""))
    if str(o.get("pages")) != "11" and "partial" not in name:
        name = f"{name} — partial {o.get('pages')}/11"
    vs = variants_for(m)
    rows_html = "".join(f'<div class="vbar {cls}" style="--v:{v if v==v else 0}"><span class="vlab">{esc(lab)} <b>{v*100:.1f}%</b> <small>· {f*100:.0f}% figs</small></span></div>' for lab, v, f, cls in vs)
    bars.append(f'''<li class="bar-row">
  <div class="bar-name"><span class="m">{esc(name)}</span><span class="kind">{esc(kind)}{' · ' + esc(params) if params and params != '—' else ''}</span>
    <span class="kind">{o.get('looped',0)}/{o['pages']} looped · {o['s_page']:.0f} s/page · {pct(o['label_recall'])} labels</span></div>
  <div class="vbars">{rows_html}</div>
</li>''')
legend_html = ('<div class="legend" style="margin:6px 0 10px"><span class="sw v-plain"></span> plain (pages as rendered) &nbsp; <span class="sw v-clahe"></span> CLAHE &nbsp; '
               '<span class="sw v-2x"></span> CLAHE + 2× upscale (hosted) &nbsp; <span class="sw v-ver"></span> + arithmetic verification &nbsp; — bar length = rows intact</div>')

# ---------- Ma'aden-only pre-processing ablations (6 scanned pages, 175 rows)
def maaden_rows(d):
    GTm = GT_M
    hit = tot = 0
    for ti, tb in enumerate(GTm, 1):
        pages = [f"maaden_p{n}" for n in (11,12,13,14,15,16)]
        pp = {1:["maaden_p11"],2:["maaden_p12"],3:["maaden_p13"],4:["maaden_p14"],5:["maaden_p15","maaden_p16"],6:["maaden_p16"]}[ti]
        fs = [Path(d) / f"{pg}.md" for pg in pp]
        if not all(f.exists() for f in fs): return None
        import eval2 as _e
        blob = "\n".join(_e.truncate_loops("\n".join(_e.lines_of(_e.extract_text(f.read_text(errors="replace")))))[0] for f in fs)
        c = _e.score_tables([tb], blob); hit += c["rows_hit"]; tot += c["rows_tot"]
    return hit / tot if tot else None
sys.path.insert(0, str(BASE)); import eval2 as _ev
GT_M = _ev.parse_gt((BASE / "maaden_main_tables.md").read_text())
ABL = {
 "mistral_ocr": [("plain", "results/mistral_ocr"), ("CLAHE", "results_exp/mistral_abl_clahe"), ("CLAHE + red-ink removal", "results_exp/mistral_abl_clahe_redfree"), ("CLAHE + 1-px stroke thickening", "results_exp/mistral_abl_clahe_dilate"), ("CLAHE + NLM denoise", "results_exp/mistral_abl_clahe_nlm"), ("CLAHE + Sauvola binarization", "results_exp/mistral_abl_clahe_sauvola"), ("CLAHE + auto-deskew", "results_exp/mistral_abl_clahe_deskew"), ("CLAHE + 2× upscale", "results_enh2x/mistral_ocr")],
 "dots_mocr":   [("plain", "results/dots_mocr"), ("CLAHE", "results_enh/dots_mocr"), ("CLAHE + red-ink removal", "results_exp/dots_mocr_redfree")],
 "chandra2":    [("plain", "results/chandra2"), ("CLAHE", "results_enh/chandra2"), ("CLAHE + 2× upscale", "results_enh2x/chandra2"), ("CLAHE + red-ink removal", "results_exp/chandra2_redfree")],
}
abl_rows = []
for m, vs in ABL.items():
    cells = []
    for lab, d in vs:
        v = maaden_rows(d)
        if v is None: continue
        cls = "v-plain" if lab == "plain" else ("v-2x" if "2×" in lab else ("v-abl" if "+" in lab else "v-clahe"))
        cells.append(f'<div class="vbar {cls}" style="--v:{v}"><span class="vlab">{esc(lab)} <b>{v*100:.1f}%</b></span></div>')
    abl_rows.append(f'<li class="bar-row"><div class="bar-name"><span class="m">{esc(INFO.get(m,(m,))[0])}</span><span class="kind">Ma\'aden scans · rows / 175</span></div><div class="vbars">{"".join(cells)}</div></li>')
abl_section = f'''<h2>Ma'aden scans — pre-processing ablations</h2>
<p class="prose">Same six scanned pages (175 rows), each step applied on top of CLAHE, for the three models we tested it on. Red-ink removal masks the hand-drawn annotation boxes (HSV threshold → inpaint); binarization and blind deskew are included to show what not to do with VLM readers.</p>
<ol class="bars">{"".join(abl_rows)}</ol>'''

# ---------- heatmap
hm_head = "".join(f'<th class="{"grp-start" if t.startswith("ma-") and t=="ma-P&L" else ""}">{TABLE_LABEL[t.split("-",1)[1]]}</th>' for t in ORDER_TABLES)
hm_rows = []
for m in models:
    vals = {r["table"]: r["row_recall"] for r in per_table if r["model"] == m}
    cells = []
    for t in ORDER_TABLES:
        v = vals.get(t, float("nan"))
        if v != v:
            cells.append('<td class="na">–</td>')
        else:
            cells.append(f'<td class="heat{" hi" if v >= 0.55 else ""}{" grp-start" if t=="ma-P&L" else ""}" style="--v:{v:.3f}">{v*100:.0f}</td>')
    hm_rows.append(f'<tr><th scope="row">{esc(INFO.get(m,(m,))[0])}</th>{"".join(cells)}</tr>')

# ---------- full metrics table
def mrow(m, doc):
    r = bydoc.get((m, doc)) if doc != "ALL" else overall.get(m)
    if not r: return ""
    ai = r.get("ai_share", float("nan")); ai_s = "—" if (ai != ai or doc != "maaden") else f"{ai*100:.0f}%"
    return (f'<tr class="{ "all" if doc=="ALL" else "" }"><th scope="row">{esc(INFO.get(m,(m,))[0]) if doc=="aramco" else ""}</th><td>{ {"aramco":"Aramco (digital)","maaden":"Maaden (scans)","ALL":"overall"}[doc]}</td>'
            f'<td>{r.get("looped",0)}/{r["pages"]}</td><td>{pct1(r["fig_recall"])}</td><td>{pct1(r["fig_sgn"])}</td><td>{pct1(r["row_recall"])}</td>'
            f'<td>{pct1(r["label_recall"])}</td><td>{pct1(r["num_prec"])}</td><td>{"—" if r["cer"]!=r["cer"] else f"{r["cer"]:.2f}"}</td><td>{"—" if r["wer"]!=r["wer"] else f"{r["wer"]:.2f}"}</td><td>{ai_s}</td><td>{r["s_page"]:.0f}</td></tr>')
full_rows = "".join(mrow(m, d) for m in models for d in ("aramco", "maaden", "ALL"))

# ---------- digit probe table
probe_rows = "".join(f'<tr><th scope="row">{esc(INFO.get(m,(m,))[0])}</th><td>{esc(probes[m]["western"])}</td><td>{esc(probes[m]["arabic_indic"])}</td></tr>' for m in models if m in probes)

# ---------- per-model notes
note_items = []
for m in models:
    name, kind, params, dec, mode = INFO.get(m, (m, "", "", "", ""))
    note = NARR.get("models", {}).get(m, "")
    note_items.append(f'<div class="note"><h4>{esc(name)}</h4><p class="spec">{esc(kind)} · {esc(params)} · decoding: {esc(dec)} · {esc(mode)}</p><p>{note}</p></div>')

# ---------- samples (RTL snippets)
def sample(m, page, n=6):
    f = RES / m / f"{page}.md"
    if not f.exists(): return ""
    sys.path.insert(0, str(BASE)); import eval2
    t = eval2.extract_text(f.read_text(errors="replace"))
    lines = [l for l in eval2.lines_of(t) if len(eval2.numbers(l)) >= 2][:n]
    return "\n".join(re.sub(r"\s*\|\s*", " | ", re.sub(r"\s+", " ", l)).strip(" |") for l in lines)
samples = "".join(f'<figure class="sample"><figcaption>{esc(INFO.get(m,(m,))[0])} — Aramco comprehensive income (p13), first rows as produced</figcaption><pre dir="rtl" lang="ar">{esc(sample(m, "aramco_p13"))}</pre></figure>'
                  for m in ["mistral_ocr", "dots_mocr", "qari4b"] if m in overall and sample(m, "aramco_p13"))

# ---------- generalization check: Arabian Drilling (third document, top models only)
drill_section = ""
RES_DR = BASE / "results_drill"
if RES_DR.exists() and any(p.is_dir() for p in RES_DR.iterdir()):
    env = dict(os.environ, EVAL_DOCS="drilling")
    subprocess.run([sys.executable, str(BASE / "eval2.py"), "--results", str(RES_DR), "--json", str(RES_DR / "summary.json")], check=True, capture_output=True, env=env)
    DR = json.loads((RES_DR / "summary.json").read_text())
    dr_all = {r["model"]: r for r in DR["summary"] if r["doc"] == "drilling" and r["pages"] == "6/6"}
    dr_tab = {}
    for r in DR["per_table"]:
        dr_tab.setdefault(r["model"], {})[r["table"]] = r["row_recall"]
    DRN = {"mistral_ocr": "Mistral OCR", "mistral_ocr_clahe": "Mistral OCR · CLAHE", "mistral_ocr_clahe2x": "Mistral OCR · CLAHE+2×",
           "dots_mocr": "dots.mocr", "dots_mocr_clahe": "dots.mocr · CLAHE", "chandra2": "Chandra-OCR 2", "chandra2_clahe": "Chandra-OCR 2 · CLAHE"}
    order = [k for k in ["mistral_ocr", "mistral_ocr_clahe", "mistral_ocr_clahe2x", "dots_mocr", "dots_mocr_clahe", "chandra2", "chandra2_clahe"] if k in dr_all]
    order += [k for k in dr_all if k.endswith("_verified")]
    tabs = ["dr-P&L", "dr-OCI", "dr-Bal.sheet", "dr-Equity", "dr-Cashflow", "dr-Non-cash"]
    trs = []
    for k in order:
        r = dr_all[k]; nm = DRN.get(k.replace("_verified", ""), k) + (" + verification" if k.endswith("_verified") else "")
        cells = "".join(f'<td class="heat{" hi" if (dr_tab.get(k, {}).get(t, 0) or 0) >= 0.55 else ""}" style="--v:{dr_tab.get(k, {}).get(t, 0) or 0:.3f}">{(dr_tab.get(k, {}).get(t, 0) or 0)*100:.0f}</td>' for t in tabs)
        trs.append(f'<tr><th scope="row">{esc(nm)}</th><td>{r["row_recall"]*100:.1f}%</td><td>{r["fig_recall"]*100:.1f}%</td><td>{r["label_recall"]*100:.0f}%</td><td>{r["s_page"]:.0f}</td>{cells}</tr>')
    drill_section = f'''<h2>Does it generalize? A third filing: Arabian Drilling FY2024</h2>
<p class="prose">A fresh scanned filing (6 pages, 109 rows, 220 figures, Arabic-Indic digits, no annotations, landscape equity statement) run after the benchmark was designed, with the three top contenders and their best input treatments. Ground truth was transcribed and arithmetically verified the same way.</p>
<div class="tablewrap"><table><thead><tr><th>run</th><th>rows intact</th><th>figures</th><th>labels</th><th>s/page</th><th>P&amp;L</th><th>OCI</th><th>Balance</th><th>Equity</th><th>Cash flow</th><th>Non-cash</th></tr></thead><tbody>{"".join(trs)}</tbody></table></div>
<div class="legend">Per-statement cells: % of that statement's rows intact (the six right-hand columns).</div>'''

# ---------- plain vs enhanced (CLAHE + 2x upscale) comparison
enh_section = ""
if enh_rows:
    done_enh = {r["model"] for r in enh_rows if r["doc"] == "ALL" and r["pages"] == "11"}
    eo = {r["model"]: r for r in enh_rows if r["doc"] == "ALL" and r["model"] in done_enh}
    ebd = {(r["model"], r["doc"]): r for r in enh_rows if r["doc"] != "ALL" and r["model"] in done_enh}
    running_enh = {r["model"] for r in enh_rows if r["doc"] == "ALL"} - done_enh
    e2 = {r["model"]: r for r in enh2x_rows if r["doc"] == "ALL" and r["pages"] == "11"}
    def cell(a, b):
        if a != a or b != b: return "—"
        d = (b - a) * 100; cls = "good" if d >= 1 else ("bad" if d <= -1 else "")
        return f'<span class="delta {cls}">{a*100:.1f} → {b*100:.1f} <small>({d:+.1f})</small></span>'
    trs = []
    allm = sorted(set(overall) | set(eo), key=lambda m: -max((overall.get(m, {}).get("row_recall") or 0), (eo.get(m, {}).get("row_recall") or 0)))
    for m in allm:
        o, e = overall.get(m), eo.get(m)
        name = esc(INFO.get(m, (m,))[0])
        def pair(doc, key):
            a = (bydoc.get((m, doc)) or {}).get(key, float("nan")) if doc != "ALL" else (o or {}).get(key, float("nan"))
            b = (ebd.get((m, doc)) or {}).get(key, float("nan")) if doc != "ALL" else (e or {}).get(key, float("nan"))
            return cell(a, b)
        note = "" if (o and e) else ("<small>enhanced only</small>" if e else ("<small>enhanced run in progress</small>" if m in running_enh else "<small>plain only</small>"))
        x = e2.get(m); x_cell = f"{x['row_recall']*100:.1f} / {x['fig_recall']*100:.1f}" if x else "—"
        trs.append(f"<tr><th scope=row>{name} {note}</th><td>{pair('ALL','row_recall')}</td><td>{pair('aramco','row_recall')}</td><td>{pair('maaden','row_recall')}</td><td>{pair('ALL','fig_recall')}</td><td>{pair('maaden','fig_recall')}</td><td>{x_cell}</td></tr>")
    enh_section = f'''<h2>Plain vs enhanced input</h2>
<p class="prose">Same models, same pages, pre-processed with CLAHE (clip 2.0, 8×8 tiles) before OCR. Each cell reads <em>plain → CLAHE (delta)</em>; green = helps by ≥1 point, red = hurts. The last column is a stronger variant — CLAHE + 2× Lanczos upscale + unsharp — run for the hosted models only (it multiplies the local models' vision-token count and exhausted memory on the 36 GB machine).</p>
<div class="tablewrap"><table><thead><tr><th>model</th><th>rows · overall</th><th>rows · Aramco (digital)</th><th>rows · Ma'aden (scans)</th><th>figures · overall</th><th>figures · Ma'aden</th><th>CLAHE+2× rows / figs (hosted)</th></tr></thead><tbody>{"".join(trs)}</tbody></table></div>
<div class="legend">Models still running in the enhanced pass show “plain only” until they finish.</div>'''

page = f'''<meta charset="utf-8">
<title>Qawaim OCR Bench</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Serif:wght@500;600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+Arabic:wght@400;500&display=swap">
<style>
:root{{--paper:#F5F6F3;--surface:#FFFFFF;--ink:#1B1F1E;--ink-2:#4A524E;--muted:#7D8782;--rule:#D6DBD7;--accent:#0E5E63;--accent-ink:#FFFFFF;--good:#2F7D4F;--warn:#B9821E;--bad:#B3412E;--chip:#E9EEEB}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--paper:#141716;--surface:#1C201F;--ink:#E7EAE6;--ink-2:#C3C9C5;--muted:#8E9893;--rule:#2E3533;--accent:#4FB3A9;--accent-ink:#0E1514;--good:#5FB27E;--warn:#D9A441;--bad:#D9705B;--chip:#242A28}}}}
:root[data-theme="dark"]{{--paper:#141716;--surface:#1C201F;--ink:#E7EAE6;--ink-2:#C3C9C5;--muted:#8E9893;--rule:#2E3533;--accent:#4FB3A9;--accent-ink:#0E1514;--good:#5FB27E;--warn:#D9A441;--bad:#D9705B;--chip:#242A28}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--paper);color:var(--ink);font-family:"IBM Plex Sans",system-ui,-apple-system,Segoe UI,sans-serif;font-size:16px;line-height:1.55}}
.wrap{{max-width:1120px;margin:0 auto;padding:48px 28px 80px}}
.prose{{max-width:72ch}}
h1,h2,h3,h4{{font-family:"IBM Plex Serif",Georgia,serif;text-wrap:balance;margin:0}}
h1{{font-size:2.6rem;font-weight:600;letter-spacing:-0.01em;line-height:1.1}}
h2{{font-size:1.5rem;font-weight:600;margin:56px 0 14px;padding-top:18px;border-top:1px solid var(--rule)}}
h3{{font-size:1.15rem;font-weight:600;margin:28px 0 8px}}
h4{{font-size:1.05rem;font-weight:600}}
p{{margin:0 0 12px}}
.eyebrow{{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:.78rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-bottom:10px}}
.lede{{font-size:1.15rem;color:var(--ink-2);max-width:66ch;margin-top:14px}}
.meta{{display:flex;flex-wrap:wrap;gap:8px 22px;margin-top:18px;font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:.8rem;color:var(--muted)}}
.verdict{{margin-top:36px;padding:22px 24px;background:var(--surface);border:1px solid var(--rule);border-left:4px solid var(--accent)}}
.verdict p{{max-width:78ch}}
ol.bars{{list-style:none;margin:18px 0 0;padding:0;display:grid;gap:10px}}
.bar-row{{display:grid;grid-template-columns:minmax(200px,1.2fr) minmax(220px,2fr) minmax(260px,1.4fr);gap:14px;align-items:center;padding:8px 0;border-bottom:1px solid var(--rule)}}
.bar-name .m{{display:block;font-weight:600}}
.bar-name .kind{{display:block;font-size:.78rem;color:var(--muted);font-family:"IBM Plex Mono",ui-monospace,monospace}}
.bar-track{{position:relative;height:22px;background:var(--chip);overflow:hidden}}
.bar-row{{grid-template-columns:minmax(220px,1fr) minmax(320px,3fr)}}
.vbars{{display:flex;flex-direction:column;gap:4px}}
.vbar{{position:relative;height:16px;background:var(--chip)}}
.vbar::before{{content:"";position:absolute;inset:0 auto 0 0;width:calc(var(--v)*100%);background:var(--accent)}}
.vbar.v-clahe::before{{background:color-mix(in oklab,var(--accent) 55%,var(--surface))}}
.vbar.v-2x::before{{background:transparent;border:1.5px dashed var(--accent);box-sizing:border-box}}
.vbar.v-ver::before{{background:var(--good)}}
.vbar.v-abl::before{{background:color-mix(in oklab,var(--accent) 35%,var(--surface))}}
.vlab{{position:absolute;left:8px;top:0;line-height:16px;font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:.72rem;color:var(--ink);white-space:nowrap;text-shadow:0 0 3px var(--surface),0 0 3px var(--surface)}}
.vlab small{{color:var(--ink-2)}}
.sw{{display:inline-block;width:14px;height:10px;vertical-align:middle;margin-right:4px;background:var(--accent)}}
.sw.v-clahe{{background:color-mix(in oklab,var(--accent) 55%,var(--surface))}} .sw.v-2x{{background:transparent;border:1.5px dashed var(--accent)}} .sw.v-ver{{background:var(--good)}}
.bar-fill{{position:absolute;inset:0 auto 0 0;width:calc(var(--v)*100%);background:var(--accent)}}
.bar-ghost{{position:absolute;inset:0 auto 0 0;width:calc(var(--v)*100%);border:1px dashed var(--accent);box-sizing:border-box;opacity:.8}}
.bar-meta .enh{{color:var(--good);font-weight:600}}
.bar-val{{position:absolute;right:6px;top:3px;line-height:16px;padding:0 5px;background:var(--surface);color:var(--ink);font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:.78rem;font-variant-numeric:tabular-nums}}
.bar-meta{{display:flex;flex-wrap:wrap;gap:4px 14px;font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:.76rem;color:var(--ink-2);font-variant-numeric:tabular-nums}}
.tablewrap{{overflow-x:auto;margin:14px 0 6px;border:1px solid var(--rule);background:var(--surface)}}
table{{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;font-size:.88rem}}
th,td{{padding:7px 10px;text-align:right;border-bottom:1px solid var(--rule);white-space:nowrap}}
th{{font-weight:600;color:var(--ink-2)}}
thead th{{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:.72rem;letter-spacing:.06em;text-transform:uppercase;border-bottom:2px solid var(--ink)}}
tbody th[scope=row]{{text-align:left;font-weight:500;color:var(--ink)}}
td.heat{{background:color-mix(in oklab,var(--accent) calc(var(--v)*82%),var(--surface));font-family:"IBM Plex Mono",ui-monospace,monospace;text-align:center}}
td.heat.hi{{color:var(--accent-ink)}}
td.na{{color:var(--muted);text-align:center}}
.grp-start{{border-left:2px solid var(--ink)}}
tr.all td,tr.all th{{font-weight:600;border-bottom:2px solid var(--rule)}}
.legend{{font-size:.8rem;color:var(--muted);font-family:"IBM Plex Mono",ui-monospace,monospace;margin-top:6px}}
.delta{{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:.82rem;white-space:nowrap}}
.delta.good{{color:var(--good);font-weight:600}} .delta.bad{{color:var(--bad);font-weight:600}}
.findings{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px;margin-top:14px}}
.finding{{padding:16px 18px;background:var(--surface);border:1px solid var(--rule)}}
.finding h4{{margin-bottom:6px}}
.notes{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px}}
.note{{padding:14px 16px;border:1px solid var(--rule);background:var(--surface)}}
.note .spec{{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:.74rem;color:var(--muted);margin:4px 0 8px}}
.note p{{font-size:.92rem}}
figure.sample{{margin:16px 0;padding:0}}
figure.sample figcaption{{font-size:.8rem;color:var(--muted);font-family:"IBM Plex Mono",ui-monospace,monospace;margin-bottom:6px}}
pre{{margin:0;padding:12px 14px;background:var(--surface);border:1px solid var(--rule);overflow-x:auto;font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:.8rem;line-height:1.6;white-space:pre-wrap}}
pre[dir=rtl]{{font-family:"IBM Plex Sans Arabic","IBM Plex Sans",sans-serif;font-size:.9rem;text-align:right}}
dl.metrics{{display:grid;grid-template-columns:max-content 1fr;gap:6px 18px;margin:10px 0 0}}
dl.metrics dt{{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:.82rem;color:var(--accent);font-weight:500}}
dl.metrics dd{{margin:0;max-width:70ch}}
code{{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:.86em;background:var(--chip);padding:1px 5px}}
a{{color:var(--accent)}}
@media (max-width:760px){{.bar-row{{grid-template-columns:1fr}}h1{{font-size:2rem}}}}
@media (prefers-reduced-motion: no-preference){{.bar-fill{{transition:width .5s ease}}}}
</style>
<div class="wrap">
<div class="eyebrow">Arabic financial-statement OCR · {len(models)} model runs · 11 pages · hand-verified ground truth</div>
<h1>Qawaim OCR Bench</h1>
<p class="lede">{NARR.get("lede", "Which OCR model can pull the figures out of Saudi financial statements — digital PDFs with Western digits and scanned pages with Arabic-Indic numerals — without breaking the rows?")}</p>
<div class="meta"><span>Aramco FY2024 (PDF pp. 12–16, digital)</span><span>Ma'aden FY2024 (PDF pp. 11–16, scanned)</span><span>319 rows · 943 figures</span><span>Apple M4 Max 36 GB · MLX bf16</span><span>{NARR.get("date", "2026-08-22")}</span></div>

<section class="verdict"><div class="eyebrow">Verdict</div>{NARR.get("verdict", "<p>Pending — queue still running.</p>")}</section>

<h2>Ranking by row recall</h2>
<p class="prose">Row recall = share of the 319 ground-truth data rows whose <em>every</em> figure appears together on one output line or table row — the number that tells you whether a statement can be parsed, not just whether digits were read. Each model shows every variant we measured as a parallel bar: the plain-input benchmark (pages as rendered — the sort key), CLAHE pre-processing, CLAHE + 2× upscale (hosted models), and the arithmetic-verification stage on top where it was run. Under the name: pages that ran to the token cap, wall-clock per page and label recall for the plain run.</p>
{legend_html}
<ol class="bars">{"".join(bars)}</ol>

{abl_section}

<h2>Row recall per statement</h2>
<p class="prose">Aramco is a born-digital PDF with Western digits; Ma'aden is a scan with Arabic-Indic digits and hand-drawn red annotation boxes. Cells are the percentage of that statement's rows that survived intact.</p>
<div class="tablewrap"><table><thead><tr><th></th><th colspan="5" style="text-align:center">Aramco · digital</th><th colspan="6" class="grp-start" style="text-align:center">Ma'aden · scanned</th></tr><tr><th>model</th>{hm_head}</tr></thead><tbody>{"".join(hm_rows)}</tbody></table></div>
<div class="legend">– = no output for that page</div>

{enh_section}

{drill_section}

{decisions_section()}

<h2>What the numbers say</h2>
<div class="findings">{NARR.get("findings", "")}</div>

<h2>Samples</h2>
<p class="prose">Same page, three models — the first rows that carried two or more figures, exactly as produced (tags stripped).</p>
{samples}

<h2>All metrics</h2>
<div class="tablewrap"><table><thead><tr><th>model</th><th>document</th><th>looped</th><th>fig recall</th><th>fig recall (signed)</th><th>row recall</th><th>label recall</th><th>num precision</th><th>CER</th><th>WER</th><th title="share of digits in the Ma'aden output written in Arabic-Indic numerals (source script)">٠-٩ kept</th><th>s/page</th></tr></thead><tbody>{full_rows}</tbody></table></div>
<div class="legend">CER/WER are doc-level and order-sensitive; a model that loops or flips column order scores &gt;1 even when its figures are right — treat them as secondary. “٠-٩ kept” = share of digits in the Ma'aden output written in Arabic-Indic numerals as printed (scoring itself is script-agnostic).</div>

<h2>Digit-script probe</h2>
<p class="prose">The same six amounts rendered in clean synthetic images (Arial, no scan noise) in Western and Arabic-Indic digits, plus one stacked column per script; a pass requires every digit right. It isolates numeral knowledge from layout and scan quality. Caveat: lone large numerals are out-of-distribution for document OCR models, so a low score here with a high Ma'aden figure recall (Mistral) means the model reads the script in context but not in isolation.</p>
<div class="tablewrap"><table><thead><tr><th>model</th><th>Western 0–9</th><th>Arabic-Indic ٠–٩</th></tr></thead><tbody>{probe_rows}</tbody></table></div>

<h2>Model notes</h2>
<div class="notes">{"".join(note_items)}</div>

<h2>Method</h2>
<div class="prose">
<h3>Ground truth</h3><p>The five primary statements of each filing, transcribed into Markdown tables and arithmetically checked (every subtotal and total re-added) — 144 data rows / 576 figures for Aramco, 175 rows / 367 figures for Ma'aden (incl. the non-cash annex). Pages were rendered at 200 dpi (Aramco 1700×2200, Ma'aden 1654×2339; one landscape page) and every model received the same PNGs.</p>
<h3>Metrics</h3>
<dl class="metrics">
<dt>fig recall</dt><dd>Share of ground-truth figures (data-column amounts; note references and header years excluded) found anywhere in the output. Absolute values; Arabic-Indic and Persian digits normalized; <code>(x)</code> and <code>x</code> equal.</dd>
<dt>fig recall (signed)</dt><dd>Same, but <code>(1,234)</code> must come out negative.</dd>
<dt>row recall</dt><dd>Share of data rows whose complete set of figures appears on one output line / <code>&lt;tr&gt;</code>.</dd>
<dt>label recall</dt><dd>Share of Arabic row labels found in the output (fuzzy partial ratio ≥ 85 after normalizing alef/ya/ta-marbuta and stripping diacritics).</dd>
<dt>num precision</dt><dd>Share of all numbers emitted that exist in the ground truth — the hallucination and repetition signal.</dd>
<dt>looped</dt><dd>Pages where generation ran to the token cap (4096 for Markdown/plain-text models, 8192 for HTML/JSON layout models) — in practice always a repetition loop; legitimate pages need 700–3,900 tokens.</dd>
</dl>
<h3>Inference</h3><p>All open models ran on Apple Silicon through <code>mlx-vlm</code> 0.6.15 as bf16 conversions (their native dtype; no quantization). Each model used its own documented prompt and, where its own pipeline documents decoding settings, those settings (dots: T=0.1; LFM2.5-VL: T=0.1/min_p 0.15/rep 1.05; Aya: T=0.3); everything else greedy, seeds fixed. Qari-OCR 0.4 is a LoRA adapter — merged into its Qwen3-VL-4B base before conversion. PaddleOCR-VL ran its full layout + recognition pipeline on CPU (Paddle has no Metal backend). Mistral OCR was called through Mistral's <code>/v1/ocr</code> endpoint with each PNG as an image document. Baseer (Misraj) is not open-weights and was skipped.</p>
<h3>Caveats</h3><p>Two filings, eleven pages — a focused probe, not a broad benchmark; rankings can shift on other layouts. The Ma'aden scans carry hand-drawn red annotation boxes that are part of the real documents and visibly distract some models. MLX ports of the newest architectures (Qwen3.5, dots, GLM-OCR) are community conversions; GLM-OCR's Arabic behaviour was identical on torch, and AIN's failure reproduced on torch at 2 MP. Torch/MPS itself could not be used: above ~2.2 MP the Qwen2-VL vision tower returns NaN logits on MPS (32-bit attention indexing), and it is ~10× slower than MLX.</p>
<h3>Reproduce</h3><p><code>~/Desktop/Projects/DocProcess/ocr_benchmark</code>: <code>prep_pages.py</code> (render pages) → <code>run_all.sh</code> (queue of <code>bench.py --model …</code>) → <code>run_mistral_native.py</code> → <code>digit_probe.py</code> → <code>eval2.py --per-table</code> → <code>make_report.py</code>. Outputs per model in <code>results/&lt;model&gt;/</code> with <code>_timing.jsonl</code> and <code>_meta.json</code>.</p>
</div>
</div>
'''
(BASE / "REPORT.html").write_text(page, encoding="utf-8")
print("REPORT.html written:", len(page), "bytes;", len(models), "models")