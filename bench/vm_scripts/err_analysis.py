"""Where does a model miss? For each GT data row not matched, show the GT figures and the closest output line
(by shared figures, then by fuzzy label), and classify the miss."""
import sys, glob, re
from collections import Counter
sys.path.insert(0, "."); import eval2
from rapidfuzz import fuzz
def analyse(model, docs=("aramco", "maaden"), show=40):
    GT = {d: eval2.parse_gt(f.read_text()) for d, f in eval2.GT_FILES.items()}
    kinds = Counter(); shown = 0
    for doc in docs:
        for ti, tb in enumerate(GT[doc], 1):
            pages = eval2.TABLE_PAGES[doc][ti]
            blob = "\n".join(eval2.truncate_loops("\n".join(eval2.lines_of(eval2.extract_text(open(f"results/{model}/{p}.md", errors="replace").read()))))[0] for p in pages if glob.glob(f"results/{model}/{p}.md"))
            lines = [l for l in blob.splitlines() if l.strip()]
            lnums = [Counter(eval2.numbers(l)) for l in lines]
            for r in tb["rows"]:
                need = Counter(abs(v) for v in r["figs"])
                if any(not (need - ln) for ln in lnums): continue
                # closest line: max shared figures, tie-break by label similarity
                best = max(range(len(lines)), key=lambda i: (sum((need & lnums[i]).values()), fuzz.partial_ratio(eval2.norm_ar(r["label"]), eval2.norm_ar(lines[i])))) if lines else None
                shared = sum((need & lnums[best]).values()) if best is not None else 0
                labsim = fuzz.partial_ratio(eval2.norm_ar(r["label"]), eval2.norm_ar(lines[best])) if best is not None else 0
                # classify
                all_blob = Counter(eval2.numbers(blob))
                present = sum((need & all_blob).values())
                if present == len(r["figs"]) and shared < len(r["figs"]): kind = "row split / figures on different lines"
                elif present < len(r["figs"]) and labsim >= 80 and shared >= 1: kind = "figure misread or dropped in the row"
                elif labsim >= 80: kind = "row found, figures wrong/missing"
                else: kind = "row not found (label absent)"
                kinds[kind] += 1
                if shown < show:
                    shown += 1
                    print(f"[{doc} T{ti} {eval2.TABLE_NAMES[ti]}] {r['label'][:45]!r} GT={[int(abs(v)) if abs(v)>=1 else abs(v) for v in r['figs']]}")
                    print(f"      -> {kind}; closest line ({shared}/{len(r['figs'])} figs, label sim {labsim}): {re.sub(r'\\s+',' ',lines[best])[:150] if best is not None else '-'}")
    print("\nmiss kinds:", dict(kinds))
if __name__ == "__main__":
    analyse(sys.argv[1], show=int(sys.argv[2]) if len(sys.argv) > 2 else 40)
