"""Page-level parity between two result dirs: Jaccard of figure multisets (>=1000 or decimals) and identical-output flag."""
import sys, re; sys.path.insert(0, "."); import eval2, post_dots
from pathlib import Path
from collections import Counter
def figs(f):
    raw = f.read_text(errors="replace"); bl = post_dots.blocks_of(raw); text = post_dots.render(bl) if bl else raw
    return Counter(abs(v) for l in eval2.lines_of(eval2.extract_text(text)) for v in eval2.numbers(l) if abs(v) >= 1000 or v != int(v))
a, b = Path(sys.argv[1]), Path(sys.argv[2]); tot = 0; same = 0; rows = []
for f in sorted(a.glob("*.md")):
    g = b / f.name
    if not g.exists(): continue
    fa, fb = figs(f), figs(g); inter = sum((fa & fb).values()); union = sum((fa | fb).values())
    j = inter / union if union else 1.0; ident = f.read_text() == g.read_text()
    rows.append((f.stem, round(j, 3), sum(fa.values()), sum(fb.values()), ident)); tot += 1; same += ident
print(f"{a.name} vs {b.name}: {tot} pages, identical text {same}, mean figure-Jaccard {sum(r[1] for r in rows)/max(1,len(rows)):.3f}")
for r in rows: print(f"   {r[0]:<14} jaccard={r[1]:<6} figs {r[2]:>3} vs {r[3]:>3} {'IDENTICAL' if r[4] else ''}")
