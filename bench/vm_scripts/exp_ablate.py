"""Pre-processing ablation on the Ma'aden scans (CLAHE base + one extra technique each), scored with Mistral OCR."""
import cv2, numpy as np, sys, json, time
from pathlib import Path
sys.path.insert(0, "."); import eval2, run_mistral_native as rm
BASE = Path("."); pages = sorted(BASE.glob("pages/maaden_*.png"))
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
def deskew(g):
    thr = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thr > 0))
    ang = cv2.minAreaRect(coords[:, ::-1].astype(np.float32))[-1]
    ang = -(90 - ang) if ang > 45 else -ang
    if abs(ang) < 0.2 or abs(ang) > 5: return g, 0.0
    h, w = g.shape; M = cv2.getRotationMatrix2D((w / 2, h / 2), -ang, 1.0)
    return cv2.warpAffine(g, M, (w, h), flags=cv2.INTER_CUBIC, borderValue=255), ang
def red_removal(bgr):
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    m1 = cv2.inRange(hsv, (0, 70, 60), (12, 255, 255)); m2 = cv2.inRange(hsv, (165, 70, 60), (180, 255, 255))
    m = cv2.dilate(m1 | m2, np.ones((3, 3), np.uint8))
    return cv2.inpaint(bgr, m, 3, cv2.INPAINT_TELEA), int(m.sum() / 255)
variants = {"clahe": {}, "clahe_redfree": {}, "clahe_deskew": {}, "clahe_dilate": {}, "clahe_nlm": {}, "clahe_sauvola": {}}
for p in pages:
    bgr = cv2.imread(str(p)); g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    rf, npx = red_removal(bgr); grf = cv2.cvtColor(rf, cv2.COLOR_BGR2GRAY)
    base = clahe.apply(g)
    out = {"clahe": base, "clahe_redfree": clahe.apply(grf)}
    d, ang = deskew(base); out["clahe_deskew"] = d
    out["clahe_dilate"] = cv2.erode(base, np.ones((2, 2), np.uint8))          # erode on white-bg = thicken dark strokes
    out["clahe_nlm"] = cv2.fastNlMeansDenoising(base, None, 7, 7, 21)
    try:
        from skimage.filters import threshold_sauvola
        t = threshold_sauvola(base, window_size=31); out["clahe_sauvola"] = (base > t).astype(np.uint8) * 255
    except Exception:
        out["clahe_sauvola"] = cv2.adaptiveThreshold(base, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10)
    for k, im in out.items():
        d = BASE / "pages_exp" / f"abl_{k}"; d.mkdir(parents=True, exist_ok=True); cv2.imwrite(str(d / p.name), im)
    print(f"{p.name}: red px removed {npx}, deskew {ang:+.2f}°", flush=True)
GT = eval2.parse_gt(open("maaden_main_tables.md").read())
def score(d):
    tot = {"rows_hit":0,"rows_tot":0,"fig_hit":0,"fig_tot":0}
    for ti, tb in enumerate(GT, 1):
        blob = "\n".join("\n".join(eval2.lines_of(eval2.extract_text(open(f"{d}/{p}.md").read()))) for p in eval2.TABLE_PAGES["maaden"][ti])
        c = eval2.score_tables([tb], blob)
        for k in tot: tot[k] += c[k]
    return tot
for k in variants:
    out = BASE / "results_exp" / f"mistral_abl_{k}"; out.mkdir(parents=True, exist_ok=True)
    for p in sorted((BASE / "pages_exp" / f"abl_{k}").glob("*.png")):
        f = out / f"{p.stem}.md"
        if f.exists() and f.stat().st_size: continue
        text, raw = rm.ocr_page(p); f.write_text(text)
    t = score(out); print(f"  Mistral | {k:<14} Ma'aden rows {t['rows_hit']:>3}/{t['rows_tot']}  figs {t['fig_hit']:>3}/{t['fig_tot']}", flush=True)
