import os
import time
from pathlib import Path

import torch
from transformers import AutoProcessor, AutoModelForImageTextToText

MODEL_ID = "zai-org/GLM-OCR"
IMAGES = sorted(Path(os.environ.get("IMG_DIR", "/path/to/DocProcess/ocr_benchmark/images")).glob("*.png"))
OUT_DIR = Path(os.environ.get("OUT_DIR", "/path/to/DocProcess/ocr_benchmark/output/glm"))
PROMPT = "Text Recognition:"

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    processor = AutoProcessor.from_pretrained(MODEL_ID)
    model = AutoModelForImageTextToText.from_pretrained(
        MODEL_ID, torch_dtype=torch.float16, device_map="mps"
    )
    model.eval()

    for img_path in IMAGES:
        out_file = OUT_DIR / f"{img_path.stem}.md"
        if out_file.exists():
            print(f"[glm] {img_path.name}: cached, skipping", flush=True)
            continue
        t0 = time.time()
        messages = [{
            "role": "user",
            "content": [
                {"type": "image", "url": str(img_path)},
                {"type": "text", "text": PROMPT},
            ],
        }]
        inputs = processor.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True,
            return_dict=True, return_tensors="pt"
        ).to(model.device)
        inputs.pop("token_type_ids", None)

        with torch.no_grad():
            generated = model.generate(**inputs, max_new_tokens=8192, do_sample=False)
        trimmed = generated[:, inputs["input_ids"].shape[1]:]
        output = processor.decode(trimmed[0], skip_special_tokens=False)

        secs = time.time() - t0
        out_file.write_text(output, encoding="utf-8")
        print(f"[glm] {img_path.name}: {secs:.1f}s, {len(output)} chars", flush=True)

if __name__ == "__main__":
    main()
