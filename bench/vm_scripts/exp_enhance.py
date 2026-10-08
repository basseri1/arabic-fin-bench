"""Image-enhancement variants of the Ma'aden scans: CLAHE, 2x Lanczos upscale + unsharp mask, and both."""
import cv2, numpy as np
from pathlib import Path
from PIL import Image, ImageFilter
BASE = Path(__file__).resolve().parent
pages = sorted((BASE / "pages").glob("maaden_*.png"))
outs = {k: BASE / "pages_exp" / k for k in ("clahe", "up2x", "clahe_up2x")}
for d in outs.values(): d.mkdir(parents=True, exist_ok=True)
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
for p in pages:
    g = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
    c = clahe.apply(g)
    cv2.imwrite(str(outs["clahe"] / p.name), c)
    im = Image.open(p).convert("RGB"); up = im.resize((im.width * 2, im.height * 2), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=2, percent=120, threshold=3))
    up.save(outs["up2x"] / p.name)
    cu = Image.fromarray(c).resize((g.shape[1] * 2, g.shape[0] * 2), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=2, percent=120, threshold=3))
    cu.save(outs["clahe_up2x"] / p.name)
    print(p.name, "->", c.shape, up.size)
