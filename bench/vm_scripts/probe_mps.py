"""Isolate the Qwen2-VL NaN: dtype (bf16 vs fp16) x image size (full 3.7MP vs 2MP cap) on MPS."""
import time, torch, os
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
from transformers import AutoProcessor, Qwen2VLForConditionalGeneration
from qwen_vl_utils import process_vision_info
mid = "NAMAA-Space/Qari-OCR-v0.3-VL-2B-Instruct"
img = "/path/to/DocProcess/ocr_benchmark/pages/aramco_p13.png"
for dtype, maxpix in [(torch.bfloat16, 2_000_000), (torch.float16, None), (torch.bfloat16, None)]:
    model = Qwen2VLForConditionalGeneration.from_pretrained(mid, torch_dtype=dtype, device_map="mps").eval()
    proc = AutoProcessor.from_pretrained(mid, **({"max_pixels": maxpix} if maxpix else {}))
    msgs = [{"role": "user", "content": [{"type": "image", "image": f"file://{img}"}, {"type": "text", "text": "Read this page."}]}]
    text = proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    ii, vi = process_vision_info(msgs)
    inputs = proc(text=[text], images=ii, videos=vi, padding=True, return_tensors="pt").to("mps")
    t0 = time.time()
    with torch.inference_mode():
        lg = model(**inputs).logits[0, -1].float()
    tf = time.time() - t0
    with torch.inference_mode():
        g = model.generate(**inputs, max_new_tokens=24, do_sample=False)
    gen = proc.batch_decode(g[:, inputs.input_ids.shape[1]:], skip_special_tokens=True)[0]
    print(f"dtype={str(dtype)[6:]:<9} maxpix={maxpix} seq={inputs.input_ids.shape[1]} nan={torch.isnan(lg).any().item()} "
          f"prefill={tf:.1f}s gen24={time.time()-t0-tf:.1f}s  -> {gen[:100]!r}", flush=True)
    del model; torch.mps.empty_cache()
