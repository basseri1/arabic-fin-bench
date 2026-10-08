"""Per-page selection between two (or more) pipeline outputs without ground truth: prefer the output with more
satisfied arithmetic relationships, then more numeric rows, then more distinct figures. Offline evaluation on Ma'aden."""
import sys, re, itertools; sys.path.insert(0, ".")
import eval2, validate, post_dots
from pathlib import Path
pages = [f"maaden_p{n}" for n in range(11, 17)]
GT = eval2.parse_gt(open("maaden_main_tables.md").read())
def bm_text(f):
    raw = f.read_text(errors="replace"); bl = post_dots.blocks_of(raw); return post_dots.render(bl) if bl else raw
def features(text):
    t = eval2.extract_text(text); lines = eval2.lines_of(t)
    n_rows2 = sum(1 for l in lines if len(eval2.numbers(l)) >= 2)
    figs = {abs(v) for l in lines for v in eval2.numbers(l) if abs(v) >= 1000 or v != int(v)}
    n_rel = 0
    for rows in validate.parse_tables(t):
        mat, width = validate.matrix(rows)
        if mat and width: n_rel += len(validate.relationships(mat, width))
    return (n_rel, n_rows2, len(figs))
def score_pages(texts):
    """texts: {page: text} -> (rows_hit, fig_hit) on Ma'aden GT."""
    R = F = 0
    for ti, tb in enumerate(GT, 1):
        blob = "\n".join(eval2.truncate_loops("\n".join(eval2.lines_of(eval2.extract_text(texts[p]))))[0] for p in eval2.TABLE_PAGES["maaden"][ti])
        c = eval2.score_tables([tb], blob); R += c["rows_hit"]; F += c["fig_hit"]
    return R, F
def load(d): return {pg: bm_text(Path(d) / f"{pg}.md") for pg in pages}
def page_gt_score(texts, pg):
    """GT rows hit counting only tables on this page (for the oracle)."""
    R = 0
    for ti, tb in enumerate(GT, 1):
        if eval2.TABLE_PAGES["maaden"][ti] == [pg]:
            R += eval2.score_tables([tb], "\n".join(eval2.lines_of(eval2.extract_text(texts[pg]))))["rows_hit"]
    return R
if __name__ == "__main__":
    base = load("results_enh/dots_mocr")
    for other in sys.argv[1:]:
        o = load(other); pick = {}; pick_or = {}; choices = []
        for pg in pages:
            fb, fo = features(base[pg]), features(o[pg])
            pick[pg] = o[pg] if fo > fb else base[pg]; choices.append("O" if fo > fb else "B")
            pick_or[pg] = o[pg] if page_gt_score(o, pg) > page_gt_score(base, pg) else base[pg]
        print(f"{other:<36} base {score_pages(base)}  other {score_pages(o)}  selected {score_pages(pick)}  choices {''.join(choices)}  oracle {score_pages(pick_or)}")
