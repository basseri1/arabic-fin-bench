"""Round 2 dots.mocr ablations (Ma'aden): ink removal (red+blue signatures) and table-region crops from three
layout detectors (dots self-layout, surya layout2, PP-DocLayoutV2) plus a fixed-margin crop. Waits for round 1."""
import cv2, numpy as np, sys, json, os, subprocess, time
from pathlib import Path
sys.path.insert(0, "."); import eval2
B = Path("."); MLX = str(B / "venv_mlx/bin/python")
pages = [f"maaden_p{n}" for n in range(11, 17)]
def gray(p): return cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
def clahe(g, clip=2.0, tile=8): return cv2.createCLAHE(clipLimit=clip, tileGridSize=(tile, tile)).apply(g)
def inkfree(p):
    """Remove red annotations and blue-ink signatures; black print underneath is untouched (not in the colour mask)."""
    bgr = cv2.imread(str(p)); hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    red = cv2.inRange(hsv, (0, 70, 60), (12, 255, 255)) | cv2.inRange(hsv, (165, 70, 60), (180, 255, 255))
    blue = cv2.inRange(hsv, (95, 60, 40), (135, 255, 255))
    m = cv2.dilate(red | blue, np.ones((3, 3), np.uint8))
    return cv2.cvtColor(cv2.inpaint(bgr, m, 3, cv2.INPAINT_TELEA), cv2.COLOR_BGR2GRAY)
def dots_blocks(pg):
    raw = Path(f"results_enh/dots_mocr/{pg}.md").read_text()
    bl = json.loads(raw[raw.index("["):raw.rindex("]") + 1]); out = []
    for b in bl:
        c = b.get("category", ""); l = c.lower()
        lab = "table" if "table" in l else "header" if "page-header" in l else "footer" if "page-footer" in l else "picture" if "picture" in l else "text" if c in ("Text", "Section-header", "Caption", "List-item", "Footnote", "Title") else "other"
        out.append({"label": lab, "raw": c, "bbox": b["bbox"]})
    return out
def crop_box(blocks, W, H, m=30):
    tables = [b for b in blocks if b["label"] == "table"]
    if not tables: return None
    top = min(b["bbox"][1] for b in tables)
    cy = lambda b: (b["bbox"][1] + b["bbox"][3]) / 2
    pics = [b for b in blocks if b["label"] == "picture" and cy(b) > H * 0.5]
    cut = min(cy(b) for b in pics) if pics else H * 0.97
    cands = [b for b in blocks if b["label"] in ("table", "text") and cy(b) >= top and cy(b) < cut]
    bottom = max(b["bbox"][3] for b in cands)
    return (int(max(0, top - m)), int(min(H, bottom + m)))
def build(name, fn):
    d = B / "pages_abl" / name; d.mkdir(parents=True, exist_ok=True)
    for pg in pages:
        out = d / f"{pg}.png"
        if not out.exists(): cv2.imwrite(str(out), fn(pg))
    return d
def cropper(det, base=None):
    def fn(pg):
        g = (base or (lambda pg: gray(B / "pages" / f"{pg}.png")))(pg); H, W = g.shape
        blocks = dots_blocks(pg) if det == "dots" else json.loads(Path(f"layouts/{det}/{pg}.json").read_text())
        box = crop_box(blocks, W, H)
        if box is None: print(f"  [{det}] {pg}: no table found -> full page"); return clahe(g)
        y0, y1 = box; print(f"  [{det}] {pg}: crop rows {y0}-{y1} of {H}")
        return clahe(g[y0:y1, :])
    return fn
def fixed(pg):
    g = gray(B / "pages" / f"{pg}.png"); H = g.shape[0]
    return clahe(g[int(H * 0.11):int(H * 0.86), :])
GT = eval2.parse_gt(open("maaden_main_tables.md").read())
def score(d):
    tot = {"rows_hit": 0, "rows_tot": 0, "fig_hit": 0, "fig_tot": 0}
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
# wait for detectors and for round 1 to release the GPU
while not all(Path(f"layouts/{d}/{pg}.json").exists() for d in ("surya", "pp") for pg in pages): time.sleep(30)
print("layouts ready", flush=True)
VARS = [("inkfree", lambda pg: clahe(inkfree(B / "pages" / f"{pg}.png"))),
        ("crop_dots", cropper("dots")), ("crop_surya", cropper("surya")), ("crop_pp", cropper("pp")), ("crop_fixed", fixed),
        ("crop_dots_inkfree", cropper("dots", base=lambda pg: inkfree(B / "pages" / f"{pg}.png"))),
        ("crop_pp_inkfree", cropper("pp", base=lambda pg: inkfree(B / "pages" / f"{pg}.png")))]
dirs = [(n, build(n, fn)) for n, fn in VARS]
while "ABLATION DONE" not in Path("logs/abl_dots.log").read_text(): time.sleep(60)
print("round 1 finished -> round 2", flush=True)
for n, d in dirs: run(n, d)
print("ABLATION2 DONE", flush=True)
