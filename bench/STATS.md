# Inferential statistics for the research questions

Held-out test split: 22 filings, 107 statements. Scripts: `bench/stats_rq.py`.

## RQ1 — Are the leading on-premises systems non-inferior to the leading hosted services?

Row recall difference (on-premises − hosted) on the same statements; filing-level bootstrap (10,000 resamples of the 22 filings). Non-inferior at a margin of 2 points when the one-sided 95% lower bound exceeds −2 points. The margin was set after the main results were known; the smallest margin each comparison passes is given so that readers can apply their own.

| On-premises | Hosted | Row recall (on-prem / hosted) | Difference | 95% CI, by filing | One-sided 95% lower bound | Non-inferior at 2 points | Smallest margin passed | 95% CI, by statement (for contrast) |
|---|---|---|---:|---|---:|---|---:|---|
| dots.mocr adopted pipeline (3 seeds) | Mistral OCR | 96.4% / 96.8% | -0.36 | -3.24 to 3.58 | -2.86 | no | 2.86 points | -3.24 to 3.24 |
| dots.mocr adopted pipeline (3 seeds) | Cohere Parse | 96.4% / 96.8% | -0.45 | -2.99 to 2.11 | -2.55 | no | 2.55 points | -3.03 to 2.28 |
| dots.mocr adopted pipeline (3 seeds) | LandingAI ADE | 96.4% / 97.7% | -1.36 | -3.99 to 1.60 | -3.60 | no | 3.60 points | -4.22 to 1.34 |
| Chandra OCR 2 (own input size) | Mistral OCR | 95.5% / 96.8% | -1.21 | -7.32 to 4.90 | -6.22 | no | 6.22 points | -7.44 to 4.74 |
| Chandra OCR 2 (own input size) | Cohere Parse | 95.5% / 96.8% | -1.30 | -6.99 to 3.78 | -6.00 | no | 6.00 points | -6.96 to 3.20 |
| Chandra OCR 2 (own input size) | LandingAI ADE | 95.5% / 97.7% | -2.21 | -6.87 to 1.71 | -6.07 | no | 6.07 points | -7.62 to 1.73 |

Differences and bounds are in points of row recall.

### Where the differences come from

Row recall per filing on the 22 held-out filings. A severe failure is a filing below 95% row recall; flagged totals are printed totals that still do not reconcile in the system's own output, computed without ground truth (the arithmetic check works on any output, hosted or not).

| System | Filings at 99% or more | 95–99% | Below 95% (severe) | Worst filing | Severe failures with at least one flagged total |
|---|---:|---:|---:|---:|---:|
| dots.mocr adopted pipeline (3 seeds) | 8 | 9 | 5 | 84.0% | 3 of 5 |
| Chandra OCR 2 (own input size) | 12 | 7 | 3 | 69.8% | 0 of 3 |
| Mistral OCR | 15 | 5 | 2 | 66.0% | 0 of 2 |
| Cohere Parse | 10 | 9 | 3 | 81.2% | 2 of 3 |
| LandingAI ADE | 10 | 10 | 2 | 79.3% | 2 of 2 |

Severe failures: dots.mocr adopted pipeline (3 seeds): al_rajhi_FY2024 91.1% (4 flagged of 48 checked totals), alahli_global_trade_fund_H1-2023 94.9% (0 flagged of 18 checked totals), halwani_FY2024 93.9% (0 flagged of 40 checked totals), othaim_FY2024 89.5% (2 flagged of 56 checked totals), snb_FY2024 84.0% (1 flagged of 58 checked totals); Chandra OCR 2 (own input size): othaim_FY2024 75.9% (0 flagged of 77 checked totals), saudi_re_FY2024 94.6% (0 flagged of 42 checked totals), taiba_FY2024 69.8% (0 flagged of 39 checked totals); Mistral OCR: nama_FY2024 66.0% (0 flagged of 29 checked totals), snb_FY2024 78.0% (0 flagged of 40 checked totals); Cohere Parse: al_khodari_FY2018 94.9% (2 flagged of 84 checked totals), al_rajhi_FY2024 81.2% (6 flagged of 45 checked totals), cenomi_retail_FY2024 90.2% (0 flagged of 49 checked totals); LandingAI ADE: othaim_FY2024 94.2% (3 flagged of 68 checked totals), saudi_re_FY2024 79.3% (3 flagged of 26 checked totals).

Paired by filing (a tie is a difference of at most one row):

| On-premises | Hosted | On-premises better | Tie | Hosted better |
|---|---|---:|---:|---:|
| dots.mocr adopted pipeline (3 seeds) | Mistral OCR | 2 | 13 | 7 |
| dots.mocr adopted pipeline (3 seeds) | Cohere Parse | 6 | 9 | 7 |
| dots.mocr adopted pipeline (3 seeds) | LandingAI ADE | 1 | 15 | 6 |
| Chandra OCR 2 (own input size) | Mistral OCR | 2 | 15 | 5 |
| Chandra OCR 2 (own input size) | Cohere Parse | 6 | 12 | 4 |
| Chandra OCR 2 (own input size) | LandingAI ADE | 2 | 18 | 2 |

### Flagging severe failures without ground truth

Cross-engine row check: a filing is flagged when more than 5% of the rows read by a second, self-hosted engine (Chandra OCR 2 for dots.mocr; the dots.mocr pipeline for every other system) do not appear as a row of the system's output. The 5% threshold was set on the development split, where it flags every severe failure of both self-hosted engines. A flag can also mean the second engine failed; either way the filing goes to review.

| System | Split | Severe failures flagged | Other filings flagged (false alarms) |
|---|---|---:|---:|
| dots.mocr adopted pipeline (3 seeds) | dev | 3 of 3 | 0 of 7 |
| Chandra OCR 2 (own input size) | dev | 1 of 1 | 4 of 9 |
| Mistral OCR | dev | 1 of 1 | 3 of 9 |
| Cohere Parse | dev | 1 of 1 | 3 of 9 |
| LandingAI ADE | dev | 1 of 1 | 3 of 9 |
| dots.mocr adopted pipeline (3 seeds) | test | 5 of 5 | 3 of 17 |
| Chandra OCR 2 (own input size) | test | 2 of 3 | 1 of 19 |
| Mistral OCR | test | 2 of 2 | 1 of 20 |
| Cohere Parse | test | 3 of 3 | 2 of 19 |
| LandingAI ADE | test | 2 of 2 | 1 of 20 |

Severe failures not flagged on the test split: Chandra OCR 2 (own input size): saudi_re_FY2024 (94.6% row recall, 4.7% rows disagreeing).

## RQ2 — How low is the error rate among automatically accepted figures?

HIGH tier = anchored in a reconciling printed total and read identically by the other self-hosted engine (`bench/CONFIDENCE.md`). Exact one-sided 95% upper bound on the error rate among accepted figures; figures are treated as independent, which clustering within filings makes optimistic.

| Output | Split | Accepted figures | Wrong among accepted | Sent to review | 95% upper bound on error rate among accepted |
|---|---|---:|---:|---:|---:|
| dots.mocr pipeline, seed 0 | test | 4,533 | 0 | 9.2% | 0.066% |
| dots.mocr pipeline, seed 0 | all | 6,848 | 0 | 9.1% | 0.044% |
| dots.mocr pipeline, seed 1 | test | 4,499 | 0 | 8.7% | 0.067% |
| dots.mocr pipeline, seed 1 | all | 6,730 | 0 | 8.8% | 0.045% |
| dots.mocr pipeline, seed 2 | test | 4,454 | 0 | 8.8% | 0.067% |
| dots.mocr pipeline, seed 2 | all | 6,700 | 0 | 8.9% | 0.045% |
| Chandra OCR 2, own input size | test | 4,489 | 0 | 9.1% | 0.067% |
| Chandra OCR 2, own input size | all | 6,757 | 0 | 9.7% | 0.044% |
