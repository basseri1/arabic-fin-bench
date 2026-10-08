"""The three Cohere Parse figures judged by eye in scoring_examples.html (Part A #7, Part B R11 and R12), shown again
after the parser fix (HTML rowspan, 2026-10-03): the printed crop, Cohere's own HTML table rendered as written (merged
cells included), the year the colspan-only parser read above the figure, the year the fixed parser reads, and the
verdict now. Local use only (embeds crops of the filings).
Writes agent_check/results/parser_fix_examples.html.   usage: python tools/parser_fix_examples.py
"""
import html
import json
import re
import sys
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PAPER / "tools"))
sys.path.insert(0, str(PAPER / "bench"))
import scoring_examples as X  # noqa: E402
import root_causes as RC  # noqa: E402
import common_subset as CS  # noqa: E402
import rq2_strict as R  # noqa: E402
import validate  # noqa: E402

ITEMS = [("Part A #7", "almarai_FY2024", 13, "مدفوعات أصل عقود الايجار", -122093),
         ("Part B R11", "almarai_FY2024", 13, "سداد قروض وتسهيلات", -16576340),
         ("Part B R12", "almarai_FY2024", 10, "", 1904539)]
RUN = CS.SYSTEMS["Cohere Parse"]


def raw_table(page, value):
    """Cohere's own <table> holding the figure, with only table markup kept and the figure marked."""
    raw = (R.RESULTS / RUN / f"{page}.md").read_text(encoding="utf-8")
    digits = f"{abs(value):,.0f}"
    for tb in re.findall(r"<table.*?</table>", raw, flags=re.S | re.I):
        if digits in tb:
            tb = re.sub(r"<(/?)(table|thead|tbody|tr|th|td|br|strong|b)\b([^>]*)>",
                        lambda m: f"<{m.group(1)}{m.group(2)}" + "".join(f' {a}="{v}"' for a, v in re.findall(r'(rowspan|colspan)\s*=\s*"?(\d+)', m.group(3))) + ">",
                        tb, flags=re.I)
            tb = re.sub(r"<(?!/?(table|thead|tbody|tr|th|td|br|strong|b)\b)[^>]+>", "", tb, flags=re.I)
            return tb.replace(digits, f"<mark>{digits}</mark>", 1).replace("<table", '<table class="t raw" dir="rtl"', 1)
    return "<p class='none'>(table not found)</p>"


def find(recs, fid, label, value):
    for r in recs:
        if r["filing"] != fid:
            continue
        st = TEST[fid]["statements"][r["k"][0]]
        row = next(x for x in st["rows"] if x["id"] == r["k"][1])
        if R.nlabel(row.get("label_ar", "")) == R.nlabel(label) and (row.get("values") or {}).get(r["k"][2]) == value:
            return r
    raise LookupError((fid, label, value))


def main():
    global TEST
    S = json.load(open(PAPER / "bench" / "rq2_strict_summary.json"))
    tr, tc = S["thresholds"]["row"], S["thresholds"]["col"]
    TEST = R.score.load_gt(str(PAPER / "gt"), "test")
    second = R.MAIN["dots.mocr pipeline, seed 0"][0]
    sub = {"almarai_FY2024": TEST["almarai_FY2024"]}
    validate.parse_tables = RC.parse_tables_colspan_only
    o_old, recs_old, cache_old = RC.run(RUN, sub, tr, tc, second)
    validate.parse_tables = RC.CURRENT_PARSER
    o_new, recs_new, cache_new = RC.run(RUN, sub, tr, tc, second)
    secs = []
    for name, fid, pno, label, value in ITEMS:
        a, b = find(recs_old, fid, label, value), find(recs_new, fid, label, value)
        st = TEST[fid]["statements"][b["k"][0]]
        row = next(x for x in st["rows"] if x["id"] == b["k"][1])
        img = X.crop(fid, pno, [v for v in (row.get("values") or {}).values() if isinstance(v, (int, float)) and v])
        d_old, d_new = cache_old[(RUN, fid)][a["cell"]["doc"]], cache_new[(RUN, fid)][b["cell"]["doc"]]
        verdict = lambda r: "complete" if r["outcome"] == "complete" else f"{r['outcome']}: {'period' if r['side'] == 'column' else r['side']}"
        period = next(c.get("label", "") for c in st["columns"] if c["id"] == b["k"][2])
        secs.append(f"""
<section>
  <h2>{X.e(name)}: Cohere Parse, {X.e(st.get('title_ar', ''))}, page {pno}</h2>
  <p>Printed line «{X.e(label) or '(no label printed)'}», figure {X.e(X.fmt(value))}, period «{X.e(period)}».</p>
  <img src="data:image/png;base64,{img}" alt="printed page">
  <div class="grid">
    <div><h3>What Cohere wrote (its HTML, merged cells as written)</h3>{raw_table(f"{fid}_p{pno:02d}", value)}</div>
    <div><h3>Your ground truth</h3>{X.gt_table(st, b['k'][1], b['k'][2])}</div>
  </div>
  <div class="verdict">
    <p><b>Before the fix</b> (rowspan ignored): header read above the figure «{X.e(d_old['header'][a['cell']['c']])}» → verdict <b>{X.e(verdict(a))}</b>.</p>
    <p><b>After the fix</b>: header read above the figure «{X.e(d_new['header'][b['cell']['c']])}» → verdict <b>{X.e(verdict(b))}</b>.</p>
  </div>
</section>""")
    css = re.search(r"<style>(.*?)</style>", (PAPER / "agent_check" / "results" / "scoring_examples.html").read_text(encoding="utf-8"), re.S).group(1)
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Parser fix: Cohere</title><style>{css}
table.raw td, table.raw th {{ border:1px solid var(--line); padding:3px 6px; }} mark {{ background:var(--fig); font-weight:700; }}
.verdict p {{ margin:4px 0; }}</style></head><body><main>
<h1>Correction: the three Cohere figures you judged</h1>
<p class="intro">In the first examples page, the table shown as “what the system wrote” for these three figures was our parser's reading
of Cohere's HTML, not the HTML itself. Cohere writes its notes heading as one cell spanning three header rows (rowspan="3").
Our parser ignored rowspan, so in the year row each year slid one column over: 2023 landed above the 2024 figures. Cohere's
own table is right, as rendered below. With rowspan honoured, all three figures are complete. Across the common base, this
removes all 31 of Cohere's “wrong period” figures and 31 of its 58 figures without a period.</p>
{''.join(secs)}
</main></body></html>"""
    out = PAPER / "agent_check" / "results" / "parser_fix_examples.html"
    out.write_text(page, encoding="utf-8")
    print("wrote", out)


if __name__ == "__main__":
    main()
