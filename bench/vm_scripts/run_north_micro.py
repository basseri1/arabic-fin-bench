#!/usr/bin/env python
"""North Micro Vision Instruct (CohereLabs, 2.4B, Apache-2.0) with Transformers (no vLLM support yet), on this VM's GPU.
Same prompt as the other general VLMs, greedy decoding by default (--temperature > 0 gives the model card's
Transformers sampling: top-p 0.8, top-k 20, fixed seed), 8192-token cap, the benchmark's loop detector; pages are
batched (left padding), sorted by size. Outputs: <out>/<page>.md, _timing.jsonl (per-page secs = batch wall-clock
split evenly), _meta.json.
Usage: PAGES_DIR=pages32/plain python run_north_micro.py --out results32/north_micro_plain [--batch 16] [--device cuda]"""
import argparse, json, os, sys, time
from pathlib import Path
import torch
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor, StoppingCriteria, StoppingCriteriaList

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
from bench import looping          # same repetition rule as the vLLM runs
MODEL = os.path.expanduser(os.environ.get("NM_MODEL", "~/models/NorthMicroVision"))   # NM_MODEL selects a checkpoint directory
REVISION = os.environ.get("NM_REVISION", "46b719694e3bad142f3e931774f4622f1024009e")
PROMPT = ("Extract all text and tables from this Arabic document page. "
          "Preserve the table structure using Markdown. Output only the extracted content.")


class LoopStop(StoppingCriteria):
    """Per-sequence stop when the generated text starts repeating (checked every 64 tokens)."""
    def __init__(self, tok, start):
        self.tok, self.start, self.stopped = tok, start, None
    def __call__(self, input_ids, scores, **kw):
        if self.stopped is None:
            self.stopped = torch.zeros(input_ids.shape[0], dtype=torch.bool, device=input_ids.device)
        n = input_ids.shape[1] - self.start
        if n % 64 == 0 and n > 0:
            for i in range(input_ids.shape[0]):
                if not self.stopped[i] and looping(self.tok.decode(input_ids[i, self.start:], skip_special_tokens=True)):
                    self.stopped[i] = True
        return self.stopped.clone()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True); ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--device", default="cuda"); ap.add_argument("--max-new-tokens", type=int, default=8192)
    ap.add_argument("--only", default=""); ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--top-p", type=float, default=0.8); ap.add_argument("--top-k", type=int, default=20)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    sampling = dict(do_sample=True, temperature=a.temperature, top_p=a.top_p, top_k=a.top_k) if a.temperature > 0 else dict(do_sample=False)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    pages = sorted(Path(os.environ.get("PAGES_DIR", BASE / "pages")).glob("*.png"))
    if a.only:
        keep = set(a.only.split(",")); pages = [p for p in pages if p.stem in keep]
    todo = [p for p in pages if not ((out / f"{p.stem}.md").exists() and (out / f"{p.stem}.md").stat().st_size > 0)]
    todo.sort(key=lambda p: Image.open(p).size[0] * Image.open(p).size[1])
    import transformers
    (out / "_meta.json").write_text(json.dumps({"model": "north_micro", "backend": f"transformers {transformers.__version__}",
        "checkpoint": "CohereLabs/North-Micro-Vision-Instruct", "revision": REVISION, "model_dir": MODEL, "prompt": PROMPT, "decoding": sampling, "seed": a.seed,
        "max_new_tokens": a.max_new_tokens, "batch": a.batch, "date": time.strftime("%F")}, indent=1))
    proc = AutoProcessor.from_pretrained(MODEL)
    proc.tokenizer.padding_side = "left"
    dtype = torch.bfloat16 if a.device == "cuda" else torch.float32
    model = AutoModelForImageTextToText.from_pretrained(MODEL, dtype=dtype, attn_implementation="sdpa").to(a.device).eval()
    print(f"[north_micro] {len(pages)} pages ({len(todo)} to run), batch {a.batch}, {a.device}", flush=True)
    t_all = time.time()
    for b in range(0, len(todo), a.batch):
        chunk = todo[b:b + a.batch]
        msgs = [[{"role": "user", "content": [{"type": "image", "path": str(p)}, {"type": "text", "text": PROMPT}]}] for p in chunk]
        t0 = time.time()
        try:
            inputs = proc.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True, return_tensors="pt",
                                              return_dict=True, processor_kwargs={"padding": True}).to(a.device)
            start = inputs["input_ids"].shape[1]
            stop = LoopStop(proc.tokenizer, start)
            torch.manual_seed(a.seed * 1000 + b // a.batch)
            with torch.inference_mode():
                gen = model.generate(**inputs, **sampling, max_new_tokens=a.max_new_tokens,
                                     stopping_criteria=StoppingCriteriaList([stop]))
            texts = proc.batch_decode(gen[:, start:], skip_special_tokens=True, clean_up_tokenization_spaces=False)
            ntok = [int((g[start:] != proc.tokenizer.pad_token_id).sum()) for g in gen]
            err = None
        except Exception as e:
            texts, ntok, err = [""] * len(chunk), [0] * len(chunk), f"{type(e).__name__}: {e}"
            (out / "_errors.log").open("a").write(f"\n===== {[p.name for p in chunk]}\n{err}\n")
            torch.cuda.empty_cache() if a.device == "cuda" else None
        secs = time.time() - t0
        for i, (p, t) in enumerate(zip(chunk, texts)):
            (out / f"{p.stem}.md").write_text(t, encoding="utf-8")
            looped = bool(stop.stopped is not None and stop.stopped[i]) if not err else False
            fin = "error" if err else "loop" if looped else "length" if ntok[i] >= a.max_new_tokens else "stop"
            rec = {"page": p.stem, "secs": round(secs / len(chunk), 1), "batch_secs": round(secs, 1), "chars": len(t),
                   "error": bool(err), "gen_tokens": ntok[i], "prompt_tokens": start if not err else None, "finish": fin}
            with (out / "_timing.jsonl").open("a") as f:
                f.write(json.dumps(rec) + "\n")
        print(f"[north_micro] batch {b // a.batch + 1}: {len(chunk)} pages in {secs:.0f}s{'  ERROR ' + err if err else ''}", flush=True)
    print(f"[north_micro] DONE in {time.time() - t_all:.0f}s", flush=True)


if __name__ == "__main__":
    main()
