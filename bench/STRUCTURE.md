# Structure-aware checks of row recall

Method in the header of `bench/structure_metrics.py`. dots.mocr is shown for seed 0.

## A. Column order of credited rows

Rows credited by row recall with at least two distinct non-zero figures; 'swapped' rows put figures in a different column order from the rest of their statement (figures under the wrong period).

| System | Credited rows checked (32 filings) | Swapped | Share | Test split: checked | Swapped |
|---|---:|---:|---:|---:|---:|
| LandingAI ADE | 2,756 | 0 | 0.0% | 1,892 | 0 |
| Mistral OCR | 2,755 | 40 | 1.5% | 1,884 | 16 |
| Cohere Parse | 2,734 | 0 | 0.0% | 1,874 | 0 |
| Chandra OCR 2 | 2,699 | 16 | 0.6% | 1,829 | 3 |
| dots.mocr (pipeline) | 2,685 | 0 | 0.0% | 1,885 | 0 |
| dots.mocr (out of the box) | 2,561 | 1 | 0.0% | 1,815 | 1 |
| Qwen3.6-27B | 2,290 | 35 | 1.5% | 1,616 | 0 |
| Chandra OCR 1 | 1,940 | 17 | 0.9% | 1,298 | 16 |
| Persian–Arabic line OCR | 1,968 | 0 | 0.0% | 1,293 | 0 |
| Qwen3.8-27B (self-hosted) | 1,892 | 140 | 7.4% | 1,276 | 25 |
| Surya OCR 2 | 1,792 | 28 | 1.6% | 1,071 | 27 |
| Qwen3.8-27B (API) | 1,686 | 100 | 5.9% | 1,137 | 0 |
| Qwen3-VL-32B (FP8) | 1,576 | 0 | 0.0% | 1,041 | 0 |
| PaddleOCR PP-OCRv5 Arabic | 1,317 | 1 | 0.1% | 775 | 1 |
| Nanonets-OCR2 | 962 | 19 | 2.0% | 531 | 14 |
| PaddleOCR-VL-1.6 | 597 | 0 | 0.0% | 242 | 0 |
| ERNIE 4.5 VL | 551 | 0 | 0.0% | 216 | 0 |
| Command A Vision | 364 | 0 | 0.0% | 167 | 0 |
| Nemotron Nano 12B VL | 308 | 0 | 0.0% | 176 | 0 |
| Qari-OCR v0.3 | 25 | 4 | 16.0% | 24 | 4 |

## B. GriTS-Con against row recall

GriTS-Con: mean over statements, 95% CI by bootstrap over filings; orientation-invariant as described above.

| System | Row recall (test) | GriTS-Con F (test) | 95% CI | GriTS recall (test) | GriTS precision (test) | Row recall (32) | GriTS-Con F (32) |
|---|---:|---:|---|---:|---:|---:|---:|
| Cohere Parse | 96.8% | 85.3 | 82.8–87.9 | 89.1 | 84.9 | 97.1% | 84.4 |
| LandingAI ADE | 97.7% | 81.6 | 78.3–84.5 | 86.3 | 81.3 | 97.9% | 81.1 |
| Mistral OCR | 96.8% | 80.8 | 78.1–83.6 | 84.9 | 81.2 | 97.3% | 78.6 |
| dots.mocr (pipeline) | 96.4% | 77.2 | 73.5–81.2 | 79.2 | 79.4 | 95.3% | 75.5 |
| dots.mocr (out of the box) | 93.7% | 76.2 | 72.5–80.4 | 78.4 | 78.6 | 91.8% | 73.8 |
| Chandra OCR 2 | 95.5% | 73.6 | 70.0–76.8 | 77.7 | 74.7 | 96.6% | 74.2 |
| Qwen3.8-27B (API) | 64.1% | 70.9 | 67.8–73.9 | 74.5 | 71.7 | 64.3% | 69.0 |
| Qwen3.8-27B (self-hosted) | 69.7% | 67.8 | 64.6–71.0 | 71.4 | 68.4 | 70.8% | 67.2 |
| Qwen3-VL-32B (FP8) | 57.8% | 64.9 | 60.4–69.0 | 64.5 | 70.3 | 59.6% | 64.8 |
| Qwen3.6-27B | 84.4% | 64.5 | 59.2–69.8 | 65.9 | 68.3 | 82.7% | 61.9 |
| Surya OCR 2 | 62.8% | 52.3 | 47.3–57.1 | 51.0 | 59.1 | 69.3% | 54.9 |
| Persian–Arabic line OCR | 70.2% | 51.5 | 48.9–54.3 | 55.5 | 51.1 | 72.5% | 51.9 |
| PaddleOCR PP-OCRv5 Arabic | 45.0% | 47.9 | 44.8–50.7 | 51.8 | 48.0 | 50.8% | 48.5 |
| Chandra OCR 1 | 70.6% | 46.2 | 41.6–50.5 | 44.6 | 54.3 | 73.7% | 49.9 |
| Nanonets-OCR2 | 34.0% | 34.9 | 29.2–40.5 | 38.9 | 34.7 | 40.3% | 36.2 |
| PaddleOCR-VL-1.6 | 15.3% | 31.4 | 26.3–36.7 | 30.4 | 37.1 | 22.7% | 35.0 |
| ERNIE 4.5 VL | 10.9% | 25.4 | 21.2–30.0 | 22.3 | 34.5 | 18.9% | 29.1 |
| Nemotron Nano 12B VL | 8.5% | 14.8 | 10.2–19.7 | 14.5 | 19.6 | 10.3% | 15.7 |
| Command A Vision | 8.2% | 11.8 | 8.6–16.0 | 10.6 | 17.8 | 12.7% | 14.6 |
| Qari-OCR v0.3 | 1.9% | 0.1 | 0.0–0.3 | 0.1 | 0.3 | 1.7% | 0.5 |

## C. Where GriTS separates systems: figures against labels

GriTS-Con recall computed on the value columns alone (figures in the right cell) and on the label column alone; 'exact' replaces the LCS similarity by exact matching, since a figure with one wrong digit is wrong, while the LCS similarity gives it most of the credit (20,979,012 against 20,979,512 scores 0.94).

| System | Row recall (test) | Values, exact (test) | Values, LCS (test) | Labels (test) | Values, exact (32) | Labels (32) |
|---|---:|---:|---:|---:|---:|---:|
| Mistral OCR | 96.8% | 95.9 | 97.6 | 86.5 | 95.1 | 82.9 |
| dots.mocr (pipeline) | 96.4% | 93.5 | 95.8 | 71.0 | 92.4 | 67.7 |
| Chandra OCR 2 | 95.5% | 93.0 | 94.9 | 77.4 | 93.7 | 77.9 |
| Cohere Parse | 96.8% | 92.9 | 95.0 | 94.6 | 93.0 | 94.8 |
| dots.mocr (out of the box) | 93.7% | 92.4 | 94.6 | 70.7 | 89.2 | 66.6 |
| LandingAI ADE | 97.7% | 92.4 | 95.6 | 87.2 | 92.6 | 87.2 |
| Qwen3.6-27B | 84.4% | 76.7 | 82.9 | 75.0 | 74.7 | 72.9 |
| Qwen3.8-27B (self-hosted) | 69.7% | 74.7 | 89.4 | 90.5 | 74.8 | 89.2 |
| Qwen3.8-27B (API) | 64.1% | 72.3 | 89.3 | 90.1 | 70.7 | 87.8 |
| Chandra OCR 1 | 70.6% | 61.9 | 65.6 | 29.5 | 66.4 | 29.2 |
| Qwen3-VL-32B (FP8) | 57.8% | 61.9 | 73.6 | 86.5 | 63.5 | 85.6 |
| Surya OCR 2 | 62.8% | 57.2 | 62.1 | 53.2 | 62.8 | 52.4 |
| Persian–Arabic line OCR | 70.2% | 52.2 | 65.8 | 83.3 | 52.5 | 83.2 |
| Nanonets-OCR2 | 34.0% | 36.0 | 44.9 | 50.1 | 39.8 | 48.6 |
| PaddleOCR PP-OCRv5 Arabic | 45.0% | 33.0 | 60.2 | 82.0 | 35.2 | 81.2 |
| PaddleOCR-VL-1.6 | 15.3% | 16.5 | 39.9 | 32.6 | 21.0 | 33.9 |
| ERNIE 4.5 VL | 10.9% | 10.2 | 26.7 | 27.9 | 17.6 | 29.1 |
| Nemotron Nano 12B VL | 8.5% | 6.4 | 17.3 | 5.4 | 10.2 | 4.6 |
| Command A Vision | 8.2% | 6.4 | 13.4 | 14.6 | 11.1 | 16.3 |
| Qari-OCR v0.3 | 1.9% | 0.0 | 0.1 | 0.1 | 0.3 | 0.1 |

Rank agreement with row recall across the 20 configurations — GriTS-Con F: test ρ = 0.93, τ = 0.82; all ρ = 0.93, τ = 0.80. Exact-match values: test ρ = 0.94, τ = 0.83; all ρ = 0.95, τ = 0.85.

**Reading.** Placing figures in their exact cells ranks the systems almost exactly as row recall does (ρ = 0.94), and row recall rarely credits a row with swapped period columns (at most 1.5% of credited rows for the leading systems), so the primary metric is not an artefact of ignoring structure. The leading systems tie on figures (dots.mocr (pipeline) 93.5, Chandra OCR 2 93.0, Mistral OCR 95.9, Cohere Parse 92.9, LandingAI ADE 92.4) and differ on labels (dots.mocr (pipeline) 71.0, Chandra OCR 2 77.4, Mistral OCR 86.5, Cohere Parse 94.6, LandingAI ADE 87.2). GriTS-Con's LCS similarity gives most of the credit to a figure with a wrong digit, which flatters systems that misread digits; for financial figures the exact-match variant is the meaningful one.

