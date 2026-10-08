"""Geometry-aware post-processing for dots.ocr / dots.mocr JSON output: non-table text blocks that share a
horizontal band (same row on the page) are merged into one line, right-to-left, so label + figures that the
model emitted as separate blocks become one table row. Tables are kept as emitted (HTML rows).
Usage: python post_dots.py <results_dir> <out_dir>   (writes <page>.md with the merged lines)"""
import json, re, re, sys
from pathlib import Path
CH_DIV = re.compile(r'<div\s+data-bbox="(\d+)\s+(\d+)\s+(\d+)\s+(\d+)"\s+data-label="([^"]+)">(.*?)</div>', re.S)
def blocks_of(raw):
    try: return json.loads(raw[raw.index("["):raw.rindex("]") + 1])
    except Exception: pass
    out = []                                    # Chandra HTML: <div data-bbox="x0 y0 x1 y1" data-label="...">...</div>
    for m in CH_DIV.finditer(raw):
        cat = m.group(5).replace("Section-Header", "Section-header").replace("Page-Header", "Page-header").replace("Page-Footer", "Page-footer")
        out.append({"bbox": [int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))], "category": cat, "text": m.group(6)})
    return out if len(out) >= 2 else None
def band_merge(blocks, tol=0.6):
    """Group blocks whose vertical centres lie within tol*height of each other; order each group right-to-left."""
    items = []
    for b in blocks:
        x0, y0, x1, y1 = b["bbox"]; items.append(dict(b, cy=(y0 + y1) / 2, h=max(1, y1 - y0), x0=x0))
    items.sort(key=lambda b: b["cy"]); groups = []
    for b in items:
        if groups and abs(b["cy"] - groups[-1][-1]["cy"]) < tol * min(b["h"], groups[-1][-1]["h"]) and not (b.get("category") == "Table" or groups[-1][-1].get("category") == "Table"):
            groups[-1].append(b)
        else: groups.append([b])
    return [sorted(g, key=lambda b: -b["x0"]) for g in groups]
def render(blocks):
    out = []
    for g in band_merge(blocks):
        if len(g) == 1 and g[0].get("category") == "Table":
            out.append(g[0].get("text", "")); continue
        out.append("  ".join(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", b.get("text", ""))).strip() for b in g))
    return "\n".join(out)
if __name__ == "__main__":
    src, dst = Path(sys.argv[1]), Path(sys.argv[2]); dst.mkdir(parents=True, exist_ok=True); n = 0
    for f in sorted(src.glob("*.md")):
        raw = f.read_text(errors="replace"); bl = blocks_of(raw)
        (dst / f.name).write_text(render(bl) if bl else raw); n += 1
    for extra in ("_timing.jsonl", "_meta.json"):
        if (src / extra).exists(): (dst / extra).write_text((src / extra).read_text())
    print(f"post_dots: {n} pages -> {dst}")
