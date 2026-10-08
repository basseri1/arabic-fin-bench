# RQ2 — verification and confidence routing (32-filing benchmark)

Signals use no ground truth; the approved ground truth only scores them. Definitions are in the header of `bench/confidence32.py`. Token probabilities, the third pilot signal, come from a separate re-run and are analysed in their own section below.

## Arithmetic verification (automatic repairs)

Each repair is one single-digit edit that makes a broken printed total reconcile, accepted only when it is the unique such edit. Scored against the ground truth: figures of 1,000 or more against all figures of the filing, smaller ones (per-share lines) against the cell's own row, found by its label. Repaired = wrong before, right after; damaged = the reverse.

| Output | Split | Repairs | Repaired | Damaged | Both wrong | Both right | Totals flagged, not repaired |
|---|---|---:|---:|---:|---:|---:|---:|
| dots.mocr pipeline, seed 0 | test | 5 | 5 | 0 | 0 | 0 | 26 |
| dots.mocr pipeline, seed 0 | dev | 0 | 0 | 0 | 0 | 0 | 14 |
| dots.mocr pipeline, seed 0 | all | 5 | 5 | 0 | 0 | 0 | 40 |
| dots.mocr pipeline, seed 1 | test | 6 | 5 | 1 | 0 | 0 | 23 |
| dots.mocr pipeline, seed 1 | dev | 0 | 0 | 0 | 0 | 0 | 11 |
| dots.mocr pipeline, seed 1 | all | 6 | 5 | 1 | 0 | 0 | 34 |
| dots.mocr pipeline, seed 2 | test | 6 | 5 | 1 | 0 | 0 | 22 |
| dots.mocr pipeline, seed 2 | dev | 0 | 0 | 0 | 0 | 0 | 13 |
| dots.mocr pipeline, seed 2 | all | 6 | 5 | 1 | 0 | 0 | 35 |
| Chandra OCR 2, own input size | test | 4 | 4 | 0 | 0 | 0 | 28 |
| Chandra OCR 2, own input size | dev | 0 | 0 | 0 | 0 | 0 | 10 |
| Chandra OCR 2, own input size | all | 4 | 4 | 0 | 0 | 0 | 38 |
| Chandra OCR 2, 200 dpi page | test | 8 | 7 | 1 | 0 | 0 | 52 |
| Chandra OCR 2, 200 dpi page | dev | 2 | 2 | 0 | 0 | 0 | 9 |
| Chandra OCR 2, 200 dpi page | all | 10 | 9 | 1 | 0 | 0 | 61 |

## Confidence tiers on the delivered output (test split, 22 filings)

| Output | Figures | Wrong | Error rate | HIGH (wrong) | MEDIUM (wrong) | LOW (wrong) | Errors caught by reviewing LOW | …LOW + MEDIUM | Accepted with every error caught |
|---|---:|---:|---:|---|---|---|---:|---:|---:|
| dots.mocr pipeline, seed 0 | 4,994 | 29 | 0.6% | 90.8% (0) | 7.6% (11) | 1.6% (18) | 62.1% | 100.0% | 90.8% |
| dots.mocr pipeline, seed 1 | 4,928 | 31 | 0.6% | 91.3% (0) | 7.1% (11) | 1.6% (20) | 64.5% | 100.0% | 91.3% |
| dots.mocr pipeline, seed 2 | 4,884 | 35 | 0.7% | 91.2% (0) | 7.2% (14) | 1.6% (21) | 60.0% | 100.0% | 91.2% |
| Chandra OCR 2, own input size | 4,938 | 22 | 0.4% | 90.9% (0) | 7.7% (13) | 1.4% (9) | 40.9% | 100.0% | 91.5% |

Error classes (test split):

| Output | Misread digit | Separator/scale | Other |
|---|---:|---:|---:|
| dots.mocr pipeline, seed 0 | 14 | 9 | 6 |
| dots.mocr pipeline, seed 1 | 16 | 9 | 6 |
| dots.mocr pipeline, seed 2 | 19 | 9 | 7 |
| Chandra OCR 2, own input size | 12 | 10 | 0 |

## The same rule on the other splits

| Output | Split | Figures | Wrong | Error rate | HIGH share | Wrong in HIGH | Errors caught by reviewing LOW + MEDIUM |
|---|---|---:|---:|---:|---:|---:|---:|
| dots.mocr pipeline, seed 0 | dev | 2,539 | 34 | 1.3% | 91.2% | 0 | 100.0% |
| dots.mocr pipeline, seed 0 | all | 7,533 | 63 | 0.8% | 90.9% | 0 | 100.0% |
| dots.mocr pipeline, seed 1 | dev | 2,453 | 34 | 1.4% | 90.9% | 0 | 100.0% |
| dots.mocr pipeline, seed 1 | all | 7,381 | 65 | 0.9% | 91.2% | 0 | 100.0% |
| dots.mocr pipeline, seed 2 | dev | 2,471 | 34 | 1.4% | 90.9% | 0 | 100.0% |
| dots.mocr pipeline, seed 2 | all | 7,355 | 69 | 0.9% | 91.1% | 0 | 100.0% |
| Chandra OCR 2, own input size | dev | 2,542 | 2 | 0.1% | 89.2% | 0 | 100.0% |
| Chandra OCR 2, own input size | all | 7,480 | 24 | 0.3% | 90.3% | 0 | 100.0% |

## Adding token probabilities (step 2)

The same outputs re-generated with token log-probabilities returned (a fresh run of the same configuration, since batching changes some outputs). A figure's token probability is the lowest probability among the tokens of its digits. Three rules on the held-out test split: the two-signal rule above; the pilot's rule (a digit token below 0.95 also sends a figure to LOW); and 2 of 3 signals (HIGH needs two of anchored, engine-agreed and token probability at or above a threshold chosen on the development split).

| Output | Rule | Threshold | Figures | Wrong | Accepted (HIGH) | Wrong accepted | Sent to review | Errors caught |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| dots.mocr pipeline, seed 0 (token run) | two signals | – | 4,961 | 29 | 90.4% | 0 | 9.6% | 100.0% |
| dots.mocr pipeline, seed 0 (token run) | pilot rule | 0.95 | 4,961 | 29 | 87.5% | 0 | 12.5% | 100.0% |
| dots.mocr pipeline, seed 0 (token run) | 2 of 3 signals | none safe on dev | | | | | | |
| Chandra OCR 2, own input size (token run) | two signals | – | 4,932 | 25 | 90.7% | 0 | 9.3% | 100.0% |
| Chandra OCR 2, own input size (token run) | pilot rule | 0.95 | 4,932 | 25 | 80.2% | 0 | 19.8% | 100.0% |
| Chandra OCR 2, own input size (token run) | 2 of 3 signals | 0.5 | 4,932 | 25 | 98.6% | 14 | 1.4% | 44.0% |

Separation by token probability alone (area under the ROC curve, wrong against correct figures; 0.5 = no information) and the share of figures whose digits were found in the token stream:

| Output | AUROC test | AUROC dev | Figures with token probabilities (test) |
|---|---:|---:|---:|
| dots.mocr pipeline, seed 0 (token run) | 0.826 | 0.617 | 99.9% |
| Chandra OCR 2, own input size (token run) | 0.811 | 0.954 | 99.9% |

**Reading.** Token probabilities separate wrong from correct figures only moderately, and the costliest misreads are confident ones: decimal-separator confusions on per-unit values (2.8374 read as 28,374) score above 0.99. The pilot's rule costs review time without catching anything the two structural signals miss. Promoting figures on token probability is unsafe: for dots.mocr no threshold kept the development split's errors out; for Chandra OCR 2 the development split holds only 2 errors, and the threshold chosen there let 14 wrong figures through on the test split. On this benchmark, anchoring and engine agreement do the work; token probabilities are at most a tie-breaker inside the review queue.

Wrong figures accepted under 2 of 3 signals (test): alahli_global_trade_fund_H1-2023_p03 27,748 (p=0.996, separator/scale); alahli_global_trade_fund_H1-2023_p03 28,374 (p=0.998, separator/scale); blom_saudi_fund_FY2022_p04 255,967 (p=0.835, separator/scale); blom_saudi_fund_FY2022_p04 255,556 (p=0.991, separator/scale); nama_FY2024_p08 6,670 (p=0.992, separator/scale); riyad_aliemar_fund_FY2023_p06 44,306,994 (p=0.998, separator/scale); riyad_aliemar_fund_FY2023_p06 82,465,938 (p=0.998, separator/scale); saudi_re_FY2024_p09 440,111,424 (p=0.847, misread digit); saudi_re_FY2024_p11 1,015,037 (p=0.562, misread digit); saudi_re_FY2024_p11 1,015,037 (p=0.562, misread digit); saudi_re_FY2024_p11 82,029 (p=0.731, misread digit); saudi_re_FY2024_p11 82,029 (p=0.731, misread digit); sedco_capital_reit_FY2022_p07 88,486 (p=0.938, separator/scale); sedco_capital_reit_FY2022_p07 84,885 (p=0.999, separator/scale)

Wrong figures in the HIGH tier: none, in any split or configuration.

![Risk–coverage](figures/risk_coverage.png)

## Limitations

- **Value-level scoring.** A figure counts as correct when its value occurs in the filing's ground truth; a right value in the wrong row or column, or a misread that happens to equal another figure of the filing, is not caught. Row recall in `RESULTS.md` covers placement.
- **Omissions are out of scope here.** Per-figure confidence can only rank figures that were emitted. Dropped rows and columns are found by the structure check and by printed totals that no longer reconcile (the flagged totals above).
- **Figure filter.** Figures of 1,000 or more, or with decimals (97.0% of the test split's non-zero ground-truth figures); small integers are left out because chance matches with note references and units are common.
- **Repairs can hurt.** Three repairs across all configurations broke a correct figure: an earnings-per-share line (−1.8 → 0) pulled into a sum by dots.mocr seeds 1 and 2 on Herfy, and one wrong-cell repair by Chandra OCR 2 at 200 dpi on Maadaniyah. Excluding per-share lines from sum checks would prevent the first; any such change should be tuned on the development split only.
- **Engine agreement uses Chandra OCR 2 and dots.mocr as each other's second reader.** Both are self-hosted; a hosted second reader would defeat the purpose for sensitive documents.

