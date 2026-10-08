import sys; sys.path.insert(0, "."); import eval2
from pathlib import Path
GT = eval2.parse_gt(open("maaden_main_tables.md").read()); GTd = eval2.parse_gt(open("drilling_main_tables.md").read())
def rows(d, doc, ti, GTx):
    fs = [Path(d) / f"{p}.md" for p in eval2.TABLE_PAGES[doc][ti]]
    if not all(f.exists() for f in fs): return "n/a"
    blob = "\n".join(eval2.truncate_loops("\n".join(eval2.lines_of(eval2.extract_text(f.read_text(errors="replace")))))[0] for f in fs)
    c = eval2.score_tables([GTx[ti - 1]], blob); return f"{c['rows_hit']}/{c['rows_tot']}"
for d in sys.argv[1:]:
    print(f"{d:<42} ma-P&L {rows(d,'maaden',1,GT):<6} ma-Bal {rows(d,'maaden',3,GT):<6} ma-Equity {rows(d,'maaden',4,GT):<6} ma-noncash {rows(d,'maaden',6,GT):<6} dr-Equity {rows(d,'drilling',4,GTd)}")
