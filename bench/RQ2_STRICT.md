# RQ2, strict: facts in context, components, missing information and blind spots

Method: header of `bench/rq2_strict.py`. Held-out test split (22 filings) unless stated. A figure is a **correct fact** when the output's own row label and column header resolve to the ground-truth cell and the signed value equals it (one to one).

Column identity is assessed in statements whose columns are periods; in equity matrices, whose two-level component headers could not be resolved reliably, only the row is assessed (this restriction was added after inspecting test outputs of a commercial reference; it can only lower error counts).

Context thresholds chosen on the development split: row-label similarity 90, column-header similarity 70 (grid of 70/80/90 each; objective: unique-value figures resolved to their own cell minus those resolved elsewhere).

## 1. Facts versus values (rule fixed in the pilot: arithmetic + agreement)

| Output | Figures | Value right | Complete, correct facts | Correct, row not stated | Correct, column not assessed | Column not stated | Wrong column | Wrong row | Sign | Wrong value |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| dots.mocr pipeline, seed 0 | 4,994 | 99.4% | 51.7% | 23.8% | 8.1% | 14.5% | 0.1% | 1.2% | 0.0% | 0.6% |
| dots.mocr pipeline, seed 1 | 4,928 | 99.4% | 50.1% | 26.3% | 8.2% | 13.5% | 0.1% | 1.3% | 0.0% | 0.6% |
| dots.mocr pipeline, seed 2 | 4,884 | 99.3% | 50.9% | 25.2% | 8.3% | 13.2% | 0.0% | 1.5% | 0.0% | 0.7% |
| Chandra OCR 2, own input size | 4,938 | 99.6% | 51.2% | 7.7% | 7.6% | 21.4% | 0.4% | 11.3% | 0.1% | 0.4% |

Resolver check on the test split (figures whose value occurs once in the filing, so their cell is known): dots.mocr pipeline, seed 0: 2561 resolved to their cell, 27 elsewhere, 121 unresolved; dots.mocr pipeline, seed 1: 2549 resolved to their cell, 36 elsewhere, 89 unresolved; dots.mocr pipeline, seed 2: 2537 resolved to their cell, 28 elsewhere, 97 unresolved; Chandra OCR 2, own input size: 2015 resolved to their cell, 407 elsewhere, 195 unresolved.

### 1b. Fact-level reading of the leading systems (all emitted figures, test split)

| System | Figures | Value right | Complete, correct facts | Correct, row not stated | Correct, column not assessed | Column not stated | Wrong column | Wrong row | Sign | Wrong value | Ground-truth figures recovered as complete facts |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Mistral OCR | 4,894 | 99.7% | 63.8% | 5.2% | 6.7% | 14.1% | 1.0% | 8.8% | 0.0% | 0.3% | 61.3% |
| Cohere Parse | 4,984 | 99.6% | 72.3% | 2.7% | 22.9% | 1.2% | 0.0% | 0.4% | 0.0% | 0.4% | 70.7% |
| LandingAI ADE | 4,986 | 96.7% | 69.3% | 3.1% | 12.1% | 11.2% | 0.0% | 1.0% | 0.0% | 3.3% | 67.8% |
| dots.mocr pipeline, seed 0 | 4,994 | 99.4% | 51.7% | 23.8% | 8.1% | 14.5% | 0.1% | 1.2% | 0.0% | 0.6% | 50.7% |
| Chandra OCR 2, own input size | 4,938 | 99.6% | 51.2% | 7.7% | 7.6% | 21.4% | 0.4% | 11.3% | 0.1% | 0.4% | 49.6% |

## 2. Measures for the rule fixed in the pilot (strict, test split)

| Output | Coverage | Accepted-fact error (95% bound: naive / clustered) | Of which value errors | Accepted, context not stated | Filings with an accepted error | Correct automatic recovery (complete / value with all stated context right) | Error-detection recall | Review workload |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| dots.mocr pipeline, seed 0 | 90.8% | 1.26% (57; 1.57% / 1.89%) | 0.00% | 45.6% | 14 of 22 | 47.3% / 75.0% | 40.0% | 9.0% |
| dots.mocr pipeline, seed 1 | 91.3% | 1.16% (52; 1.45% / 1.83%) | 0.00% | 47.7% | 12 of 22 | 45.2% / 75.0% | 46.9% | 8.4% |
| dots.mocr pipeline, seed 2 | 91.2% | 1.57% (70; 1.91% / 2.37%) | 0.00% | 46.6% | 13 of 22 | 45.3% / 74.2% | 37.5% | 8.4% |
| Chandra OCR 2, own input size | 90.9% | 12.05% (541; 12.88% / 16.63%) | 0.00% | 35.2% | 20 of 22 | 46.5% / 59.4% | 10.0% | 8.8% |

Value level (the earlier scoring): no accepted figure has a wrong value; 95% upper bound, naive / corrected for clustering of value errors by filing: dots.mocr pipeline, seed 0: 0.066% / 0.504% (intra-filing correlation 0.032, design effect 7.6); dots.mocr pipeline, seed 1: 0.067% / 0.505% (intra-filing correlation 0.032, design effect 7.6); dots.mocr pipeline, seed 2: 0.067% / 0.534% (intra-filing correlation 0.035, design effect 8.0); Chandra OCR 2, own input size: 0.067% / 0.219% (intra-filing correlation 0.011, design effect 3.3).

Accepted errors by kind: dots.mocr pipeline, seed 0: wrong column 2, wrong row 55; dots.mocr pipeline, seed 1: wrong column 2, wrong row 50; dots.mocr pipeline, seed 2: wrong column 2, wrong row 68; Chandra OCR 2, own input size: sign 1, wrong column 13, wrong row 527.

## 3. Each component separately (token re-runs, test split)

| Output | Rule | Coverage | Accepted-fact error | 95% bound, clustered | Accepted, context not stated | Recovery | Detection recall | Omissions detected | Review workload | Error at 10% review |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| dots.mocr pipeline, seed 0 (token run) | accept everything | 100.0% | 1.91% (95) | 2.67% | 47.5% | 49.2% | 0.0% | 0 of 16 | 0.0% | – |
| dots.mocr pipeline, seed 0 (token run) | arithmetic only | 91.7% | 1.30% (59) | 1.96% | 47.1% | 46.1% | 37.9% | 0 of 16 | 8.0% | 1.30% |
| dots.mocr pipeline, seed 0 (token run) | agreement only | 98.0% | 1.54% (75) | 2.18% | 47.5% | 48.7% | 21.1% | 0 of 16 | 1.9% | 1.54% |
| dots.mocr pipeline, seed 0 (token run) | arithmetic + agreement (rule fixed in the pilot) | 90.4% | 1.27% (57) | 1.88% | 47.0% | 45.6% | 40.0% | 0 of 16 | 9.3% | 1.27% |
| dots.mocr pipeline, seed 0 (token run) | + completeness checks | 28.2% | 2.51% (35) | 3.83% | 15.8% | 22.4% | 63.2% | 9 of 16 | 72.5% | 1.68% |
| dots.mocr pipeline, seed 0 (token run) | + context agreement | 18.7% | 1.94% (18) | 3.28% | 14.0% | 15.3% | 81.1% | 9 of 16 | 81.7% | 1.68% |
| dots.mocr pipeline, seed 0 (token run) | + token probabilities | 18.4% | 1.54% (14) | 2.82% | 13.4% | 15.2% | 85.3% | 9 of 16 | 82.0% | 1.68% |
| Chandra OCR 2, own input size (token run) | accept everything | 100.0% | 11.78% (581) | 16.05% | 36.7% | 49.9% | 0.0% | 0 of 16 | 0.0% | – |
| Chandra OCR 2, own input size (token run) | arithmetic only | 91.5% | 11.76% (531) | 16.05% | 35.4% | 46.8% | 8.6% | 0 of 16 | 8.2% | 11.76% |
| Chandra OCR 2, own input size (token run) | agreement only | 98.8% | 11.41% (556) | 16.05% | 36.5% | 49.8% | 4.3% | 0 of 16 | 1.1% | 11.41% |
| Chandra OCR 2, own input size (token run) | arithmetic + agreement (rule fixed in the pilot) | 90.7% | 11.58% (518) | 16.05% | 35.2% | 46.7% | 10.8% | 0 of 16 | 9.0% | 11.58% |
| Chandra OCR 2, own input size (token run) | + completeness checks | 50.6% | 18.33% (458) | 24.53% | 11.7% | 34.3% | 21.2% | 11 of 16 | 50.5% | 12.95% |
| Chandra OCR 2, own input size (token run) | + context agreement | 29.9% | 1.29% (19) | 4.28% | 11.6% | 25.2% | 96.7% | 11 of 16 | 70.6% | 13.00% |
| Chandra OCR 2, own input size (token run) | + token probabilities | 27.0% | 1.28% (17) | 4.31% | 12.1% | 22.6% | 97.1% | 11 of 16 | 73.4% | 13.00% |

## 4. Natural failures that can fool both checks (test split)

| Output | Wrong column | …accepted | Wrong row | …accepted | Sign | …accepted | Same wrong value in both engines | …accepted | Statements missing >=30% of figures | …flagged at document level |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| dots.mocr pipeline, seed 0 | 3 | 2 | 62 | 55 | 1 | 0 | 9 | 0 | 3 | 2 |
| dots.mocr pipeline, seed 1 | 3 | 2 | 63 | 50 | 1 | 0 | 9 | 0 | 2 | 1 |
| dots.mocr pipeline, seed 2 | 2 | 2 | 75 | 68 | 0 | 0 | 10 | 0 | 3 | 2 |
| Chandra OCR 2, own input size | 20 | 13 | 556 | 527 | 3 | 1 | 9 | 0 | 8 | 4 |

## 5. Synthetic challenge set (reported separately; real outputs with one injected error each)

| Output | Injected error | Instances | Scored as errors | Accepted, rule fixed in the pilot | Accepted, + completeness | Accepted, + context agreement | Caught at document level |
|---|---|---:|---:|---:|---:|---:|---:|
| dots.mocr pipeline, seed 0 | period swap (one row) | 44 | 44 | 22 | 10 | 1 | – |
| dots.mocr pipeline, seed 0 | period swap (whole table) | 44 | 44 | 44 | 18 | 7 | – |
| dots.mocr pipeline, seed 0 | dropped negative | 44 | 38 | 10 | 3 | 2 | – |
| dots.mocr pipeline, seed 0 | shifted labels | 44 | 44 | 44 | 26 | 2 | – |
| dots.mocr pipeline, seed 0 | same digit error in both engines | 44 | 43 | 0 | 0 | 0 | – |
| dots.mocr pipeline, seed 0 | dropped column | 44 | – | – | – | – | 44 |
| Chandra OCR 2, own input size | period swap (one row) | 44 | 44 | 20 | 13 | 0 | – |
| Chandra OCR 2, own input size | period swap (whole table) | 44 | 44 | 44 | 28 | 6 | – |
| Chandra OCR 2, own input size | dropped negative | 44 | 38 | 10 | 9 | 7 | – |
| Chandra OCR 2, own input size | shifted labels | 44 | 41 | 37 | 25 | 0 | – |
| Chandra OCR 2, own input size | same digit error in both engines | 44 | 42 | 0 | 0 | 0 | – |
| Chandra OCR 2, own input size | dropped column | 44 | – | – | – | – | 43 |

