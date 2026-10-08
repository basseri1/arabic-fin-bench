"""PaddleOCR-VL-1.6 through its vendor pipeline (PaddleOCRVL, pipeline_version v1.6: layout detection, then the 0.9B VLM
reads each block), the VLM served by vLLM on the same GPU (vl_rec_backend="vllm-server"). Vendor defaults otherwise.
Writes <out>/<page>.md (the pipeline Markdown), _timing.jsonl and _meta.json.
usage: PAGES_DIR=pages32/plain ~/venv_pvl/bin/python run_paddleocr_vl.py --out results32/paddleocr_vl16_plain [--only a,b]
"""
import argparse
import json
import os
import time
from pathlib import Path

os.environ.setdefault("PADDLE_PDX_MODEL_SOURCE", "huggingface")
ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--only", default="")
ap.add_argument("--server", default="http://localhost:8118/v1")
ap.add_argument("--concurrency", type=int, default=16)
a = ap.parse_args()

import paddle  # noqa: E402
import paddleocr  # noqa: E402
from paddleocr import PaddleOCRVL  # noqa: E402

out = Path(a.out)
out.mkdir(parents=True, exist_ok=True)
pages = sorted(Path(os.environ.get("PAGES_DIR", "pages32/plain")).glob("*.png"))
if a.only:
    keep = set(a.only.split(","))
    pages = [p for p in pages if p.stem in keep]
pages = [p for p in pages if not ((out / f"{p.stem}.md").exists() and (out / f"{p.stem}.md").stat().st_size > 0)]
(out / "_meta.json").write_text(json.dumps({
    "model": "paddleocr_vl16", "checkpoint": "PaddlePaddle/PaddleOCR-VL-1.6",
    "pipeline": f"paddleocr {paddleocr.__version__} PaddleOCRVL(pipeline_version=v1.6), paddle {paddle.__version__}",
    "vl_rec_backend": "vllm-server", "server": a.server, "date": time.strftime("%F")}, indent=1))
pipe = PaddleOCRVL(pipeline_version="v1.6", vl_rec_backend="vllm-server", vl_rec_server_url=a.server,
                   vl_rec_api_model_name="PaddleOCR-VL-1.6-0.9B", vl_rec_max_concurrency=a.concurrency)
t0 = last = time.time()
with open(out / "_timing.jsonl", "a") as tl:
    for p, res in zip(pages, pipe.predict([str(p) for p in pages])):
        md = res.markdown
        text = md.get("markdown_texts", "") if isinstance(md, dict) else str(md)
        (out / f"{p.stem}.md").write_text(text, encoding="utf-8")
        now = time.time()
        tl.write(json.dumps({"page": p.stem, "seconds": round(now - last, 2), "chars": len(text)}) + "\n")
        last = now
        print(f"[paddleocr_vl16] {p.name}: {len(text)} chars", flush=True)
print(f"[paddleocr_vl16] DONE {len(pages)} pages in {time.time() - t0:.0f}s", flush=True)
