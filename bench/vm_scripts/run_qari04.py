import os
import time
from pathlib import Path

import torch
from transformers import AutoProcessor, Qwen3VLForConditionalGeneration
from peft import PeftModel
from PIL import Image

BASE = "unsloth/Qwen3-VL-4B-Instruct"
ADAPTER = "NAMAA-Space/Qari-OCR-0.4.0-VL-4B-Instruct"
IMAGES = sorted(Path(os.environ.get("IMG_DIR", "/path/to/DocProcess/ocr_benchmark/images")).glob("*.png"))
OUT_DIR = Path(os.environ.get("OUT_DIR", "/path/to/DocProcess/ocr_benchmark/output/qari04"))
PROMPT = "Free OCR."

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    processor = AutoProcessor.from_pretrained(ADAPTER)
    model = Qwen3VLForConditionalGeneration.from_pretrained(
        BASE, torch_dtype=torch.float16, device_map="mps"
    )
    model = PeftModel.from_pretrained(model, ADAPTER)
    model.eval()

    for img_path in IMAGES:
        out_file = OUT_DIR / f"{img_path.stem}.md"
        if out_file.exists():
            print(f"[qari04] {img_path.name}: cached, skipping", flush=True)
            continue
        t0 = time.time()
        messages = [{
            "role": "user",
            "content": [
                {"type": "image", "image": Image.open(img_path)},
                {"type": "text", "text": PROMPT},
            ],
        }]
        inputs = processor.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True,
            return_dict=True, return_tensors="pt"
        ).to(model.device)

        with torch.no_grad():
            generated = model.generate(**inputs, max_new_tokens=2048, do_sample=False)
        trimmed = generated[:, inputs.input_ids.shape[1]:]
        output = processor.batch_decode(trimmed, skip_special_tokens=True,
                                        clean_up_tokenization_spaces=False)[0]

        secs = time.time() - t0
        out_file.write_text(output, encoding="utf-8")
        print(f"[qari04] {img_path.name}: {secs:.1f}s, {len(output)} chars", flush=True)

if __name__ == "__main__":
    main()
