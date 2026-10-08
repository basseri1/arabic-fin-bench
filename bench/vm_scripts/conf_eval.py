"""Evaluate the combined per-figure confidence signals on a results dir (with .tok.json) against GT, all 3 companies."""
import sys, json; sys.path.insert(0, "."); import confidence as C
d = sys.argv[1]
rows = C.run(d, "results_enh/chandra2", ["maaden", "aramco"]) + C.run(d, "results_drill/chandra2_clahe", ["drilling"])
big = [r for r in rows if r["value"] >= 1000]                       # real financial figures (excludes EPS decimals / note refs)
wrong = [r for r in big if not r["correct"]]
print(f"{len(big)} emitted figures >= 1000; not in GT: {len(wrong)}")
for r in wrong: print("   not-in-GT:", r["page"], r["value"], "p_min", round(r["p_min"], 3) if r.get("p_min") else None, "anchored", r["anchored"], "suspect", r["suspect"], "agreed", r["agreed"])
ok = [r for r in big if r["correct"] and r.get("p_min") is not None]
for thr in (0.99, 0.95, 0.90, 0.80):
    print(f"  p_min < {thr}: flags {sum(1 for r in ok if r['p_min'] < thr)} correct figures ({100*sum(1 for r in ok if r['p_min'] < thr)/len(ok):.1f}%) and {sum(1 for r in wrong if (r.get('p_min') or 1) < thr)} of the not-in-GT ones")
print("agreed with Chandra-2:", sum(1 for r in big if r["agreed"]), "of", len(big), "| anchored:", sum(1 for r in big if r["anchored"]), "| anchored & agreed:", sum(1 for r in big if r["anchored"] and r["agreed"]))
low = [r for r in big if r["suspect"] or (not r["agreed"] and not r["anchored"]) or (r.get("p_min") or 1) < 0.95]
print(f"LOW by combined rule: {len(low)} figures ->", [(r["page"], r["value"], "WRONG" if not r["correct"] else "ok") for r in low][:15])
med = [r for r in big if r not in low and not (r["anchored"] and r["agreed"])]
print(f"MEDIUM: {len(med)}  HIGH: {len(big) - len(low) - len(med)}")
