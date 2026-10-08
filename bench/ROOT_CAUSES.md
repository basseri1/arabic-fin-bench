# Root causes of the fact errors

Method: header of `bench/root_causes.py`. Common base of Table 10 (3,878 figures, test split).

## 1. Parsing: one parser per output format

| System | Output format | Complete | No row | Wrong row | No period | Wrong period | Value wrong or missing |
|---|---|---|---|---|---|---|---|
| Cohere Parse | HTML tables | 3541 → 3604 | 136 | 7 → 6 | 58 → 27 | 31 → 0 | 105 |
| Mistral OCR | Markdown tables | 3124 | 256 | 332 | 64 | 50 | 50 |
| dots.mocr pipeline, seed 0 | HTML tables (layout output) | 2582 | 1180 | 50 | 3 | 3 | 59 |
| Chandra OCR 2, own input size | HTML tables in layout blocks | 2526 | 374 | 548 | 209 | 20 | 194 |

Figures, colspan-only parser → parser with rowspan. Only Cohere Parse changes: its headers span rows (the notes heading covers the year rows), and ignoring rowspan put each year over the wrong column.

## 2. Rows without a label

| System | Rows without a label | Breakdown |
|---|---:|---|
| Cohere Parse | 64 | no label in the output row: 64 |
| Mistral OCR | 231 | no label in the output row: 227; label of this line on its own row just above: 4 |
| dots.mocr pipeline, seed 0 | 1162 | no label in the output row: 1150; label of this line on its own row just above: 10; Arabic text in the row, not taken as a label: 2 |
| Chandra OCR 2, own input size | 317 | no label in the output row: 283; label of this line on its own row just above: 24; Arabic text in the row, not taken as a label: 10 |

## 3. What starts a run of shifted labels

| System | Runs | Breakdown |
|---|---:|---|
| Cohere Parse | 3 | neither: 2 (67%); a label on its own row just above (wrapped or split label): 1 (33%) |
| Mistral OCR | 47 | figures written on a heading's row: 25 (53%); a label on its own row just above (wrapped or split label): 13 (28%); neither: 7 (15%); a heading on its own row just above: 2 (4%) |
| dots.mocr pipeline, seed 0 | 17 | figures written on a heading's row: 9 (53%); a label on its own row just above (wrapped or split label): 4 (24%); neither: 3 (18%); a heading on its own row just above: 1 (6%) |
| Chandra OCR 2, own input size | 80 | figures written on a heading's row: 36 (45%); a label on its own row just above (wrapped or split label): 29 (36%); neither: 15 (19%) |

## 4. Period errors

| System | Figures | Breakdown |
|---|---:|---|
| Cohere Parse | 27 | unresolved: no header (none to inherit): 20; unresolved: header names no year: 7 |
| Mistral OCR | 114 | misplaced: header year maps to another period: 50; unresolved: no header (none to inherit): 32; unresolved: header names no year: 28; unresolved: header years do not line up with the columns of figures: 4 |
| dots.mocr pipeline, seed 0 | 6 | misplaced: header year maps to another period: 2; unresolved: header year maps to another period: 1; misplaced: header years do not line up with the columns of figures: 1; unresolved: header years do not line up with the columns of figures: 1; unresolved: two printed columns share a year the header does not separate: 1 |
| Chandra OCR 2, own input size | 229 | unresolved: no header (none to inherit): 114; unresolved: two printed columns share a year the header does not separate: 76; unresolved: header names no year: 18; misplaced: no header (none to inherit): 14; misplaced: header year maps to another period: 6; unresolved: header years do not line up with the columns of figures: 1 |

## 5. The way the model is run

| Run | Setting | Complete | No row | Wrong row | No period | Wrong period | Value wrong or missing |
|---|---|---:|---:|---:|---:|---:|---:|
| dots_mocr_plain_s0 | 200 dpi page | 61.4% | 33.5% | 1.3% | 0.4% | 0.2% | 3.3% |
| dots_mocr_plain_s0_bm | 200 dpi + band-merge | 61.4% | 33.5% | 1.3% | 0.4% | 0.2% | 3.3% |
| dots_mocr_clahe_s0_raw | CLAHE | 66.3% | 27.6% | 1.3% | 0.6% | 0.1% | 4.0% |
| dots_mocr_clahe_s0 | CLAHE + structure retry | 66.5% | 30.4% | 1.3% | 0.1% | 0.1% | 1.6% |
| dots_mocr_clahe_s0_bm | CLAHE + retry + band-merge | 66.5% | 30.4% | 1.3% | 0.1% | 0.1% | 1.6% |
| dots_mocr_clahe_s0_bm_ver | adopted (+ verification) | 66.6% | 30.4% | 1.3% | 0.1% | 0.1% | 1.5% |
| chandra2_plain | 200 dpi page | 63.9% | 8.2% | 12.9% | 3.6% | 2.1% | 9.3% |
| chandra2_plain_ver | 200 dpi + verification | 64.0% | 8.3% | 13.0% | 3.5% | 2.1% | 9.1% |
| chandra2_chandra_cap | own input size | 65.0% | 9.6% | 14.1% | 5.4% | 0.5% | 5.3% |
| chandra2_chandra_cap_ver | own input size + verification | 65.1% | 9.6% | 14.1% | 5.4% | 0.5% | 5.2% |

dots.mocr: share of the printed labels found in its tables, on the statement pages where the adopted output has fewer than half:

| Page | 200 dpi page | 200 dpi + band-merge | CLAHE | CLAHE + structure retry | CLAHE + retry + band-merge | adopted (+ verification) |
|---|---:|---:|---:|---:|---:|---:|
| al_khodari_FY2018_p08 (financial_position) | 0.07 | 0.07 | 0.07 | 0.07 | 0.07 | 0.07 |
| al_khodari_FY2018_p09 (income_and_comprehensive_income) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| alif_meem_yaa_FY2023_p09 (cash_flows) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| alinma_tokio_marine_FY2022_p07 (financial_position) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| almarai_FY2024_p08 (financial_position) | 1.00 | 1.00 | 1.00 | 0.03 | 0.03 | 0.03 |
| almarai_FY2024_p13 (cash_flows) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| bahri_FY2024_p10 (cash_flows) | 0.08 | 0.08 | 0.06 | 0.06 | 0.06 | 0.06 |
| bahri_FY2024_p10 (other) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| cenomi_retail_FY2024_p13 (cash_flows) | 0.02 | 0.02 | 0.04 | 0.04 | 0.04 | 0.04 |
| cenomi_retail_FY2024_p14 (cash_flows) | 0.24 | 0.24 | 0.24 | 0.24 | 0.24 | 0.24 |
| halwani_FY2024_p07 (comprehensive_income) | 0.18 | 0.18 | 0.18 | 0.18 | 0.18 | 0.18 |
| halwani_FY2024_p09 (financial_position) | 0.42 | 0.42 | 0.42 | 0.42 | 0.42 | 0.42 |
| halwani_FY2024_p13 (cash_flows) | 0.47 | 0.47 | 0.00 | 0.00 | 0.00 | 0.00 |
| halwani_FY2024_p13 (other) | 1.00 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| kingdom_holding_FY2024_p09 (comprehensive_income) | 0.30 | 0.30 | 0.40 | 0.40 | 0.40 | 0.40 |
| liva_FY2024_p07 (financial_position) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| nama_FY2024_p07 (financial_position) | 1.00 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| othaim_FY2024_p07 (financial_position) | 0.06 | 0.06 | 0.06 | 0.06 | 0.06 | 0.06 |
| othaim_FY2024_p11 (cash_flows) | 0.02 | 0.02 | 0.02 | 0.02 | 0.02 | 0.02 |
| othaim_FY2024_p12 (cash_flows) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| othaim_FY2024_p12 (other) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| riyad_aliemar_fund_FY2023_p08 (changes_in_net_assets) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| sedco_capital_reit_FY2022_p08 (income_and_comprehensive_income) | 1.00 | 1.00 | 0.21 | 0.21 | 0.21 | 0.21 |
| taiba_FY2024_p09 (financial_position) | 0.15 | 0.15 | 0.15 | 0.15 | 0.15 | 0.15 |
| taiba_FY2024_p10 (income) | 1.00 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| taiba_FY2024_p11 (comprehensive_income) | 0.40 | 0.40 | 0.40 | 0.40 | 0.40 | 0.40 |
| taiba_FY2024_p14 (cash_flows) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| taiba_FY2024_p14 (other) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

On 28 such pages, 5 had most labels in an earlier stage (lost to CLAHE or to the structure retry, which keeps the attempt with the most figures and never looks at labels); on the others no configuration writes the labels.
