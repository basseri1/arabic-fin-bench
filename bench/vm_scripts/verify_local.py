"""Local verification service (datalab-style) for Arabic financial statements with dots.mocr / Chandra-2.
Given a PDF (or an existing results dir), returns every table row with per-figure confidence and reasons.

  python verify_local.py --pdf file.pdf [--pages 11-16] [--model dots_mocr] [--second chandra2] [--hires] --out result.json
  python verify_local.py --from-results results_pipe/dots_mocr_clahe_bm_ver --pages-list maaden_p11,... [--second-results results_enh/chandra2] --out result.json

Confidence per figure (GT-free):  anchored = inside a satisfied sum relationship; broken_sum = inside a broken one;
agree/disagree = second independent reading has / lacks the same value; low_token_prob = min digit-token probability
below threshold (when the run captured log-probs, BENCH_LOGPROBS=1); repaired = changed by the arithmetic verifier;
page_retried = structure check re-ran the page.  Level: LOW if broken_sum | disagree | low_token_prob | repaired;
HIGH if anchored and (agree or p_min high); else MEDIUM."""
import argparse, json, math, os, re, subprocess, sys, shutil
from pathlib import Path
from collections import Counter
sys.path.insert(0, str(Path(__file__).parent)); import eval2, validate, post_dots, prep_lib, structure_check, confidence as C
B = Path(__file__).parent; MLX = str(B / "venv_mlx/bin/python") if os.environ.get("BENCH_BACKEND", "mlx") == "mlx" else sys.executable
RUNNER = str(B / ("bench.py" if os.environ.get("BENCH_BACKEND", "mlx") == "mlx" else "bench_vllm.py")); TAU_LOW = float(os.environ.get("TAU_LOW", "0.90"))
def render(pdf, pages, out, hires=False):
    import fitz, cv2, numpy as np
    d = fitz.open(pdf); out.mkdir(parents=True, exist_ok=True); stems = []
    for n in pages:
        pg = d[n - 1]; landscape = pg.rect.width > pg.rect.height; dpi = 600 if (hires and not landscape) else 200
        pix = pg.get_pixmap(dpi=dpi, alpha=False); arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        g = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY) if pix.n == 3 else arr[:, :, 0]
        stem = f"{Path(pdf).stem}_p{n:02d}"; cv2.imwrite(str(out / f"{stem}.png"), prep_lib.clahe(g)); stems.append(stem)
    return stems
def ocr(model, pages_dir, res, logprobs=True, seed=None):
    env = dict(os.environ, PAGES_DIR=str(pages_dir), TOKENIZERS_PARALLELISM="false", MLX_MEM_LIMIT_GB=os.environ.get("MLX_MEM_LIMIT_GB", "22"))
    if logprobs: env["BENCH_LOGPROBS"] = "1"
    if seed is not None: env["BENCH_SEED"] = str(seed)
    subprocess.run([MLX, RUNNER, "--model", model, "--out", str(res)], env=env, check=False)
def retry_structure(model, pages_dir, res, stems, max_tries=3):
    retried = {}
    for stem in stems:
        f = res / f"{stem}.md"
        if not f.exists(): continue
        r0 = structure_check.check_text(structure_check.page_text(f))
        if not r0["flags"]: continue
        for seed in range(1, max_tries + 1):
            tp = B / "_tmp" / f"vl_retry_{stem}"; tp.mkdir(parents=True, exist_ok=True); shutil.copy(pages_dir / f"{stem}.png", tp / f"{stem}.png")
            to = B / "_tmp" / f"vl_retry_out_{stem}_s{seed}"; ocr(model, tp, to, seed=seed)
            g = to / f"{stem}.md"
            if g.exists() and not structure_check.check_text(structure_check.page_text(g))["flags"]:
                shutil.copy(g, f); tj = to / f"{stem}.tok.json"
                if tj.exists(): shutil.copy(tj, res / f"{stem}.tok.json")
                retried[stem] = dict(flags=r0["flags"], seed=seed); break
        else: retried[stem] = dict(flags=r0["flags"], seed=None)
    return retried
def rows_with_confidence(res_dir, stems, second_dir=None, fixes=None, retried=None):
    fixes = fixes or []; retried = retried or {}
    fixed_vals = {(f["page"], abs(float(f["to"]))): abs(float(f["from"])) for f in fixes}
    anc, sus = C.anchors(res_dir, stems)
    sec = Counter()
    if second_dir:
        for s in stems: sec.update(v for v, _, _ in C.figures_in(C.page_text(second_dir, s)))
    out = []
    for stem in stems:
        text = eval2.extract_text(C.page_text(res_dir, stem)); tc = C.token_conf(res_dir, stem)
        raw = tc[0] if tc else None
        for ti, rows in enumerate(validate.parse_tables(text)):
            for r in rows:
                label = next((c for c in r if validate.AR_LETTERS.search(c)), "")
                cells = []
                for c in r:
                    v = validate.cell_value(c)
                    if v in (None, 0.0) or (abs(v) < 1000 and v == int(v)): continue
                    av = abs(v); reasons = []
                    if av in anc: reasons.append("anchored")
                    if av in sus: reasons.append("broken_sum")
                    if second_dir: reasons.append("agree" if sec[av] > 0 else "disagree")
                    p_min = None
                    if tc and raw is not None:
                        i = raw.find(c.strip())
                        cf = tc[1](i, i + len(c.strip())) if i >= 0 else None
                        if cf: p_min = cf[1]; reasons.append("low_token_prob") if cf[1] < TAU_LOW else None
                    if (stem, av) in fixed_vals: reasons.append(f"repaired_from_{fixed_vals[(stem, av)]:.0f}")
                    if stem in retried: reasons.append("page_retried")
                    low = "broken_sum" in reasons or "low_token_prob" in reasons or any(x.startswith("repaired") for x in reasons) or ("disagree" in reasons and "anchored" not in reasons)
                    if "disagree" in reasons and "anchored" in reasons and not low: reasons.append("anchored_but_second_reader_differs")
                    level = "LOW" if low else "HIGH" if ("anchored" in reasons and "disagree" not in reasons and ("agree" in reasons or (p_min is not None and p_min >= TAU_LOW) or not second_dir)) else "MEDIUM"
                    cells.append(dict(text=c.strip(), value=v, confidence=level, p_min=p_min, reasons=reasons))
                if cells: out.append(dict(page=stem, table=ti, label=label, figures=cells))
    return out
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--pdf"); ap.add_argument("--pages", default=""); ap.add_argument("--model", default="dots_mocr"); ap.add_argument("--second", default=None)
    ap.add_argument("--hires", action="store_true"); ap.add_argument("--from-results"); ap.add_argument("--pages-list", default=""); ap.add_argument("--second-results"); ap.add_argument("--out", default="verify_result.json")
    a = ap.parse_args(); fixes = []; retried = {}
    if a.from_results:
        res = Path(a.from_results); stems = a.pages_list.split(",") if a.pages_list else sorted(p.stem for p in res.glob("*.md")); second = a.second_results
    else:
        lo, hi = (int(x) for x in a.pages.split("-")) if "-" in a.pages else (int(a.pages), int(a.pages))
        work = B / "_tmp" / f"verify_{Path(a.pdf).stem}"; pages_dir = work / "pages"; stems = render(a.pdf, range(lo, hi + 1), pages_dir, a.hires)
        res = work / a.model; ocr(a.model, pages_dir, res); retried = retry_structure(a.model, pages_dir, res, stems)
        if a.model.startswith("dots"):
            bm = Path(str(res) + "_bm"); subprocess.run([sys.executable, str(B / "post_dots.py"), str(res), str(bm)], check=True)
            for s in stems:
                tj = res / f"{s}.tok.json"
                if tj.exists(): shutil.copy(tj, bm / f"{s}.tok.json")
            res = bm
        rep, _ = validate.validate_doc(str(res), stems); fixes = rep["fixes"]; ver = Path(str(res) + "_ver"); validate.apply_fixes(str(res), str(ver), stems, rep)
        for s in stems:
            tj = res / f"{s}.tok.json"
            if tj.exists(): shutil.copy(tj, ver / f"{s}.tok.json")
        res = ver; second = None
        if a.second:
            sres = work / a.second; ocr(a.second, pages_dir, sres, logprobs=False); second = str(sres)
    rows = rows_with_confidence(str(res), stems, second, fixes, retried)
    n = sum(len(r["figures"]) for r in rows); lv = Counter(c["confidence"] for r in rows for c in r["figures"])
    json.dump(dict(source=a.pdf or a.from_results, pages=stems, figures=n, levels=dict(lv), fixes=fixes, retried=retried, rows=rows), open(a.out, "w"), ensure_ascii=False, indent=1)
    print(f"{n} figures: {dict(lv)} -> {a.out}")
    for r in rows:
        for c in r["figures"]:
            if c["confidence"] == "LOW": print(f"  LOW  {r['page']} {r['label'][:40]!r} {c['text']}  {c['reasons']}")
