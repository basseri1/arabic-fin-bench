# Sensitivity of the conclusions to our own thresholds

Each quantity is computed once; the thresholds are then varied around the default values (bold). Method: `bench/sensitivity.py`.

## Verdicts

- **Label match:** the ranking of systems barely moves between thresholds 75 and 95 (Kendall τ 0.85–0.97 against 85). Conclusion unchanged.
- **Taxonomy:** omissions (τ 0.88–1.00), unrelated figures (τ 0.75–1.00), dropped labels (τ 0.94–1.00) and invented labels (τ 0.90–1.00) keep their ranking; the leading systems stay at the low end at every cut-off. Misplaced rows are rare for every system (0–7 statements) and their ranking is not stable (τ down to 0.52): report them as rare, without ranking.
- **Cross-engine row check:** a smooth trade-off, not a knife-edge: 15 of 15 severe failures flagged with 15 false alarms at 3%, 14 with 8 at 5% (the default, set on dev), 13 with 4 at 8%.
- **Severe-failure line:** every leading system has failing filings at 90%, 95% and 98%, so 'no system is uniformly safe' does not depend on the line. The row check catches the large failures (all below 90%) but only a minority of small shortfalls (95–98%): state the detection claim for failures below 95%.
- **Figure filter (RQ2):** no wrong figure reaches the HIGH tier whether figures from 100, 1,000 or 10,000 up are included, and the review share stays at 9–10%. Conclusion unchanged.

## 1. Label match threshold

Label recall (all 32 filings) by fuzzy-match threshold; Kendall τ of the system ranking against the default threshold of 85.

| System | 75 | 80 | **85** | 90 | 95 |
|---|---:|---:|---:|---:|---:|
| dots.mocr (out of the box) | 72.7 | 71.2 | 69.7 | 69.3 | 68.2 |
| dots.mocr (pipeline) | 76.3 | 74.5 | 73.2 | 72.7 | 71.5 |
| Chandra OCR 2 | 98.9 | 98.5 | 97.7 | 97.0 | 94.1 |
| Chandra OCR 1 | 84.3 | 83.3 | 82.3 | 80.9 | 77.0 |
| Nanonets-OCR2 | 73.5 | 72.3 | 70.6 | 69.4 | 65.7 |
| Qwen3-VL-32B (FP8) | 96.6 | 94.8 | 92.6 | 89.3 | 85.9 |
| Qwen3.8-27B (self-hosted) | 97.9 | 97.3 | 96.2 | 95.1 | 92.0 |
| Nemotron Nano 12B VL | 1.1 | 0.7 | 0.5 | 0.3 | 0.2 |
| Qari-OCR v0.3 | 44.6 | 43.4 | 42.0 | 40.8 | 39.2 |
| PaddleOCR-VL-1.6 | 63.2 | 61.1 | 57.7 | 53.8 | 44.1 |
| Surya OCR 2 | 90.8 | 89.9 | 89.0 | 87.9 | 86.7 |
| Persian–Arabic line OCR | 99.5 | 98.6 | 97.1 | 94.7 | 89.2 |
| PaddleOCR PP-OCRv5 Arabic | 99.2 | 98.4 | 97.5 | 96.0 | 90.6 |
| Mistral OCR | 95.4 | 94.8 | 94.1 | 93.6 | 92.9 |
| Cohere Parse | 97.3 | 97.2 | 96.3 | 95.8 | 95.2 |
| LandingAI ADE | 99.6 | 99.1 | 98.4 | 97.7 | 97.1 |
| Qwen3.6-27B | 80.2 | 77.7 | 74.1 | 71.1 | 66.7 |
| Qwen3.8-27B (API) | 93.1 | 92.5 | 91.3 | 89.3 | 85.1 |
| ERNIE 4.5 VL | 36.1 | 29.4 | 23.0 | 18.7 | 15.0 |
| Command A Vision | 1.5 | 0.6 | 0.3 | 0.2 | 0.2 |
| LightOnOCR-3 0.8B | 96.9 | 96.6 | 95.5 | 93.5 | 86.4 |
| LightOnOCR-3 1B | 95.4 | 95.1 | 94.6 | 94.0 | 91.2 |
| LightOnOCR-3 4B | 94.1 | 93.5 | 92.8 | 91.6 | 87.8 |
| nace.ai Parse | 84.4 | 83.1 | 81.7 | 80.5 | 78.8 |
| nace.ai Parse | 84.4 | 83.1 | 81.7 | 80.5 | 78.8 |
| Kendall τ against 85 | 0.93 | 0.97 | 1.00 | 0.96 | 0.85 |

## 2. Taxonomy cut-offs

Counts per system as each cut-off moves (others at their defaults); the default in bold.

**omission** (statements; cut-off om = 0.1, **0.2**, 0.3, 0.5)

| System | 0.1 | 0.2 | 0.3 | 0.5 |
|---|---:|---:|---:|---:|
| dots.mocr (out of the box) | 15 | 11 | 9 | 4 |
| dots.mocr (pipeline) | 10 | 7 | 6 | 5 |
| Chandra OCR 2 | 6 | 4 | 2 | 1 |
| Chandra OCR 1 | 58 | 47 | 41 | 32 |
| Nanonets-OCR2 | 111 | 98 | 86 | 67 |
| Qwen3-VL-32B (FP8) | 99 | 65 | 53 | 33 |
| Qwen3.8-27B (self-hosted) | 92 | 56 | 41 | 25 |
| Nemotron Nano 12B VL | 142 | 142 | 141 | 141 |
| Qari-OCR v0.3 | 154 | 154 | 153 | 153 |
| PaddleOCR-VL-1.6 | 126 | 125 | 125 | 124 |
| Surya OCR 2 | 59 | 53 | 45 | 29 |
| Persian–Arabic line OCR | 93 | 45 | 19 | 3 |
| PaddleOCR PP-OCRv5 Arabic | 123 | 109 | 90 | 43 |
| Mistral OCR | 6 | 3 | 2 | 1 |
| Cohere Parse | 10 | 6 | 5 | 3 |
| LandingAI ADE | 5 | 2 | 1 | 1 |
| Qwen3.6-27B | 37 | 27 | 21 | 19 |
| Qwen3.8-27B (API) | 94 | 73 | 51 | 37 |
| ERNIE 4.5 VL | 128 | 128 | 128 | 128 |
| Command A Vision | 142 | 141 | 137 | 131 |
| LightOnOCR-3 0.8B | 106 | 87 | 78 | 60 |
| LightOnOCR-3 1B | 24 | 15 | 9 | 2 |
| LightOnOCR-3 4B | 26 | 19 | 12 | 5 |
| nace.ai Parse | 37 | 28 | 23 | 18 |
| nace.ai Parse | 37 | 28 | 23 | 18 |
| Kendall τ against the default | 0.96 | 1.00 | 0.96 | 0.88 |

**unrelated** (pages; cut-off un = 0.3, **0.5**, 0.7)

| System | 0.3 | 0.5 | 0.7 |
|---|---:|---:|---:|
| dots.mocr (out of the box) | 3 | 3 | 3 |
| dots.mocr (pipeline) | 2 | 2 | 2 |
| Chandra OCR 2 | 0 | 0 | 0 |
| Chandra OCR 1 | 2 | 0 | 0 |
| Nanonets-OCR2 | 14 | 6 | 5 |
| Qwen3-VL-32B (FP8) | 9 | 5 | 3 |
| Qwen3.8-27B (self-hosted) | 10 | 0 | 0 |
| Nemotron Nano 12B VL | 54 | 54 | 52 |
| Qari-OCR v0.3 | 9 | 9 | 9 |
| PaddleOCR-VL-1.6 | 89 | 81 | 64 |
| Surya OCR 2 | 1 | 1 | 0 |
| Persian–Arabic line OCR | 4 | 0 | 0 |
| PaddleOCR PP-OCRv5 Arabic | 24 | 2 | 0 |
| Mistral OCR | 0 | 0 | 0 |
| Cohere Parse | 0 | 0 | 0 |
| LandingAI ADE | 1 | 1 | 1 |
| Qwen3.6-27B | 3 | 2 | 1 |
| Qwen3.8-27B (API) | 20 | 5 | 0 |
| ERNIE 4.5 VL | 92 | 91 | 87 |
| Command A Vision | 54 | 45 | 39 |
| LightOnOCR-3 0.8B | 28 | 11 | 1 |
| LightOnOCR-3 1B | 1 | 0 | 0 |
| LightOnOCR-3 4B | 0 | 0 | 0 |
| nace.ai Parse | 7 | 5 | 1 |
| nace.ai Parse | 7 | 5 | 1 |
| Kendall τ against the default | 0.75 | 1.00 | 0.80 |

**misplaced** (statements; cut-off mp = 0.7, **0.8**, 0.9)

| System | 0.7 | 0.8 | 0.9 |
|---|---:|---:|---:|
| dots.mocr (out of the box) | 1 | 1 | 2 |
| dots.mocr (pipeline) | 0 | 0 | 1 |
| Chandra OCR 2 | 1 | 1 | 3 |
| Chandra OCR 1 | 0 | 1 | 5 |
| Nanonets-OCR2 | 1 | 1 | 3 |
| Qwen3-VL-32B (FP8) | 1 | 1 | 2 |
| Qwen3.8-27B (self-hosted) | 1 | 1 | 2 |
| Nemotron Nano 12B VL | 0 | 0 | 0 |
| Qari-OCR v0.3 | 1 | 1 | 1 |
| PaddleOCR-VL-1.6 | 0 | 0 | 1 |
| Surya OCR 2 | 0 | 0 | 3 |
| Persian–Arabic line OCR | 0 | 0 | 1 |
| PaddleOCR PP-OCRv5 Arabic | 0 | 0 | 0 |
| Mistral OCR | 0 | 0 | 3 |
| Cohere Parse | 0 | 2 | 2 |
| LandingAI ADE | 0 | 0 | 1 |
| Qwen3.6-27B | 3 | 3 | 7 |
| Qwen3.8-27B (API) | 0 | 0 | 4 |
| ERNIE 4.5 VL | 0 | 0 | 0 |
| Command A Vision | 1 | 1 | 2 |
| LightOnOCR-3 0.8B | 0 | 0 | 1 |
| LightOnOCR-3 1B | 1 | 3 | 6 |
| LightOnOCR-3 4B | 1 | 1 | 4 |
| nace.ai Parse | 0 | 1 | 3 |
| nace.ai Parse | 0 | 1 | 3 |
| Kendall τ against the default | 0.68 | 1.00 | 0.52 |

**labels dropped** (statements; cut-off lr = 0.1, **0.2**, 0.3)

| System | 0.1 | 0.2 | 0.3 |
|---|---:|---:|---:|
| dots.mocr (out of the box) | 24 | 29 | 30 |
| dots.mocr (pipeline) | 19 | 24 | 26 |
| Chandra OCR 2 | 0 | 0 | 0 |
| Chandra OCR 1 | 4 | 9 | 10 |
| Nanonets-OCR2 | 9 | 11 | 14 |
| Qwen3-VL-32B (FP8) | 0 | 0 | 0 |
| Qwen3.8-27B (self-hosted) | 0 | 0 | 0 |
| Nemotron Nano 12B VL | 14 | 14 | 14 |
| Qari-OCR v0.3 | 1 | 1 | 1 |
| PaddleOCR-VL-1.6 | 2 | 3 | 4 |
| Surya OCR 2 | 3 | 7 | 7 |
| Persian–Arabic line OCR | 0 | 0 | 0 |
| PaddleOCR PP-OCRv5 Arabic | 0 | 0 | 0 |
| Mistral OCR | 5 | 8 | 9 |
| Cohere Parse | 0 | 1 | 1 |
| LandingAI ADE | 0 | 0 | 0 |
| Qwen3.6-27B | 1 | 2 | 4 |
| Qwen3.8-27B (API) | 0 | 0 | 0 |
| ERNIE 4.5 VL | 2 | 2 | 2 |
| Command A Vision | 11 | 11 | 11 |
| LightOnOCR-3 0.8B | 0 | 0 | 0 |
| LightOnOCR-3 1B | 1 | 2 | 3 |
| LightOnOCR-3 4B | 2 | 2 | 4 |
| nace.ai Parse | 12 | 16 | 17 |
| nace.ai Parse | 12 | 16 | 17 |
| Kendall τ against the default | 0.94 | 1.00 | 0.98 |

**labels invented** (statements; cut-off lr = 0.1, **0.2**, 0.3)

| System | 0.1 | 0.2 | 0.3 |
|---|---:|---:|---:|
| dots.mocr (out of the box) | 0 | 0 | 0 |
| dots.mocr (pipeline) | 0 | 0 | 0 |
| Chandra OCR 2 | 0 | 0 | 0 |
| Chandra OCR 1 | 0 | 0 | 0 |
| Nanonets-OCR2 | 0 | 0 | 0 |
| Qwen3-VL-32B (FP8) | 0 | 0 | 0 |
| Qwen3.8-27B (self-hosted) | 0 | 0 | 0 |
| Nemotron Nano 12B VL | 0 | 0 | 0 |
| Qari-OCR v0.3 | 2 | 2 | 2 |
| PaddleOCR-VL-1.6 | 0 | 0 | 0 |
| Surya OCR 2 | 0 | 0 | 0 |
| Persian–Arabic line OCR | 0 | 0 | 0 |
| PaddleOCR PP-OCRv5 Arabic | 0 | 0 | 0 |
| Mistral OCR | 0 | 0 | 0 |
| Cohere Parse | 0 | 1 | 1 |
| LandingAI ADE | 0 | 0 | 0 |
| Qwen3.6-27B | 2 | 2 | 5 |
| Qwen3.8-27B (API) | 0 | 0 | 0 |
| ERNIE 4.5 VL | 9 | 13 | 17 |
| Command A Vision | 13 | 13 | 13 |
| LightOnOCR-3 0.8B | 0 | 0 | 0 |
| LightOnOCR-3 1B | 0 | 0 | 0 |
| LightOnOCR-3 4B | 0 | 0 | 0 |
| nace.ai Parse | 0 | 0 | 0 |
| nace.ai Parse | 0 | 0 | 0 |
| Kendall τ against the default | 0.90 | 1.00 | 0.99 |

## 3. Cross-engine row check threshold (test split, four leading systems pooled)

Severe failure = filing below 95% row recall. The paper's 5% was set on the development split.

| Share of rows disagreeing that flags a filing | Severe failures flagged | False alarms |
|---|---:|---:|
| 2% | 15 of 15 | 25 of 95 |
| 3% | 15 of 15 | 15 of 95 |
| **5%** | 14 of 15 | 8 of 95 |
| 8% | 13 of 15 | 4 of 95 |
| 10% | 10 of 15 | 2 of 95 |
| 15% | 8 of 15 | 0 of 95 |

## 4. Severe-failure line (test split, cross-engine check at 5%)

| Line | dots.mocr adopted pipeline (3 seeds) | Chandra OCR 2 (own input size) | Mistral OCR | Cohere Parse | LandingAI ADE | Flagged (pooled) | False alarms (pooled) |
|---|---:|---:|---:|---:|---:|---:|---:|
| 90% | 2 | 2 | 2 | 1 | 1 | 8 of 8 | 14 of 102 |
| **95%** | 5 | 3 | 2 | 3 | 2 | 14 of 15 | 8 of 95 |
| 98% | 9 | 9 | 5 | 10 | 7 | 16 of 40 | 6 of 70 |

## 5. Figure filter of the confidence analysis (test split)

| Figures included | Output | Figures | Wrong | Wrong in HIGH | Sent to review | Errors caught by review |
|---|---|---:|---:|---:|---:|---:|
| |v| ≥ 100 or decimal | dots.mocr pipeline, seed 0 | 5,094 | 30 | 0 | 9.2% | 100.0% |
| |v| ≥ 100 or decimal | Chandra OCR 2, own input size | 5,031 | 25 | 0 | 9.2% | 100.0% |
| **|v| ≥ 1,000 or decimal** | dots.mocr pipeline, seed 0 | 4,994 | 29 | 0 | 9.2% | 100.0% |
| **|v| ≥ 1,000 or decimal** | Chandra OCR 2, own input size | 4,938 | 22 | 0 | 9.1% | 100.0% |
| |v| ≥ 10,000 or decimal | dots.mocr pipeline, seed 0 | 4,645 | 28 | 0 | 9.6% | 100.0% |
| |v| ≥ 10,000 or decimal | Chandra OCR 2, own input size | 4,583 | 21 | 0 | 9.1% | 100.0% |

