"""dots.mocr ablation loop on the Ma'aden scans: builds page variants, runs the model, scores rows/figures."""
import cv2, numpy as np, sys, json, os, subprocess, time
from pathlib import Path
from PIL import Image, ImageFilter
sys.path.insert(0, "."); import eval2, fitz
B = Path("."); MLX = str(B / "venv_mlx/bin/python")
PDF = "/path/to/DocProcess/Example_files/معادن.pdf"
pages = [f"maaden_p{n}" for n in range(11, 17)]
def gray(p): return cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
def clahe(g, clip=2.0, tile=8): return cv2.createCLAHE(clipLimit=clip, tileGridSize=(tile, tile)).apply(g)
def redfree(p):
    bgr = cv2.imread(str(p)); hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, (0, 70, 60), (12, 255, 255)) | cv2.inRange(hsv, (165, 70, 60), (180, 255, 255))
    return cv2.cvtColor(cv2.inpaint(bgr, cv2.dilate(m, np.ones((3, 3), np.uint8)), 3, cv2.INPAINT_TELEA), cv2.COLOR_BGR2GRAY)
def pad(g, px=60): return cv2.copyMakeBorder(g, px, px, px, px, cv2.BORDER_CONSTANT, value=255)
def unsharp(g): return np.array(Image.fromarray(g).filter(ImageFilter.UnsharpMask(radius=2, percent=120, threshold=3)))
def render(dpi):
    d = fitz.open(PDF); out = {}
    for n in range(11, 17):
        pix = d[n - 1].get_pixmap(dpi=dpi, alpha=False); out[f"maaden_p{n}"] = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    return {k: cv2.cvtColor(v, cv2.COLOR_RGB2GRAY) for k, v in out.items()}
VARIANTS = {
 "gray":            lambda p: gray(p),
 "clahe10":         lambda p: clahe(gray(p), 1.0, 8),
 "clahe30":         lambda p: clahe(gray(p), 3.0, 8),
 "clahe20_t16":     lambda p: clahe(gray(p), 2.0, 16),
 "clahe_pad":       lambda p: pad(clahe(gray(p))),
 "clahe_unsharp":   lambda p: unsharp(clahe(gray(p))),
 "clahe_redfree_pad": lambda p: pad(clahe(redfree(p))),
}
ENV_VARIANTS = {   # (page variant to reuse, env overrides)
 "clahe_T0":        ("clahe", {"BENCH_TEMP": "0.0"}),
 "clahe_promptocr": ("clahe", {"BENCH_PROMPT_FILE": str(B / "_tmp/prompt_ocr.txt")}),
}
(B / "_tmp").mkdir(exist_ok=True); (B / "_tmp/prompt_ocr.txt").write_text("Extract the text content from this image.")
def build(name, fn):
    d = B / "pages_abl" / name; d.mkdir(parents=True, exist_ok=True)
    for pg in pages:
        out = d / f"{pg}.png"
        if not out.exists(): cv2.imwrite(str(out), fn(B / "pages" / f"{pg}.png"))
    return d
# 150-dpi render variant (+CLAHE)
d150 = B / "pages_abl" / "dpi150_clahe"; d150.mkdir(parents=True, exist_ok=True)
if not all((d150 / f"{pg}.png").exists() for pg in pages):
    for pg, g in render(150).items(): cv2.imwrite(str(d150 / f"{pg}.png"), clahe(g))
GT = eval2.parse_gt(open("maaden_main_tables.md").read())
def score(d):
    tot = {"rows_hit":0,"rows_tot":0,"fig_hit":0,"fig_tot":0}
    for ti, tb in enumerate(GT, 1):
        fs = [Path(d) / f"{p}.md" for p in eval2.TABLE_PAGES["maaden"][ti]]
        if not all(f.exists() for f in fs): return None
        blob = "\n".join(eval2.truncate_loops("\n".join(eval2.lines_of(eval2.extract_text(f.read_text(errors="replace")))))[0] for f in fs)
        c = eval2.score_tables([tb], blob)
        for k in tot: tot[k] += c[k]
    return tot
def run(name, pages_dir, env=None):
    out = B / "results_abl" / f"dots_{name}"
    e = dict(os.environ, PAGES_DIR=str(pages_dir), TOKENIZERS_PARALLELISM="false", MLX_MEM_LIMIT_GB="22", **(env or {}))
    done = all((out / f"{pg}.md").exists() and (out / f"{pg}.md").stat().st_size > 100 for pg in pages)
    if not done and out.exists():                       # partial run from before a stop -> redo cleanly
        import shutil; shutil.rmtree(out)
    t0 = time.time(); done or subprocess.run([MLX, "bench.py", "--model", "dots_mocr", "--out", str(out)], env=e, stdout=open(f"logs/abl_dots_{name}.log", "a"), stderr=subprocess.STDOUT)
    t = score(out); secs = time.time() - t0
    line = f"{name:<20} rows {t['rows_hit']:>3}/{t['rows_tot']}  figs {t['fig_hit']:>3}/{t['fig_tot']}  ({secs/60:.0f} min)" if t else f"{name}: scoring failed"
    print(line, flush=True); open("logs/abl_dots_summary.log", "a").write(line + "\n")
# baselines already on disk
for name, d in (("plain", "results/dots_mocr"), ("clahe", "results_enh/dots_mocr"), ("clahe_redfree", "results_exp/dots_mocr_redfree")):
    t = score(d); print(f"{name:<20} rows {t['rows_hit']:>3}/{t['rows_tot']}  figs {t['fig_hit']:>3}/{t['fig_tot']}  (baseline)", flush=True)
run("dpi150_clahe", d150)
for name, fn in VARIANTS.items(): run(name, build(name, fn))
for name, (base, env) in ENV_VARIANTS.items(): run(name, B / "pages_enh_clahe", env)   # CLAHE pages (all 11; Ma'aden subset scored)
print("ABLATION DONE", flush=True)
