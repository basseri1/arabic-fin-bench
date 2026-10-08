import os
import time
from pathlib import Path

from paddleocr import PaddleOCRVL

IMAGES = sorted(Path(os.environ.get("IMG_DIR", "/path/to/DocProcess/ocr_benchmark/images")).glob("*.png"))
OUT_DIR = Path(os.environ.get("OUT_DIR", "/path/to/DocProcess/ocr_benchmark/output/paddle"))

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pipeline = PaddleOCRVL()

    for img_path in IMAGES:
        marker = OUT_DIR / f"{img_path.stem}_done"
        if marker.exists():
            print(f"[paddle] {img_path.name}: cached, skipping", flush=True)
            continue
        t0 = time.time()
        output = pipeline.predict(str(img_path))
        for res in output:
            res.save_to_markdown(save_path=str(OUT_DIR))
        (OUT_DIR / f"{img_path.stem}_done").touch()
        secs = time.time() - t0
        print(f"[paddle] {img_path.name}: {secs:.1f}s", flush=True)

if __name__ == "__main__":
    main()
