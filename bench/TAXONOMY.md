# Failure taxonomy (all 32 filings)

Counted with fixed, automatic rules; definitions in the header of `bench/taxonomy.py`. dots.mocr is shown for seed 0. Totals: 158 statement pages, 156 statements.

## Output-level failures (pages)

| System | Loop | Output cap hit | No figures | of which empty table | Unrelated figures |
|---|---:|---:|---:|---:|---:|
| Mistral OCR | 1 | 0 | 0 | 0 | 0 |
| Cohere Parse | 0 | 0 | 1 | 0 | 0 |
| dots.mocr (pipeline) | 2 | 0 | 1 | 0 | 2 |
| Chandra OCR 2 | 0 | 0 | 0 | 0 | 0 |
| LandingAI ADE | 0 | 0 | 0 | 0 | 1 |
| dots.mocr (out of the box) | 3 | 0 | 1 | 0 | 3 |
| Qwen3.6-27B | 23 | 23 | 15 | 11 | 2 |
| Persian–Arabic line OCR | 0 | 0 | 0 | 0 | 0 |
| Qwen3.8-27B (self-hosted) | 2 | 0 | 1 | 0 | 0 |
| Surya OCR 2 | 3 | 0 | 13 | 10 | 1 |
| Chandra OCR 1 | 16 | 4 | 15 | 0 | 0 |
| Qwen3.8-27B (API) | 6 | 6 | 5 | 5 | 5 |
| Qwen3-VL-32B (FP8) | 3 | 0 | 1 | 1 | 5 |
| PaddleOCR PP-OCRv5 Arabic | 0 | 0 | 1 | 0 | 2 |
| Nanonets-OCR2 | 28 | 9 | 30 | 21 | 6 |
| PaddleOCR-VL-1.6 | 19 | 0 | 20 | 0 | 81 |
| ERNIE 4.5 VL | 4 | 0 | 19 | 11 | 91 |
| Command A Vision | 16 | 13 | 69 | 38 | 45 |
| Nemotron Nano 12B VL | 102 | 6 | 88 | 2 | 54 |
| Qari-OCR v0.3 | 102 | 1 | 141 | 0 | 9 |

## Structure failures (statements)

| System | Omission (≥20% of figures missing) | Misplaced rows | Labels dropped | Labels invented | Reversed labels |
|---|---:|---:|---:|---:|---:|
| Mistral OCR | 3 | 0 | 8 | 0 | 0 |
| Cohere Parse | 6 | 2 | 1 | 1 | 0 |
| dots.mocr (pipeline) | 7 | 0 | 24 | 0 | 0 |
| Chandra OCR 2 | 4 | 1 | 0 | 0 | 0 |
| LandingAI ADE | 2 | 0 | 0 | 0 | 0 |
| dots.mocr (out of the box) | 11 | 1 | 29 | 0 | 0 |
| Qwen3.6-27B | 27 | 3 | 2 | 2 | 0 |
| Persian–Arabic line OCR | 45 | 0 | 0 | 0 | 0 |
| Qwen3.8-27B (self-hosted) | 56 | 1 | 0 | 0 | 0 |
| Surya OCR 2 | 53 | 0 | 7 | 0 | 0 |
| Chandra OCR 1 | 47 | 1 | 9 | 0 | 0 |
| Qwen3.8-27B (API) | 73 | 0 | 0 | 0 | 0 |
| Qwen3-VL-32B (FP8) | 65 | 1 | 0 | 0 | 0 |
| PaddleOCR PP-OCRv5 Arabic | 109 | 0 | 0 | 0 | 0 |
| Nanonets-OCR2 | 98 | 1 | 11 | 0 | 0 |
| PaddleOCR-VL-1.6 | 125 | 0 | 3 | 0 | 0 |
| ERNIE 4.5 VL | 128 | 0 | 2 | 13 | 0 |
| Command A Vision | 141 | 1 | 11 | 13 | 0 |
| Nemotron Nano 12B VL | 142 | 0 | 14 | 0 | 0 |
| Qari-OCR v0.3 | 154 | 1 | 1 | 2 | 0 |

## Reading errors (figures) and digit script

Counts of emitted figures; rates are per 1,000 emitted figures. Digit pairs are (printed → read), Western digits shown.

| System | Emitted figures | One-digit misreads | per 1,000 | Separator/scale | Reversed digits | Top digit confusions | Figure recall: Arabic-Indic filings | Western-digit filings |
|---|---:|---:|---:|---:|---:|---|---:|---:|
| Mistral OCR | 7,525 | 7 | 0.9 | 14 | 0 | 9→2 (2), 1→6 (1), 3→8 (1), 2→3 (1) | 99.0% | 91.7% |
| Cohere Parse | 7,615 | 13 | 1.7 | 16 | 0 | 5→0 (4), 3→2 (1), 3→8 (1), 3→7 (1) | 98.5% | 95.7% |
| dots.mocr (pipeline) | 7,660 | 17 | 2.2 | 24 | 0 | 5→0 (12), 3→8 (1), 2→7 (1) | 98.0% | 92.7% |
| Chandra OCR 2 | 7,674 | 19 | 2.5 | 15 | 0 | 5→0 (3), 3→2 (3), 8→1 (2), 3→8 (1) | 97.6% | 100.0% |
| LandingAI ADE | 7,773 | 47 | 6.0 | 22 | 0 | 5→0 (10), 7→2 (3), 6→9 (2), 2→0 (2) | 97.0% | 99.2% |
| dots.mocr (out of the box) | 7,605 | 22 | 2.9 | 30 | 0 | 5→0 (12), 3→8 (1), 2→7 (1) | 96.2% | 92.8% |
| Qwen3.6-27B | 6,482 | 172 | 26.5 | 11 | 34 | 3→2 (34), 5→0 (7), 6→2 (6), 6→1 (5) | 86.0% | 60.6% |
| Persian–Arabic line OCR | 7,794 | 681 | 87.4 | 43 | 0 | 3→2 (121), 3→4 (29), 2→3 (22), 6→7 (21) | 78.1% | 99.5% |
| Qwen3.8-27B (self-hosted) | 7,502 | 1024 | 136.5 | 11 | 0 | 5→0 (283), 6→7 (236), 6→2 (82), 3→2 (50) | 73.8% | 91.2% |
| Surya OCR 2 | 5,959 | 42 | 7.0 | 11 | 0 | 3→2 (10), 2→3 (4), 5→0 (4), 6→2 (3) | 70.6% | 86.0% |
| Chandra OCR 1 | 6,010 | 98 | 16.3 | 15 | 0 | 3→2 (15), 6→2 (10), 2→3 (6), 6→3 (6) | 68.4% | 89.6% |
| Qwen3.8-27B (API) | 7,212 | 1007 | 139.6 | 17 | 0 | 5→0 (191), 6→2 (131), 6→7 (127), 3→2 (59) | 68.2% | 79.6% |
| Qwen3-VL-32B (FP8) | 6,570 | 667 | 101.5 | 20 | 0 | 5→0 (178), 6→7 (142), 2→7 (91), 3→2 (30) | 66.3% | 81.0% |
| PaddleOCR PP-OCRv5 Arabic | 7,502 | 1158 | 154.4 | 83 | 0 | 5→0 (383), 6→7 (37), 3→2 (20), 2→3 (6) | 57.6% | 95.4% |
| Nanonets-OCR2 | 7,723 | 835 | 108.1 | 20 | 0 | 3→2 (230), 5→0 (91), 0→5 (40), 7→2 (30) | 37.6% | 84.4% |
| PaddleOCR-VL-1.6 | 6,544 | 506 | 77.3 | 101 | 1 | 6→3 (61), 4→6 (45), 2→3 (35), 6→7 (20) | 5.5% | 99.4% |
| ERNIE 4.5 VL | 4,948 | 226 | 45.7 | 29 | 1 | 5→0 (19), 2→3 (14), 2→0 (12), 2→7 (8) | 1.6% | 87.2% |
| Command A Vision | 3,897 | 165 | 42.3 | 73 | 9 | 0→2 (15), 1→2 (12), 6→2 (11), 0→5 (10) | 0.4% | 68.8% |
| Nemotron Nano 12B VL | 5,624 | 87 | 15.5 | 39 | 1 | 6→7 (42), 4→1 (6), 3→4 (3), 8→0 (3) | 0.2% | 39.1% |
| Qari-OCR v0.3 | 1,799 | 11 | 6.1 | 7 | 0 | 7→9 (2), 1→8 (2), 7→8 (2) | 0.1% | 11.6% |

Across all systems, one-digit substitutions by digit pair (printed → read): 5→0 1232 (26%), 6→7 644 (14%), 3→2 596 (13%), 6→2 271 (6%), 2→7 170 (4%), 2→3 160 (3%), 6→3 117 (2%), 0→5 115 (2%).

## Examples (up to two per system and category)

- **loop**: dots.mocr (out of the box): al_rajhi_FY2024_p12; dots.mocr (out of the box): mesc_H1-2023_p04; dots.mocr (pipeline): al_rajhi_FY2024_p12; dots.mocr (pipeline): mesc_H1-2023_p04; Chandra OCR 1: alahli_global_trade_fund_H1-2023_p06; Chandra OCR 1: alinma_tokio_marine_FY2022_p11; Nanonets-OCR2: al_khodari_FY2018_p10; Nanonets-OCR2: al_rajhi_FY2024_p12 …
- **unrelated**: dots.mocr (out of the box): bishah_FY2016_p04; dots.mocr (out of the box): bishah_FY2016_p05; dots.mocr (pipeline): bishah_FY2016_p04; dots.mocr (pipeline): bishah_FY2016_p05; Nanonets-OCR2: alif_meem_yaa_FY2023_p07; Nanonets-OCR2: bahri_FY2024_p10; Qwen3-VL-32B (FP8): bishah_FY2016_p05; Qwen3-VL-32B (FP8): bishah_FY2016_p06 …
- **no figures**: dots.mocr (out of the box): mesc_H1-2023_p04; dots.mocr (pipeline): mesc_H1-2023_p04; Chandra OCR 1: al_khodari_FY2018_p08; Chandra OCR 1: alahli_global_trade_fund_H1-2023_p06; Nanonets-OCR2: al_khodari_FY2018_p09; Nanonets-OCR2: al_khodari_FY2018_p11; Qwen3-VL-32B (FP8): aramco_FY2024_p15; Qwen3.8-27B (self-hosted): snb_FY2024_p15 …
- **labels dropped**: dots.mocr (out of the box): al_khodari_FY2018 s1; dots.mocr (out of the box): al_khodari_FY2018 s2; dots.mocr (pipeline): al_khodari_FY2018 s1; dots.mocr (pipeline): al_khodari_FY2018 s2; Chandra OCR 1: al_rajhi_FY2024 s1; Chandra OCR 1: alinma_tokio_marine_FY2022 s1; Nanonets-OCR2: almarai_FY2024 s4; Nanonets-OCR2: arabian_drilling_FY2024 s1 …
- **omission**: dots.mocr (out of the box): al_rajhi_FY2024 s4 (changes_in_equity); dots.mocr (out of the box): alahli_global_trade_fund_H1-2023 s1 (financial_position); dots.mocr (pipeline): al_rajhi_FY2024 s4 (changes_in_equity); dots.mocr (pipeline): alahli_global_trade_fund_H1-2023 s1 (financial_position); Chandra OCR 2: alahli_global_trade_fund_H1-2023 s1 (financial_position); Chandra OCR 2: othaim_FY2024 s1 (financial_position); Chandra OCR 1: al_khodari_FY2018 s1 (financial_position); Chandra OCR 1: al_khodari_FY2018 s3 (changes_in_equity) …
- **misplaced**: dots.mocr (out of the box): othaim_FY2024 s6 (other); Chandra OCR 2: saudi_re_FY2024 s3 (comprehensive_income); Chandra OCR 1: saudi_re_FY2024 s1 (financial_position); Nanonets-OCR2: blom_saudi_fund_FY2022 s3 (changes_in_net_assets); Qwen3-VL-32B (FP8): nama_FY2024 s5 (other); Qwen3.8-27B (self-hosted): sedco_capital_reit_FY2022 s3 (changes_in_net_assets); Qari-OCR v0.3: aramco_FY2023 s1 (income); Cohere Parse: saudi_re_FY2024 s4 (changes_in_equity) …
- **budget**: Chandra OCR 1: alahli_global_trade_fund_H1-2023_p06; Chandra OCR 1: alinma_tokio_marine_FY2022_p11; Nanonets-OCR2: alif_meem_yaa_FY2023_p07; Nanonets-OCR2: almarai_FY2024_p10; Nemotron Nano 12B VL: al_khodari_FY2018_p08; Nemotron Nano 12B VL: alinma_tokio_marine_FY2022_p11; Qari-OCR v0.3: blom_saudi_fund_FY2022_p05; Qwen3.6-27B: almarai_FY2024_p09 …
- **skeleton**: Nanonets-OCR2: al_khodari_FY2018_p09; Nanonets-OCR2: al_khodari_FY2018_p11; Qwen3-VL-32B (FP8): aramco_FY2024_p15; Nemotron Nano 12B VL: bank_aljazira_FY2024_p09; Nemotron Nano 12B VL: othaim_FY2024_p08; Surya OCR 2: almarai_FY2024_p12; Surya OCR 2: bahri_FY2024_p07; Qwen3.6-27B: almarai_FY2024_p11 …
- **labels invented**: Qari-OCR v0.3: bishah_FY2016 s4; Qari-OCR v0.3: snb_FY2024 s5; Cohere Parse: cenomi_retail_FY2024 s1; Qwen3.6-27B: arabian_drilling_FY2024 s5; Qwen3.6-27B: blom_saudi_fund_FY2022 s3; ERNIE 4.5 VL: al_rajhi_FY2024 s4; ERNIE 4.5 VL: aramco_FY2023 s2; Command A Vision: alahli_global_trade_fund_H1-2023 s2 …
