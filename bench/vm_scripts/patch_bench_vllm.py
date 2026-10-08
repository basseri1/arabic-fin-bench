from pathlib import Path
p = Path("bench_vllm.py")
s = p.read_text()
if "qwen3vl_32b" not in s:
    Path("bench_vllm.py.bak32").write_text(s)
    anchor = '''def b64_image(path, prep):'''
    add = '''# --- 32-filing rerun: further open models served on this VM (vendor prompts; greedy decoding) ---
import bench as _bench
GENERIC_PROMPT = ("Extract all text and tables from this Arabic document page. "
                  "Preserve the table structure using Markdown. Output only the extracted content.")   # same as the hosted VLM runs
SPECS.update({
 "nanonets":       dict(prompt=_bench.SPECS["nanonets"]["prompt"], max_tokens=8192, gen=dict(temperature=0.0), prep=None, port=8010),
 "qwen3vl_32b":    dict(prompt=GENERIC_PROMPT, max_tokens=8192, gen=dict(temperature=0.0), prep=None, port=8010),
 "nemotron12b_vl": dict(prompt=GENERIC_PROMPT, max_tokens=8192, gen=dict(temperature=0.0), prep=None, port=8010),
 "chandra1":       dict(prompt=CHANDRA_OCR_LAYOUT, max_tokens=8192, gen=dict(temperature=0.0), prep="chandra", port=8011),
})
'''
    s = s.replace(anchor, add + anchor, 1)
    p.write_text(s)
    print("patched")
else:
    print("already patched")
