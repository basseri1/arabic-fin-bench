"""Merge the two column-group crops of a wide table back into full rows (sequential label alignment),
then score the equity statement. Usage: python exp_merge.py results_exp/<model>_split  [--write]"""
import sys, re, glob
sys.path.insert(0, "."); import eval2
from rapidfuzz import fuzz
from collections import Counter

def rows(path):
    t = "\n".join(eval2.lines_of(eval2.extract_text(open(path, errors="replace").read())))
    out = []
    for l in t.splitlines():
        if not l.strip(): continue
        lab = eval2.norm_ar(re.sub(r"[\d٠-٩,.()\-|]+", " ", eval2.norm_digits(l)))
        out.append((lab, l, Counter(eval2.numbers(l))))
    return out

def merge(a_path, b_path, thr=70):
    """Global alignment of the two halves' row sequences (labels appear in both crops); unmatched rows kept."""
    import difflib
    A, B = rows(a_path), rows(b_path)
    la, lb = [r[0] for r in A], [r[0] for r in B]
    # map labels to tokens so SequenceMatcher compares whole labels (fuzzy: bucket by best match)
    def key(lab, pool):
        best = max(pool, key=lambda q: fuzz.ratio(lab, q)) if pool and lab else None
        return best if best and fuzz.ratio(lab, best) >= thr else lab
    keysA = la; keysB = [key(x, la) for x in lb]
    sm = difflib.SequenceMatcher(None, keysA, keysB, autojunk=False)
    usedB = set(); pairs = {}
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1): pairs[i1 + k] = j1 + k; usedB.add(j1 + k)
    merged = []
    for i, (lab, ta, na) in enumerate(A):
        merged.append(ta + (" | " + B[pairs[i]][1] if i in pairs else ""))
    for j, (lb_, tb, nb) in enumerate(B):
        if j not in usedB: merged.append(tb)
    return "\n".join(merged)


if __name__ == "__main__":
    d = sys.argv[1]
    a = glob.glob(f"{d}/maaden_p14_A.md")[0]; b = glob.glob(f"{d}/maaden_p14_B.md")[0]
    m = merge(a, b)
    gt = eval2.parse_gt(open("maaden_main_tables.md").read())[3]   # equity
    c = eval2.score_tables([gt], m)
    print(f"{d}: equity rows {c['rows_hit']}/{c['rows_tot']}  figs {c['fig_hit']}/{c['fig_tot']}  prec {c['prec_hit']/max(1,c['prec_tot'])*100:.0f}%")
    if "--write" in sys.argv:
        import os; od = d + "_merged"; os.makedirs(od, exist_ok=True); open(f"{od}/maaden_p14.md", "w").write(m); print("wrote", od)
