"""Score model outputs against ground truth markdown.

Usage: python3 eval.py
Scores every model dir in output/ against the GT files, per document.
Metrics:
  - CER / WER (normalized text vs GT text)
  - Number recall: % of GT numeric values present in output
  - Number precision: % of output numbers that exist in GT (hallucination proxy)
"""
import re
import sys
import unicodedata
from pathlib import Path

from rapidfuzz.distance import Levenshtein

BASE = Path("/path/to/DocProcess/ocr_benchmark")
OUT = BASE / "output"

AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")

def normalize_text(t):
    t = unicodedata.normalize("NFKC", t).translate(AR_DIGITS)
    t = re.sub(r"<[^>]+>", " ", t)          # html tags
    t = re.sub(r"[|*_#`\-—–]", " ", t)      # md syntax & dashes
    t = re.sub(r"[إأآا]", "ا", t)
    t = re.sub(r"[ىي]", "ي", t)
    t = re.sub(r"ة", "ه", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()

NUM_RE = re.compile(r"-?\(?\d[\d,]*\.?\d*\)?")

def numbers(t):
    """Multiset of normalized numeric values."""
    t = unicodedata.normalize("NFKC", t).translate(AR_DIGITS)
    out = []
    for m in NUM_RE.findall(t):
        neg = m.startswith("(") or m.startswith("-")
        v = m.strip("()-").replace(",", "")
        try:
            f = float(v)
        except ValueError:
            continue
        out.append(round(-f if neg and f != 0 else f, 2))
    return out

def cer(ref, hyp):
    if not ref:
        return float("nan")
    return Levenshtein.distance(ref, hyp) / len(ref)

def wer(ref, hyp):
    r, h = ref.split(), hyp.split()
    if not r:
        return float("nan")
    # Levenshtein on word lists via token join trick is wrong; do DP
    prev = list(range(len(h) + 1))
    for i, rw in enumerate(r, 1):
        cur = [i] + [0] * len(h)
        for j, hw in enumerate(h, 1):
            cur[j] = min(prev[j] + 1, cur[j-1] + 1, prev[j-1] + (rw != hw))
        prev = cur
    return prev[-1] / len(r)

GT = {}
for gt_file in ["aramco_main_tables.md", "maaden_main_tables.md"]:
    GT[gt_file.split("_")[0]] = (BASE / gt_file).read_text(encoding="utf-8")

print(f"{'model':<10} {'doc':<8} {'pages':>5} {'CER':>7} {'WER':>7} {'num-recall':>10} {'num-prec':>9}")
for model_dir in sorted(OUT.iterdir()):
    if not model_dir.is_dir():
        continue
    pages = sorted(model_dir.glob("*.md")) + sorted(model_dir.glob("*.mmd"))
    by_doc = {}
    for pf in pages:
        doc = pf.stem.split("_")[0]
        by_doc.setdefault(doc, []).append(pf)
    for doc, pfs in by_doc.items():
        if doc not in GT:
            continue
        gt_text = normalize_text(GT[doc])
        hyp_texts, hyp_nums, gt_nums = [], [], numbers(GT[doc])
        for pf in pfs:
            t = pf.read_text(encoding="utf-8")
            hyp_texts.append(normalize_text(t))
            hyp_nums.extend(numbers(t))
        hyp_all = " ".join(hyp_texts)
        from collections import Counter
        gn, hn = Counter(gt_nums), Counter(hyp_nums)
        inter = sum((gn & hn).values())
        rec = inter / max(1, sum(gn.values()))
        prec = inter / max(1, sum(hn.values()))
        print(f"{model_dir.name:<10} {doc:<8} {len(pfs):>5} {cer(gt_text, hyp_all):>7.3f} "
              f"{wer(gt_text, hyp_all):>7.3f} {rec:>10.1%} {prec:>9.1%}")
