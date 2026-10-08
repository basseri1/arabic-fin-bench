import argparse, json, os, time
from pathlib import Path

import torch
from PIL import Image
from transformers import AutoProcessor, AutoModelForImageTextToText, Qwen2VLForConditionalGeneration
from qwen_vl_utils import process_vision_info

PROMPTS = {
    "qari": (
        "Below is the image of one page of a document. Extract all text and tables. "
        "Return the plain text representation of this document as if you were reading it naturally, "
        "preserving table structure in Markdown format. Do not hallucinate."
    ),
    "ain": (
        "Extract all text and tables from this Arabic document page. "
        "Preserve the table structure using Markdown. Output only the extracted content."
    ),
    "glm": None,
}

def load_model(model_id, arch):
    cls = Qwen2VLForConditionalGeneration if arch == "qwen2vl" else AutoModelForImageTextToText
    dtype = torch.float16
    model = cls.from_pretrained(model_id, torch_dtype=dtype, device_map="mps")
    processor = AutoProcessor.from_pretrained(model_id, max_pixels=2_000_000)
    model.eval()
    return model, processor

def run(model_id, arch, prompt_key, out_dir):
    out_dir = Path(os.environ.get("OUT_DIR", out_dir)); out_dir.mkdir(parents=True, exist_ok=True)
    images = sorted(Path(os.environ.get("IMG_DIR", "/path/to/DocProcess/ocr_benchmark/images")).glob("*.png"))
    prompt = PROMPTS[prompt_key]
    model, processor = load_model(model_id, arch)

    for img_path in images:
        out_file = out_dir / f"{img_path.stem}.md"
        if out_file.exists():
            print(f"[{prompt_key}] {img_path.name}: cached, skipping", flush=True)
            continue
        t0 = time.time()
        messages = [{
            "role": "user",
            "content": [
                {"type": "image", "image": f"file://{img_path}"},
                {"type": "text", "text": prompt},
            ],
        }]
        text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = processor(text=[text], images=image_inputs, videos=video_inputs, padding=True, return_tensors="pt").to("mps")

        with torch.no_grad():
            generated = model.generate(**inputs, max_new_tokens=4096, do_sample=False)
        trimmed = [out[len(inp):] for inp, out in zip(inputs.input_ids, generated)]
        output = processor.batch_decode(trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]

        secs = time.time() - t0
        out_file.write_text(output, encoding="utf-8")
        print(f"[{prompt_key}] {img_path.name}: {secs:.1f}s, {len(output)} chars", flush=True)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-id", required=True)
    ap.add_argument("--arch", default="auto", choices=["auto", "qwen2vl"])
    ap.add_argument("--prompt", required=True, choices=list(PROMPTS))
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    run(a.model_id, a.arch, a.prompt, a.out_dir)
