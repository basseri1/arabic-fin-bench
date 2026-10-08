"""Merge the Qari-OCR 0.4 LoRA adapter into its Qwen3-VL-4B base (CPU, bf16) and save a plain HF
checkpoint, so it can be converted to MLX like any other model."""
import torch
from pathlib import Path
from transformers import AutoProcessor, Qwen3VLForConditionalGeneration
from peft import PeftModel
BASE, ADAPTER = "unsloth/Qwen3-VL-4B-Instruct", "NAMAA-Space/Qari-OCR-0.4.0-VL-4B-Instruct"
OUT = Path(__file__).resolve().parent / "models" / "Qari04-merged-hf"
model = Qwen3VLForConditionalGeneration.from_pretrained(BASE, torch_dtype=torch.bfloat16, device_map="cpu")
model = PeftModel.from_pretrained(model, ADAPTER).merge_and_unload()
model.save_pretrained(OUT, safe_serialization=True)
AutoProcessor.from_pretrained(ADAPTER).save_pretrained(OUT)   # adapter repo ships the processor/tokenizer
print("merged ->", OUT)
