"""GT-free structure-consistency check for one OCR page output (dots JSON / HTML / markdown).
Flags: column_loss (tables with fewer numeric value columns than the period headers on the page),
       no_structure (many numbers but no table rows), thin (suspiciously few numeric rows for the numbers present).
Usage: python structure_check.py <results_dir> [pages...]"""
import re, sys, json
from pathlib import Path
sys.path.insert(0, "."); import eval2, validate, post_dots
YEAR = re.compile(r"(?<![\d٠-٩])(?:20[12]\d|٢٠[١٢][٠-٩])(?![\d٠-٩])")
def page_text(f):
    raw = f.read_text(errors="replace"); bl = post_dots.blocks_of(raw)
    return post_dots.render(bl) if bl else raw
def check_text(text):
    t = eval2.extract_text(text); lines = eval2.lines_of(t)
    years = set(YEAR.findall(t)); expect = 2 if len(years) >= 2 else 1
    all_nums = [v for l in lines for v in eval2.numbers(l)]
    big = [v for v in all_nums if abs(v) >= 1000]
    flags = []
    tables = validate.parse_tables(t); tab_rows = 0
    for rows in tables:
        if len(rows) < 5: continue
        tab_rows += len(rows)
        per_row = [sum(1 for c in r if validate.cell_value(c) not in (None, 0.0) and abs(validate.cell_value(c)) >= 1000) for r in rows]
        per_row = [n for n in per_row if n > 0]
        if not per_row: continue
        per_row.sort(); med = per_row[len(per_row) // 2]
        if med < expect: flags.append(f"column_loss(median {med} value cols, {expect} periods, {len(rows)} rows)")
    if not tables and len(big) >= 30:
        rows2 = sum(1 for l in lines if len([v for v in eval2.numbers(l) if abs(v) >= 1000]) >= 2)
        if rows2 < len(big) / 4: flags.append(f"no_structure({len(big)} figures, {rows2} numeric rows)")
    return dict(expect_cols=expect, years=sorted(years), figures=len(big), table_rows=tab_rows, flags=flags)
if __name__ == "__main__":
    d = Path(sys.argv[1]); pages = sys.argv[2:] or sorted(p.stem for p in d.glob("*.md"))
    for pg in pages:
        f = d / f"{pg}.md"
        if f.exists():
            r = check_text(page_text(f)); print(f"{d.name:<28} {pg:<14} cols≥{r['expect_cols']} figs={r['figures']:>3} rows={r['table_rows']:>3}  {'OK' if not r['flags'] else 'FLAG ' + '; '.join(r['flags'])}")
