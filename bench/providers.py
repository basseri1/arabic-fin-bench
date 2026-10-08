"""Controlled provider test (RQ3): the same 22 statements (one per test filing, drawn with seed 0; bench/provider_sample.json)
sent through OpenRouter to Qwen3.8-27B with the provider pinned and fallbacks off, against our self-hosted run of the
official BF16 weights and the original unpinned API run. Each statement is scored on its own pages only.
Quantisation is what each provider declares to OpenRouter (bench/openrouter_endpoints_qwen38_*.json).
Writes bench/PROVIDERS.md.  usage: python bench/providers.py
"""
import glob
import json
import sys
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PAPER / "tools"))
import score  # noqa: E402

RESULTS = PAPER / "bench" / "results32"
E = score.E


def main():
    sample = json.loads((PAPER / "bench" / "provider_sample.json").read_text())
    gts = score.load_gt(str(PAPER / "gt"), "test")
    eps = json.loads(Path(sorted(glob.glob(str(PAPER / "bench" / "openrouter_endpoints_qwen38_*.json")))[-1]).read_text())
    quant = {e["provider_name"]: (e.get("quantization") if e.get("quantization") not in (None, "", "unknown") else "not declared") for e in eps["data"]["endpoints"]}
    price = {e["provider_name"]: e.get("pricing") or {} for e in eps["data"]["endpoints"]}
    runs = {"self-hosted (official BF16 weights, vLLM)": RESULTS / "qwen38_27b_local_plain",
            "OpenRouter, unpinned (original run)": RESULTS / "qwen38_27b_plain"}
    for d in sorted((RESULTS / "_providers").glob("qwen38_*")):
        meta = json.loads((d / "_meta.json").read_text())
        served = {json.loads(f.read_text()).get("provider") for f in (d / "_raw").glob("*.json")}
        name = next(iter(served)) if len(served) == 1 else meta["provider_pinned"]
        runs[f"OpenRouter pinned: {name}"] = d
    rows = []
    per_stmt = {}
    for label, d in runs.items():
        texts = score.page_texts(d)
        hit = tot = fh = ft = 0; missing = 0; per = []
        for s in sample["statements"]:
            gt = gts[s["filing"]]
            idx = [st["id"] for st in gt["statements"]].index(s["statement"])
            table = score.gtlib.to_eval_tables(gt)[idx]
            if not all(p in texts for p in s["pages"]):
                missing += 1; continue
            c = E.score_tables([table], "\n".join(texts[p] for p in s["pages"]))
            hit += c["rows_hit"]; tot += c["rows_tot"]; fh += c["fig_hit"]; ft += c["fig_tot"]
            per.append(c["rows_hit"] / c["rows_tot"] if c["rows_tot"] else None)
        cost = None
        tf = d / "_timing.jsonl"
        if tf.exists() and "_providers" in str(d):
            recs = [json.loads(l) for l in tf.read_text().splitlines() if l.strip()]
            cost = sum(r.get("cost_usd") or 0 for r in recs)
        prov = label.split(": ", 1)[1] if ": " in label else None
        q = quant.get(prov, "not declared") if prov else ("bf16" if "self-hosted" in label else "mixed")
        rows.append(dict(label=label, quant=q,
                         row=hit / tot if tot else None, fig=fh / ft if ft else None, rows=tot, missing=missing, cost=cost,
                         price_out=(price.get(prov) or {}).get("completion")))
        per_stmt[label] = per
    base = per_stmt["self-hosted (official BF16 weights, vLLM)"]
    out = ["# Same model, same pages, different providers", "",
           f"Qwen3.8-27B on {len(sample['statements'])} statements ({len(sample['pages'])} pages; one statement per held-out "
           "filing, drawn with seed 0). Same prompt, temperature 0, 8,192-token cap, reasoning off. Pinned runs use "
           "OpenRouter provider routing with fallbacks disabled; every response was checked to come from the pinned provider. "
           "Quantisation is as declared by each provider to OpenRouter on the day of the run.", "",
           "| Served by | Declared quantisation | Row recall | Figure recall | Statements worse than self-hosted | Cost of the run |",
           "|---|---|---:|---:|---:|---:|"]
    for r in sorted(rows, key=lambda r: -(r["row"] or 0)):
        per = per_stmt[r["label"]]
        worse = "–" if "self-hosted" in r["label"] else sum(1 for a, b in zip(per, base) if a is not None and b is not None and a < b - 1e-9)
        cost = "–" if r["cost"] is None else f"${r['cost']:.3f}"
        out.append(f"| {r['label']} | {r['quant']} | {100 * r['row']:.1f}% | {100 * r['fig']:.1f}% | {worse} | {cost} |")
    out += ["", f"Rows scored per run: {rows[0]['rows']}. Statements missing from a run: "
            + ", ".join(f"{r['label']} {r['missing']}" for r in rows if r["missing"]) if any(r["missing"] for r in rows) else ""]
    (PAPER / "bench" / "PROVIDERS.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    json.dump(dict(rows=rows, per_statement=per_stmt), open(PAPER / "bench" / "providers_summary.json", "w"), indent=1)
    print("\n".join(out))


if __name__ == "__main__":
    main()
