#!/usr/bin/env python
"""Unified Arabic-OCR benchmark runner (one model per process).

    python bench.py --model <name> [--backend mlx|torch] [--only aramco_p12,maaden_p14] [--out DIR]

Default backend is MLX (Metal-native; all VLMs converted to bf16 - numerically the models' native dtype).
Torch/MPS adapters are kept for cross-checking. PaddleOCR-VL runs its own CPU pipeline.
Every model: greedy decoding, its own documented prompt, its own default image resolution, and a
hard wall-clock cap per page (MAX_TIME, default 900s) so a degenerate loop cannot stall the queue.
Outputs: results/<model>/<page>.md, results/<model>/_timing.jsonl (secs, tokens, tok/s), _errors.log.
Resume-safe: existing non-empty outputs are skipped.
"""
import argparse, json, os, sys, time, traceback, types
from pathlib import Path

os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

BASE = Path(__file__).resolve().parent
PAGES = Path(os.environ.get("PAGES_DIR", BASE / "pages"))
RESULTS = BASE / "results"
SCRATCH = Path(os.environ.get("SCRATCH", BASE / "_tmp")); SCRATCH.mkdir(exist_ok=True)
MAX_TIME = float(os.environ.get("MAX_TIME", "900"))
DEV = "mps"

# ----------------------------------------------------------------------------- prompts (verbatim from model cards / repos)
INSTRUCT = ("Extract all text and tables from this Arabic document page. "
            "Preserve the table structure using Markdown. Output only the extracted content.")
QARI2B = ("Below is the image of one page of a document, as well as some raw textual content that was "
          "previously extracted for it. Just return the plain text representation of this document as if "
          "you were reading it naturally. Do not hallucinate.")
DOTS_LAYOUT_ALL = """Please output the layout information from the PDF image, including each layout element's bbox, its category, and the corresponding text content within the bbox.

1. Bbox format: [x1, y1, x2, y2]

2. Layout Categories: The possible categories are ['Caption', 'Footnote', 'Formula', 'List-item', 'Page-footer', 'Page-header', 'Picture', 'Section-header', 'Table', 'Text', 'Title'].

3. Text Extraction & Formatting Rules:
    - Picture: For the 'Picture' category, the text field should be omitted.
    - Formula: Format its text as LaTeX.
    - Table: Format its text as HTML.
    - All Others (Text, Title, etc.): Format their text as Markdown.

4. Constraints:
    - The output text must be the original text from the image, with no translation.
    - All layout elements must be sorted according to human reading order.

5. Final Output: The entire output must be a single JSON object.
"""
# datalab-to/chandra: chandra/prompts.py (ocr_layout)
_CH_TAGS = ["math", "br", "i", "b", "u", "del", "sup", "sub", "table", "tr", "td", "p", "th", "div", "pre",
            "h1", "h2", "h3", "h4", "h5", "ul", "ol", "li", "input", "a", "span", "img", "hr", "tbody", "small",
            "caption", "strong", "thead", "big", "code", "chem"]
_CH_ATTRS = ["class", "colspan", "rowspan", "display", "checked", "type", "border", "value", "style", "href",
             "alt", "align", "data-bbox", "data-label"]
_CH_END = f"""
Only use these tags {_CH_TAGS}, and these attributes {_CH_ATTRS}.

Guidelines:
* Inline math: Surround math with <math>...</math> tags. Math expressions should be rendered in KaTeX-compatible LaTeX. Use display for block math.
* Tables: Use colspan and rowspan attributes to match table structure.
* Formatting: Maintain consistent formatting with the image, including spacing, indentation, subscripts/superscripts, and special characters.
* Images: Include a description of any images in the alt attribute of an <img> tag. Do not fill out the src property. Describe in detail inside the div tag. Also convert charts to high fidelity data, and convert diagrams to mermaid.
* Forms: Mark checkboxes and radio buttons properly.
* Text: join lines together properly into paragraphs using <p>...</p> tags.  Use <br> tags for line breaks within paragraphs, but only when absolutely necessary to maintain meaning.
* Chemistry: Use <chem>...</chem> tags for chemical formulas with reactive SMILES.
* Lists: Preserve indents and proper list markers.
* Use the simplest possible HTML structure that accurately represents the content of the block.
* Make sure the text is accurate and easy for a human to read and interpret.  Reading order should be correct and natural.
""".strip()
CHANDRA_OCR_LAYOUT = f"""
OCR this image to HTML, arranged as layout blocks.  Each layout block should be a div with the data-bbox attribute representing the bounding box of the block in x0 y0 x1 y1 format.  Bboxes are normalized 0-1000. The data-label attribute is the label for the block.

Use the following labels:
- Caption
- Footnote
- Equation-Block
- List-Group
- Page-Header
- Page-Footer
- Image
- Section-Header
- Table
- Text
- Complex-Block
- Code-Block
- Form
- Table-Of-Contents
- Figure
- Chemical-Block
- Diagram
- Bibliography
- Blank-Page

{_CH_END}
""".strip()

# datalab-to/lift: lift/prompts.py DIRECT_EXTRACTION_PROMPT with a generic statement-table schema
LIFT_SCHEMA = {"type": "object", "properties": {"statement_title": {"type": "string"}, "rows": {"type": "array", "items": {"type": "object", "properties": {"label": {"type": "string", "description": "row label exactly as printed (Arabic)"}, "note": {"type": "string", "description": "note reference, empty if none"}, "values": {"type": "array", "items": {"type": "number"}, "description": "every numeric amount in the row in column order; amounts in parentheses are negative"}}}}}}
LIFT_PROMPT = """Extract structured data from this document according to the provided JSON schema.  The document is provided as images, in page order.

## JSON Schema
```json
{schema}
```

## Instructions
- Return a JSON object matching the schema
- Use the correct type for each field (string, number, array)""".replace("{schema}", json.dumps(LIFT_SCHEMA, indent=2, ensure_ascii=False))


# ----------------------------------------------------------------------------- model specs
SPECS = {
    # name        backend  weights (MLX bf16)              prompt              max new tokens
    "qari2b":    dict(path="models/Qari2B-mlx-bf16",  prompt=QARI2B,            max_tokens=4096),
    "qari4b":    dict(path="models/Qari04-mlx-bf16",  prompt="Free OCR.",       max_tokens=4096),
    "ain":       dict(path="models/AIN-mlx-bf16",     prompt=INSTRUCT,          max_tokens=4096),
    "glm":       dict(path="models/GLM-OCR-mlx",      prompt="Text Recognition:", max_tokens=4096),
    "glm_table": dict(path="models/GLM-OCR-mlx",      prompt="Table Recognition:", max_tokens=4096),
    # dots_ocr/parser.py defaults: temperature=0.1, top_p=1.0 (official CLI pipeline)
    "dots_ocr":  dict(path="models/DotsOCR-mlx",      prompt=DOTS_LAYOUT_ALL,   max_tokens=8192,
                      gen_kwargs=dict(temperature=0.1, top_p=1.0, seed=0)),
    "dots_mocr": dict(path="models/DotsMOCR-mlx",     prompt=DOTS_LAYOUT_ALL,   max_tokens=8192,
                      gen_kwargs=dict(temperature=0.1, top_p=1.0, seed=0)),
    # LiquidAI docs recommend these generation settings for LFM2.5-VL (greedy loops on dense pages)
    "lfm25vl":   dict(path="models/LFM25VL-mlx",      prompt=INSTRUCT,          max_tokens=4096,
                      gen_kwargs=dict(temperature=0.1, min_p=0.15, repetition_penalty=1.05, seed=0)),
    # chandra/model/hf.py adds <|im_end|> as a stop token (generation_config only lists <|endoftext|>)
    "chandra2":  dict(path="models/Chandra2-mlx-bf16", prompt=CHANDRA_OCR_LAYOUT, max_tokens=8192, prep="chandra",
                      eos_tokens=["<|im_end|>", "<|endoftext|>"]),
    "xcuros":    dict(path="models/XCurOS-mlx-bf16",  prompt=INSTRUCT,          max_tokens=4096),
    "chandra1":  dict(path="models/Chandra1-mlx",     prompt=CHANDRA_OCR_LAYOUT, max_tokens=8192, prep="chandra",
                      eos_tokens=["<|im_end|>", "<|endoftext|>"]),
    # bakrianoo/arabic-legal-documents-ocr-1.0 (Gemma-3-4B-IT LoRA-finetune): card prompt + mandatory preprocessing
    "legalocr":  dict(path="models/LegalOCR-mlx",     prompt="Extract details to JSON.", max_tokens=4096, prep="legal"),
    # datalab-to/lift: schema extraction (own prompt template, image scaling 1088x1408, <|im_end|> stop)
    "lift":      dict(path="models/Lift-mlx",         prompt=LIFT_PROMPT,       max_tokens=8192, prep="lift",
                      eos_tokens=["<|im_end|>", "<|endoftext|>"], post="lift_rows"),
    # nanonets/Nanonets-OCR2-3B card: financial-documents prompt variant ("Only return HTML table"), greedy, rep-penalty 1
    "nanonets":  dict(path="models/NanonetsOCR2-mlx", max_tokens=8192,
                      prompt=("Extract the text from the above document as if you were reading it naturally. Return the tables in HTML format. "
                              "Return the equations in LaTeX representation. If there is an image in the document and image caption is not present, "
                              "add a small description of the image inside the <img></img> tag; otherwise, add the image caption inside <img></img>. "
                              "Watermarks should be wrapped in brackets. Ex: <watermark>OFFICIAL COPY</watermark>. Page numbers should be wrapped in "
                              "brackets. Ex: <page_number>14</page_number> or <page_number>9/22</page_number>. Prefer using ☐ and ☑ for check boxes. "
                              "Only return HTML table within <table></table>.")),
    # thelamapi/next-ocr card: system prompt "You are Next-OCR, an helpful AI assistant trained by Lamapi."
    "nextocr":   dict(path="models/NextOCR-mlx",      prompt=INSTRUCT,          max_tokens=4096,
                      system="You are Next-OCR, an helpful AI assistant trained by Lamapi."),
    # Cohere: card says do_sample=False is fine for deterministic output -> greedy
    "north":     dict(path="models/North-mlx",        prompt=INSTRUCT,          max_tokens=4096),
    # aya-vision-8b card example: do_sample=True, temperature=0.3
    "aya8b":     dict(path="models/AyaVision8B-mlx",  prompt=INSTRUCT,          max_tokens=4096,
                      gen_kwargs=dict(temperature=0.3, seed=0)),
    "paddle":    dict(backend="paddle"),
}
TORCH_IDS = {  # torch/MPS cross-check path (HF ids / local dirs)
    "qari2b": ("qwen2vl", "NAMAA-Space/Qari-OCR-v0.3-VL-2B-Instruct"),
    "ain": ("qwen2vl", "MBZUAI/AIN"),
    "qari4b": ("qari4b", None),
    "glm": ("glm", None),
    "dots_ocr": ("dots", "models/DotsOCR"),
    "dots_mocr": ("dots", "models/DotsMOCR"),
}


# ----------------------------------------------------------------------------- harness
def page_list(only):
    pages = sorted(PAGES.glob("*.png"))
    if only:
        keep = {p.strip() for p in only.split(",")}
        pages = [p for p in pages if p.stem in keep]
    return pages


def run_loop(name, pages, fn, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    timing = out_dir / "_timing.jsonl"
    for p in pages:
        out = out_dir / f"{p.stem}.md"
        if out.exists() and out.stat().st_size > 0:
            print(f"[{name}] {p.name}: cached, skipping", flush=True)
            continue
        t0 = time.time(); err = None; fn.stats = {}
        try:
            text = fn(p) or ""
        except Exception:
            text, err = "", traceback.format_exc()
            (out_dir / "_errors.log").open("a").write(f"\n===== {p.name} {time.ctime()}\n{err}")
        secs = time.time() - t0
        out.write_text(text, encoding="utf-8")
        if LAST_TOKENS.get(str(p)):
            (out_dir / f"{p.stem}.tok.json").write_text(json.dumps(LAST_TOKENS.pop(str(p)), ensure_ascii=False))
        if getattr(fn, "last_raw", None) is not None:
            (out_dir / f"{p.stem}.raw.txt").write_text(fn.last_raw, encoding="utf-8"); fn.last_raw = None
        rec = {"page": p.stem, "secs": round(secs, 1), "chars": len(text), "error": bool(err), **getattr(fn, "stats", {})}
        with timing.open("a") as f:
            f.write(json.dumps(rec) + "\n")
        extra = f", {rec.get('gen_tokens', '?')} tok @ {rec.get('gen_tps', 0):.1f} tok/s" if rec.get("gen_tokens") else ""
        print(f"[{name}] {p.name}: {secs:.1f}s, {len(text)} chars{extra}{'  ERROR' if err else ''}", flush=True)


# ----------------------------------------------------------------------------- image prep
def prep_chandra(img):
    """chandra/model/util.py scale_to_fit (max 3072x2048, min 1792x28, 28px grid) - replicated."""
    from PIL import Image
    im = Image.open(img).convert("RGB")
    w, h = im.size; ar = w / h; cur = w * h
    maxp, minp, g = 3072 * 2048, 1792 * 28, 28
    scale = (maxp / cur) ** 0.5 if cur > maxp else (minp / cur) ** 0.5 if cur < minp else 1.0
    wb, hb = max(1, round(w * scale / g)), max(1, round(h * scale / g))
    while wb * hb * g * g > maxp and not (wb == 1 and hb == 1):
        if wb == 1: hb -= 1; continue
        if hb == 1: wb -= 1; continue
        if abs((wb - 1) / hb - ar) < abs(wb / (hb - 1) - ar): wb -= 1
        else: hb -= 1
    im = im.resize((wb * g, hb * g), Image.Resampling.LANCZOS)
    out = SCRATCH / f"chandra_{Path(img).stem}.png"; im.save(out); return str(out)

def prep_legal(img):
    """bakrianoo/arabic-legal-documents-ocr-1.0 card: mandatory grayscale, max width 1024, contrast x1.5, JPEG q95."""
    from PIL import Image, ImageEnhance
    im = Image.open(img).convert("L")
    if im.width > 1024:
        im = im.resize((1024, int(im.height * 1024 / im.width)), Image.LANCZOS)
    im = ImageEnhance.Contrast(im).enhance(1.5)
    out = SCRATCH / f"legal_{Path(img).stem}.jpg"; im.save(out, "JPEG", optimize=True, quality=95); return str(out)

def _scale_to_fit(img, max_size, min_size, g=28):
    from PIL import Image
    im = Image.open(img).convert("RGB"); w, h = im.size; ar = w / h; cur = w * h
    maxp, minp = max_size[0] * max_size[1], min_size[0] * min_size[1]
    scale = (maxp / cur) ** 0.5 if cur > maxp else (minp / cur) ** 0.5 if cur < minp else 1.0
    wb, hb = max(1, round(w * scale / g)), max(1, round(h * scale / g))
    while wb * hb * g * g > maxp and not (wb == 1 and hb == 1):
        if wb == 1: hb -= 1; continue
        if hb == 1: wb -= 1; continue
        if abs((wb - 1) / hb - ar) < abs(wb / (hb - 1) - ar): wb -= 1
        else: hb -= 1
    return im.resize((wb * g, hb * g), Image.Resampling.LANCZOS)

def prep_lift(img):
    """lift/model/util.py scale_to_fit: max 1088x1408, min 1408x28, 28px grid."""
    im = _scale_to_fit(img, (1088, 1408), (1408, 28))
    out = SCRATCH / f"lift_{Path(img).stem}.png"; im.save(out); return str(out)

def post_lift_rows(text):
    """lift JSON -> one line per row 'label | note | v1 | v2 ...' so row metrics apply (raw kept separately)."""
    import json as _json, re as _re
    t = _re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    try:
        obj = _json.loads(t)
    except Exception:
        return text
    if not isinstance(obj, dict):
        return text
    out = [str(obj.get("statement_title", ""))]
    for r in obj.get("rows", []) or []:
        if not isinstance(r, dict): continue
        cells = [str(r.get("label", "")), str(r.get("note", "") or "")]
        for v in r.get("values") or []:
            cells.append(("(" + str(abs(v)) + ")") if isinstance(v, (int, float)) and v < 0 else str(v))
        out.append(" | ".join(cells))
    return "\n".join(out)

PREPS = {"chandra": prep_chandra, "legal": prep_legal, "lift": prep_lift}
POSTS = {"lift_rows": post_lift_rows}


# ----------------------------------------------------------------------------- MLX backend
def looping(t, win=200, span=12000, reps=3):
    """True when the last `win` chars already occurred >= reps-1 times in the preceding `span` chars
    (three identical 200-char windows) - a degenerate repetition loop, never a real statement."""
    if len(t) < win * reps:
        return False
    tail = t[-win:]
    body = t[-span:-win] if len(t) > span else t[:-win]
    return body.count(tail) >= reps - 1


LAST_TOKENS = {}
def make_mlx(name, spec):
    if os.environ.get("BENCH_PROMPT_FILE"):                                   # ablation overrides
        spec = dict(spec, prompt=Path(os.environ["BENCH_PROMPT_FILE"]).read_text())
    if os.environ.get("BENCH_MAX_TOKENS"):
        spec = dict(spec, max_tokens=int(os.environ["BENCH_MAX_TOKENS"]))
    from mlx_vlm import load, stream_generate
    from mlx_vlm.prompt_utils import apply_chat_template
    from mlx_vlm.utils import load_config
    try:                                   # never let one model take the whole machine (36 GB)
        import mlx.core as mx
        mx.set_memory_limit(int(os.environ.get("MLX_MEM_LIMIT_GB", "22")) * 2**30)
    except Exception as e:
        print("[warn] could not set MLX memory limit:", e, flush=True)
    path = str(BASE / spec["path"])
    model, processor = load(path)
    config = load_config(path)
    prep = PREPS.get(spec.get("prep"))
    if spec.get("eos_tokens"):
        # stream_generate() ignores the eos_tokens kwarg (only generate() reads it) -> register the stop ids
        # directly on the tokenizer wrapper's stopping criteria (and its eos list, so a reset keeps them).
        tk = getattr(processor, "tokenizer", processor)
        ids = [tk.convert_tokens_to_ids(t) if isinstance(t, str) else t for t in spec["eos_tokens"]]
        ids = [i for i in ids if isinstance(i, int) and i >= 0]
        try:
            tk.stopping_criteria.add_eos_token_ids(ids)
            if hasattr(tk, "eos_token_ids") and isinstance(tk.eos_token_ids, (list, set, tuple)):
                tk.eos_token_ids = list(dict.fromkeys(list(tk.eos_token_ids) + ids))
            print(f"[{name}] stop ids registered: {ids} -> criteria {getattr(tk.stopping_criteria, 'eos_token_ids', '?')}", flush=True)
        except Exception as e:
            print(f"[{name}] WARNING could not register stop ids: {e}", flush=True)

    def fn(img):
        src = prep(img) if prep else str(img)
        if spec.get("system"):
            try:
                prompt = apply_chat_template(processor, config, [{"role": "system", "content": spec["system"]},
                                                                 {"role": "user", "content": spec["prompt"]}], num_images=1)
            except Exception as e:
                print("[warn] system prompt unsupported by mlx_vlm template helper; using user-only:", e, flush=True)
                prompt = apply_chat_template(processor, config, spec["prompt"], num_images=1)
        else:
            prompt = apply_chat_template(processor, config, spec["prompt"], num_images=1)
        parts, t0, last, timed_out, loop_stop, n = [], time.time(), None, False, False, 0
        gen_kwargs = {"temperature": 0.0, **spec.get("gen_kwargs", {})}
        if os.environ.get("BENCH_SEED") is not None: gen_kwargs["seed"] = int(os.environ["BENCH_SEED"])
        if os.environ.get("BENCH_TEMP") is not None:                       # ablation override
            gen_kwargs["temperature"] = float(os.environ["BENCH_TEMP"])
            if gen_kwargs["temperature"] > 0: gen_kwargs.setdefault("seed", 0)
        if spec.get("eos_tokens"):                       # mlx_vlm only accepts ids (numeric strings) -> resolve here
            tk = getattr(processor, "tokenizer", processor)
            ids = [tk.convert_tokens_to_ids(t) if isinstance(t, str) else t for t in spec["eos_tokens"]]
            gen_kwargs["eos_tokens"] = [i for i in ids if isinstance(i, int) and i >= 0 and i != getattr(tk, "unk_token_id", -1)]
        toks = [] if os.environ.get("BENCH_LOGPROBS") else None
        for r in stream_generate(model, processor, prompt, image=[src], max_tokens=spec["max_tokens"], **gen_kwargs):
            parts.append(r.text); last = r; n += 1
            if toks is not None and r.token is not None and r.logprobs is not None:
                lp = r.logprobs; toks.append((int(r.token), r.text, float(lp[r.token]), float(mx.max(lp))))
            if time.time() - t0 > MAX_TIME:
                timed_out = True; break
            if n % 32 == 0 and looping("".join(parts)):
                loop_stop = True; break
        if toks is not None: LAST_TOKENS[str(src)] = toks
        if last is not None:
            fn.stats = {"prompt_tokens": last.prompt_tokens, "gen_tokens": last.generation_tokens,
                        "prompt_tps": round(last.prompt_tps, 1), "gen_tps": round(last.generation_tps, 1),
                        "finish": "max_time" if timed_out else "loop" if loop_stop else last.finish_reason, "backend": "mlx"}
        out = "".join(parts)
        if spec.get("post"):
            fn.last_raw = out
            out = POSTS[spec["post"]](out)
        return out
    fn.stats = {}
    return fn


# ----------------------------------------------------------------------------- torch / MPS backend (cross-check)
def _trim_decode(processor, gen, inputs):
    trimmed = gen[:, inputs["input_ids"].shape[1]:]
    return processor.batch_decode(trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]


def make_qwen2vl(model_id, prompt, max_new_tokens=4096, max_pixels=2_000_000):
    """Qwen2-VL family on torch/MPS. NOTE: >~2.2MP inputs overflow MPS's 32-bit attention indexing
    (NaN logits -> '!!!!' output), hence the max_pixels cap on this backend."""
    import torch
    from transformers import AutoProcessor, Qwen2VLForConditionalGeneration
    from qwen_vl_utils import process_vision_info
    model = Qwen2VLForConditionalGeneration.from_pretrained(model_id, torch_dtype=torch.bfloat16, device_map=DEV).eval()
    processor = AutoProcessor.from_pretrained(model_id, max_pixels=max_pixels)

    def fn(img):
        messages = [{"role": "user", "content": [{"type": "image", "image": f"file://{img}", "max_pixels": max_pixels},
                                                 {"type": "text", "text": prompt}]}]
        text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = processor(text=[text], images=image_inputs, videos=video_inputs, padding=True, return_tensors="pt").to(DEV)
        with torch.inference_mode():
            gen = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False, max_time=MAX_TIME)
        fn.stats = {"backend": "torch-mps", "gen_tokens": int(gen.shape[1] - inputs["input_ids"].shape[1])}
        return _trim_decode(processor, gen, inputs)
    fn.stats = {}
    return fn


def make_qari4b(max_new_tokens=4096):
    import torch
    from transformers import AutoProcessor, Qwen3VLForConditionalGeneration
    from peft import PeftModel
    from PIL import Image
    base, adapter = "unsloth/Qwen3-VL-4B-Instruct", "NAMAA-Space/Qari-OCR-0.4.0-VL-4B-Instruct"
    processor = AutoProcessor.from_pretrained(adapter, size={"longest_edge": 2_000_000, "shortest_edge": 65536})
    model = Qwen3VLForConditionalGeneration.from_pretrained(base, torch_dtype=torch.bfloat16, device_map=DEV)
    model = PeftModel.from_pretrained(model, adapter).merge_and_unload().eval()

    def fn(img):
        messages = [{"role": "user", "content": [{"type": "image", "image": Image.open(img)}, {"type": "text", "text": "Free OCR."}]}]
        inputs = processor.apply_chat_template(messages, tokenize=True, add_generation_prompt=True,
                                               return_dict=True, return_tensors="pt").to(DEV)
        with torch.inference_mode():
            gen = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False, max_time=MAX_TIME)
        return _trim_decode(processor, gen, inputs)
    fn.stats = {}
    return fn


def make_glm(max_new_tokens=4096):
    import torch
    from transformers import AutoProcessor, AutoModelForImageTextToText
    mid = "zai-org/GLM-OCR"
    processor = AutoProcessor.from_pretrained(mid, size={"longest_edge": 2_000_000, "shortest_edge": 12544})
    model = AutoModelForImageTextToText.from_pretrained(mid, dtype=torch.bfloat16, device_map=DEV).eval()

    def fn(img):
        messages = [{"role": "user", "content": [{"type": "image", "url": str(img)}, {"type": "text", "text": "Text Recognition:"}]}]
        inputs = processor.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, return_dict=True, return_tensors="pt").to(DEV)
        inputs.pop("token_type_ids", None)
        with torch.inference_mode():
            gen = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False, max_time=MAX_TIME)
        return processor.decode(gen[0, inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    fn.stats = {}
    return fn


def _dots_processor(local_dir):
    """dots' remote DotsVLProcessor predates transformers>=4.53 (no video_processor) -> build the
    equivalent Qwen2.5-VL processor by hand with dots' image-processor config, chat template, <|imgpad|>."""
    import json as _json
    from transformers import AutoTokenizer, Qwen2VLImageProcessor, Qwen2_5_VLProcessor
    from transformers.models.qwen2_vl.video_processing_qwen2_vl import Qwen2VLVideoProcessor
    tok = AutoTokenizer.from_pretrained(local_dir)
    imgp = Qwen2VLImageProcessor.from_pretrained(local_dir, max_pixels=2_000_000)
    tmpl = _json.load(open(Path(local_dir) / "chat_template.json"))["chat_template"]
    proc = Qwen2_5_VLProcessor(image_processor=imgp, tokenizer=tok, video_processor=Qwen2VLVideoProcessor(), chat_template=tmpl)
    proc.image_token = "<|imgpad|>"; proc.image_token_id = tok.convert_tokens_to_ids("<|imgpad|>")
    return proc


def make_dots(local_dir, max_new_tokens=8192):
    """dots.ocr / dots.mocr on torch/MPS. Remote code hard-imports flash_attn (CUDA-only): register a
    stub module so the static import check passes, and force SDPA attention in both towers."""
    import importlib.machinery
    stub = types.ModuleType("flash_attn")
    stub.__spec__ = importlib.machinery.ModuleSpec("flash_attn", None); stub.__version__ = "0.0.0-stub"
    def _na(*a, **k): raise RuntimeError("flash_attn stub called - attention should be sdpa")
    stub.flash_attn_varlen_func = stub.flash_attn_func = _na
    sys.modules["flash_attn"] = stub
    import torch
    from transformers import AutoConfig, AutoModelForCausalLM
    from qwen_vl_utils import process_vision_info
    cfg = AutoConfig.from_pretrained(local_dir, trust_remote_code=True)
    cfg.vision_config.attn_implementation = "sdpa"
    model = AutoModelForCausalLM.from_pretrained(local_dir, config=cfg, attn_implementation="sdpa",
                                                 torch_dtype=torch.bfloat16, trust_remote_code=True).to(DEV).eval()
    processor = _dots_processor(local_dir)

    def fn(img):
        messages = [{"role": "user", "content": [{"type": "image", "image": f"file://{img}", "max_pixels": 2_000_000},
                                                 {"type": "text", "text": DOTS_LAYOUT_ALL}]}]
        text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = processor(text=[text], images=image_inputs, videos=video_inputs, padding=True, return_tensors="pt").to(DEV)
        with torch.inference_mode():
            gen = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False, max_time=MAX_TIME)
        return _trim_decode(processor, gen, inputs)
    fn.stats = {}
    return fn


def make_torch(name, spec):
    kind, ident = TORCH_IDS[name]
    if kind == "qwen2vl": return make_qwen2vl(ident, spec["prompt"], spec["max_tokens"])
    if kind == "qari4b":  return make_qari4b(spec["max_tokens"])
    if kind == "glm":     return make_glm(spec["max_tokens"])
    if kind == "dots":    return make_dots(str(BASE / ident), spec["max_tokens"])
    raise ValueError(name)


# ----------------------------------------------------------------------------- PaddleOCR-VL (own pipeline, CPU)
def run_paddle(pages, out_dir):
    from paddleocr import PaddleOCRVL
    pipeline = PaddleOCRVL()
    out_dir.mkdir(parents=True, exist_ok=True)
    timing = out_dir / "_timing.jsonl"
    for p in pages:
        out = out_dir / f"{p.stem}.md"
        if out.exists() and out.stat().st_size > 0:
            print(f"[paddle] {p.name}: cached, skipping", flush=True); continue
        t0 = time.time(); err = None
        try:
            for res in pipeline.predict(str(p)):
                res.save_to_markdown(save_path=str(out_dir))
        except Exception:
            err = traceback.format_exc()
            (out_dir / "_errors.log").open("a").write(f"\n===== {p.name}\n{err}")
        secs = time.time() - t0
        if not out.exists():
            out.write_text("", encoding="utf-8")
        n = out.stat().st_size
        with timing.open("a") as f:
            f.write(json.dumps({"page": p.stem, "secs": round(secs, 1), "chars": n, "error": bool(err), "backend": "paddle-cpu"}) + "\n")
        print(f"[paddle] {p.name}: {secs:.1f}s, {n} bytes{'  ERROR' if err else ''}", flush=True)


# ----------------------------------------------------------------------------- main
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=sorted(SPECS))
    ap.add_argument("--backend", default="mlx", choices=["mlx", "torch"])
    ap.add_argument("--only", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    spec = SPECS[a.model]
    pages = page_list(a.only)
    out_dir = Path(a.out) if a.out else RESULTS / a.model
    print(f"[{a.model}] {len(pages)} pages -> {out_dir}  backend={spec.get('backend', a.backend)}  (python {sys.version.split()[0]})", flush=True)
    if spec.get("backend") == "paddle":
        run_paddle(pages, out_dir)
    else:
        fn = make_mlx(a.model, spec) if a.backend == "mlx" else make_torch(a.model, spec)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "_meta.json").write_text(json.dumps({"model": a.model, "backend": a.backend, **{k: v for k, v in spec.items() if k != "prompt"},
                                                         "prompt": spec["prompt"][:200], "max_time": MAX_TIME}, indent=1))
        run_loop(a.model, pages, fn, out_dir)
    print(f"[{a.model}] DONE", flush=True)
