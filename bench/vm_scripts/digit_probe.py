"""Digit-script micro-probe: can the model read Arabic-Indic (٠١٢٣٤٥٦٧٨٩) vs Western digits?
Renders the SAME numbers in both scripts (clean synthetic images, Arial, no scan noise) and
checks exact match after digit normalisation. Isolates digit-script ability from scan quality.
Usage: python digit_probe.py --model <name>   (MLX backend; same prompts as bench.py)
"""
import argparse, json, re, sys, time, unicodedata
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bench

BASE = Path(__file__).resolve().parent
OUT = BASE / "_tmp" / "digits"; OUT.mkdir(parents=True, exist_ok=True)
NUMS = ["32,546,157,340", "(23,301,998,978)", "4,133,892,264", "0.78", "115,709,626", "(16,175,246)"]
AR = str.maketrans("0123456789,.", "٠١٢٣٤٥٦٧٨٩٬٫")
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"

def render(text, path, size=64):
    font = ImageFont.truetype(FONT, size)
    W, H = int(len(text) * size * 0.62) + 120, size * 2 + 60
    im = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(im)
    d.text((60, 30 + size // 2), text, font=font, fill="black", anchor="lm")
    im.save(path)

def norm(t):
    t = unicodedata.normalize("NFKC", t).translate(str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹٬٫", "0123456789" "0123456789" ",."))  # Arabic-Indic + Persian forms
    return re.sub(r"[^\d.,()]", "", t)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--model", required=True); a = ap.parse_args()
    items = []
    for i, n in enumerate(NUMS):
        for script, txt in (("western", n), ("arabic_indic", n.translate(AR))):
            p = OUT / f"{i}_{script}.png"
            if not p.exists(): render(txt, p)
            items.append((script, n, p))
    # one "column" image per script (5 numbers stacked, like a table column)
    for script in ("western", "arabic_indic"):
        p = OUT / f"col_{script}.png"
        if not p.exists():
            font = ImageFont.truetype(FONT, 48); im = Image.new("RGB", (700, 60 * len(NUMS) + 60), "white"); d = ImageDraw.Draw(im)
            for j, n in enumerate(NUMS):
                d.text((640, 40 + j * 60), n if script == "western" else n.translate(AR), font=font, fill="black", anchor="rm")
            im.save(p)
        items.append((script, "|".join(NUMS), p))
    OPENROUTER = {"qwen38_27b": "qwen/qwen3.8-27b", "qwen36_27b": "qwen/qwen3.6-27b", "qwen3vl_32b": "qwen/qwen3-vl-32b-instruct", "nemotron12b_vl": "nvidia/nemotron-nano-12b-v2-vl:free", "ernie45_vl": "baidu/ernie-4.5-vl-424b-a47b"}
    if a.model == "mistral_ocr":                       # hosted API model: same probe, via run_mistral_native
        import run_mistral_native as rm
        fn = lambda img: rm.ocr_page(Path(img))[0]
    elif a.model in OPENROUTER:
        import run_openrouter_vlm as ro
        fn = lambda img: ro.ask(OPENROUTER[a.model], Path(img), 256)[0]
    elif a.model == "paddle_ar":
        from run_paddle_classic import make_fn; fn = make_fn()
    elif a.model == "surya2":
        from run_surya import make_fn; fn = make_fn()
    elif a.model == "persar2b":
        from run_linelevel import make_fn; fn = make_fn()
    elif a.model in ("aya32b_api", "cmda_vision"):
        import run_cohere_vlm as rc
        mid = {"aya32b_api": "c4ai-aya-vision-32b", "cmda_vision": "command-a-vision-07-2025"}[a.model]
        fn = lambda img: rc.ask(mid, Path(img), 256, 0.3 if a.model == "aya32b_api" else 0.0)[0]
    else:
        spec = bench.SPECS[a.model]
        fn = bench.make_mlx(a.model, spec)
    res = {"western": [0, 0], "arabic_indic": [0, 0]}; details = []
    for script, truth, p in items:
        try:
            out = fn(p) or ""
        except Exception as e:                       # hosted APIs: treat an error as a miss, keep going
            out = f"<error: {type(e).__name__}: {str(e)[:80]}>"
        hyp = norm(out)
        truths = truth.split("|")
        ok = all(norm(t) in hyp for t in truths)
        res[script][0] += ok; res[script][1] += 1
        details.append({"script": script, "truth": truth, "out": out.strip()[:120], "ok": ok})
        print(f"[{a.model}] {script:13s} {truth[:28]:<28} -> {'OK ' if ok else 'BAD'}  {out.strip()[:70]!r}", flush=True)
    summary = {k: f"{v[0]}/{v[1]}" for k, v in res.items()}
    print(f"[{a.model}] SUMMARY {summary}", flush=True)
    (BASE / "results" / a.model).mkdir(parents=True, exist_ok=True)
    (BASE / "results" / a.model / "_digit_probe.json").write_text(json.dumps({"summary": summary, "details": details}, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
