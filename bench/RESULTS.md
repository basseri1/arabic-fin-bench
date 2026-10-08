# Results on the 32-filing benchmark

Every run was made from the same NVIDIA H100 virtual machine: open models served there with vLLM, or Transformers where vLLM has no support (one model on the GPU at a time, except the first batch where dots.mocr and Chandra OCR 2 shared it; their speed comes from solo re-runs), hosted APIs called from it, PaddleOCR on its CPU. See the notes at the end. Ground truth: all 32 filings in gt/ (transcribed by hand by the first author from the page images, without OCR or AI tools, the 3 pilot filings first; checked arithmetically and verified cell by cell by the first author).

**Row recall** (primary): share of ground-truth table rows whose every figure appears on one output line. **Figures**: share of figures found; **Signs**: found with the right sign; **Labels**: rows whose Arabic label is found; **Precision**: share of output numbers that are in the ground truth. dots.mocr ran with 3 seeds (temperature 0.1; mean ± sd); every other system ran once with greedy decoding. 95% CI: bootstrap over filings (all statements of a resampled filing together).

## Test split (22 filings, held out)

| # | System | Params | Run | Setting | Runs | Row recall | 95% CI | Figures | Signs | Labels | Precision |
|---:|---|---|---|---|---:|---:|---|---:|---:|---:|---:|
| 1 | LandingAI ADE | – | API | 200 dpi page, DPT-3 Pro (dpt-3-pro-20260710), Parse Jobs, standard tier | 1 | 97.7% | 95.7%–99.2% | 96.7% | 96.7% | 99.0% | 89.3% |
| 2 | Cohere Parse | 2.3B | API | 200 dpi page, parse-v5.0, markdown output | 1 | 96.8% | 94.2%–98.8% | 97.2% | 97.2% | 97.1% | 89.8% |
| 3 | Mistral OCR | – | API | 200 dpi page | 1 | 96.8% | 92.6%–99.7% | 95.7% | 95.7% | 98.3% | 91.4% |
| 4 | dots.mocr | 3.0B | self-hosted, 1×H100 | adopted pipeline: CLAHE, structure retry, band-merge, verification | 3 | 96.4% ± 0.8 | 94.2%–98.3% | 95.9% | 95.9% | 86.0% | 91.1% |
| 5 | Chandra OCR 2 | 5.3B | self-hosted, 1×H100 | own input size (≤ 6.3 MP) | 1 | 95.5% | 90.9%–99.2% | 97.8% | 97.7% | 99.1% | 90.8% |
| 6 | dots.mocr | 3.0B | self-hosted, 1×H100 | out of the box (200 dpi page) | 3 | 93.7% ± 0.8 | 89.8%–97.1% | 96.3% | 96.3% | 84.8% | 91.0% |
| 7 | Qwen3.6-27B | 27B | API | 200 dpi page, generic prompt, reasoning off | 1 | 84.4% | 77.5%–90.9% | 82.4% | 82.4% | 82.3% | 87.5% |
| 8 | Chandra OCR 1 | 8.8B | self-hosted, 1×H100 | own input size (≤ 6.3 MP) | 1 | 70.6% | 63.2%–77.7% | 68.5% | 68.3% | 90.3% | 88.0% |
| 9 | Persian–Arabic line OCR | 2.1B | self-hosted, 1×H100 | PaddleOCR line boxes, one crop per line | 1 | 70.2% | 61.3%–78.9% | 81.5% | 81.5% | 98.3% | 74.2% |
| 10 | Qwen3.8-27B | 27.8B | self-hosted, 1×H100 | 200 dpi page, generic prompt, reasoning off (official BF16 weights) | 1 | 69.7% | 61.5%–77.8% | 75.4% | 75.4% | 97.7% | 74.5% |
| 11 | Qwen3.8-27B | 27.8B | API | 200 dpi page, generic prompt, reasoning off | 1 | 64.1% | 54.7%–72.7% | 72.5% | 72.4% | 96.6% | 74.4% |
| 12 | Surya OCR 2 | 0.7B | self-hosted, 1×H100 | 200 dpi page, vendor pipeline | 1 | 62.8% | 54.0%–71.6% | 69.2% | 69.0% | 97.2% | 85.5% |
| 13 | Qwen3-VL-32B (FP8) | 33.4B | self-hosted, 1×H100 | 200 dpi page, generic prompt | 1 | 57.8% | 49.7%–66.0% | 69.9% | 69.7% | 95.1% | 78.7% |
| 14 | PaddleOCR PP-OCRv5 Arabic | – | self-hosted, CPU | classical detection + recognition | 1 | 45.0% | 33.4%–57.8% | 61.9% | 51.7% | 98.1% | 62.7% |
| 15 | Nanonets-OCR2 | 3.8B | self-hosted, 1×H100 | 200 dpi page, vendor prompt | 1 | 34.0% | 23.7%–46.3% | 41.9% | 39.9% | 85.6% | 44.1% |
| 16 | PaddleOCR-VL-1.6 | 0.96B | self-hosted, 1×H100 | vendor pipeline: layout detection + VLM (vLLM) | 1 | 15.3% | 2.1%–32.5% | 19.6% | 19.3% | 66.0% | 22.6% |
| 17 | ERNIE 4.5 VL | 424B (47B active) | API | 200 dpi page, generic prompt | 1 | 10.9% | 0.5%–24.3% | 12.4% | 12.1% | 33.8% | 25.2% |
| 18 | Nemotron Nano 12B VL | 13.2B | self-hosted, 1×H100 | 200 dpi page, generic prompt | 1 | 8.5% | 0.1%–19.8% | 7.4% | 7.2% | 0.7% | 10.2% |
| 19 | Command A Vision | 111.9B | API | 200 dpi page, generic prompt | 1 | 8.2% | 0.1%–19.2% | 9.0% | 8.0% | 0.6% | 21.4% |
| 20 | Qari-OCR v0.3 | 2.2B | self-hosted, 1×H100 | 200 dpi page, vendor prompt | 1 | 1.9% | 0.0%–4.8% | 2.4% | 2.2% | 58.2% | 11.8% |

## Development split (10 filings)

| # | System | Params | Run | Setting | Runs | Row recall | 95% CI | Figures | Signs | Labels | Precision |
|---:|---|---|---|---|---:|---:|---|---:|---:|---:|---:|
| 1 | Chandra OCR 2 | 5.3B | self-hosted, 1×H100 | own input size (≤ 6.3 MP) | 1 | 98.7% | 97.1%–99.8% | 99.3% | 99.3% | 96.3% | 91.2% |
| 2 | Mistral OCR | – | API | 200 dpi page | 1 | 98.5% | 97.3%–99.6% | 99.4% | 99.4% | 91.6% | 91.5% |
| 3 | LandingAI ADE | – | API | 200 dpi page, DPT-3 Pro (dpt-3-pro-20260710), Parse Jobs, standard tier | 1 | 98.3% | 96.2%–99.6% | 99.1% | 99.1% | 98.4% | 90.1% |
| 4 | Cohere Parse | 2.3B | API | 200 dpi page, parse-v5.0, markdown output | 1 | 97.8% | 95.2%–99.4% | 98.7% | 98.7% | 98.7% | 89.8% |
| 5 | dots.mocr | 3.0B | self-hosted, 1×H100 | adopted pipeline: CLAHE, structure retry, band-merge, verification | 3 | 92.9% ± 0.6 | 82.4%–99.3% | 94.7% | 94.7% | 71.9% | 87.8% |
| 6 | dots.mocr | 3.0B | self-hosted, 1×H100 | out of the box (200 dpi page) | 3 | 87.9% ± 0.9 | 74.0%–96.7% | 92.4% | 92.4% | 71.0% | 87.3% |
| 7 | Surya OCR 2 | 0.7B | self-hosted, 1×H100 | 200 dpi page, vendor pipeline | 1 | 83.0% | 73.1%–91.8% | 85.7% | 85.5% | 83.3% | 90.1% |
| 8 | Chandra OCR 1 | 8.8B | self-hosted, 1×H100 | own input size (≤ 6.3 MP) | 1 | 80.1% | 67.6%–92.0% | 85.1% | 85.0% | 88.1% | 84.2% |
| 9 | Qwen3.6-27B | 27B | API | 200 dpi page, generic prompt, reasoning off | 1 | 78.9% | 59.6%–93.5% | 73.2% | 73.2% | 74.5% | 92.5% |
| 10 | Persian–Arabic line OCR | 2.1B | self-hosted, 1×H100 | PaddleOCR line boxes, one crop per line | 1 | 77.4% | 66.3%–89.4% | 88.1% | 88.1% | 97.8% | 77.3% |
| 11 | Qwen3.8-27B | 27.8B | self-hosted, 1×H100 | 200 dpi page, generic prompt, reasoning off (official BF16 weights) | 1 | 73.2% | 51.6%–92.6% | 84.1% | 84.1% | 95.6% | 76.8% |
| 12 | Qwen3.8-27B | 27.8B | API | 200 dpi page, generic prompt, reasoning off | 1 | 64.9% | 52.9%–78.9% | 69.1% | 69.1% | 90.8% | 79.0% |
| 13 | Qwen3-VL-32B (FP8) | 33.4B | self-hosted, 1×H100 | 200 dpi page, generic prompt | 1 | 63.3% | 48.0%–78.5% | 71.4% | 71.3% | 94.6% | 81.1% |
| 14 | PaddleOCR PP-OCRv5 Arabic | – | self-hosted, CPU | classical detection + recognition | 1 | 63.1% | 45.7%–80.0% | 79.1% | 71.7% | 97.3% | 75.0% |
| 15 | Nanonets-OCR2 | 3.8B | self-hosted, 1×H100 | 200 dpi page, vendor prompt | 1 | 53.6% | 32.9%–76.0% | 69.2% | 66.4% | 67.3% | 61.1% |
| 16 | PaddleOCR-VL-1.6 | 0.96B | self-hosted, 1×H100 | vendor pipeline: layout detection + VLM (vLLM) | 1 | 38.5% | 9.9%–70.4% | 51.8% | 51.8% | 78.7% | 53.5% |
| 17 | ERNIE 4.5 VL | 424B (47B active) | API | 200 dpi page, generic prompt | 1 | 35.9% | 7.5%–67.2% | 48.0% | 47.9% | 22.4% | 50.1% |
| 18 | Command A Vision | 111.9B | API | 200 dpi page, generic prompt | 1 | 22.2% | 5.4%–41.4% | 38.4% | 37.4% | 2.1% | 40.6% |
| 19 | Nemotron Nano 12B VL | 13.2B | self-hosted, 1×H100 | 200 dpi page, generic prompt | 1 | 14.2% | 2.5%–28.5% | 17.8% | 17.4% | 1.2% | 27.8% |
| 20 | Qari-OCR v0.3 | 2.2B | self-hosted, 1×H100 | 200 dpi page, vendor prompt | 1 | 1.3% | 0.0%–4.2% | 5.7% | 5.0% | 45.7% | 41.4% |

## All 32 filings

| # | System | Params | Run | Setting | Runs | Row recall | 95% CI | Figures | Signs | Labels | Precision |
|---:|---|---|---|---|---:|---:|---|---:|---:|---:|---:|
| 1 | LandingAI ADE | – | API | 200 dpi page, DPT-3 Pro (dpt-3-pro-20260710), Parse Jobs, standard tier | 1 | 97.9% | 96.4%–99.1% | 97.6% | 97.5% | 98.8% | 89.6% |
| 2 | Mistral OCR | – | API | 200 dpi page | 1 | 97.3% | 94.3%–99.4% | 97.0% | 97.0% | 96.1% | 91.4% |
| 3 | Cohere Parse | 2.3B | API | 200 dpi page, parse-v5.0, markdown output | 1 | 97.1% | 95.2%–98.7% | 97.7% | 97.7% | 97.6% | 89.8% |
| 4 | Chandra OCR 2 | 5.3B | self-hosted, 1×H100 | own input size (≤ 6.3 MP) | 1 | 96.6% | 93.2%–99.1% | 98.3% | 98.3% | 98.2% | 90.9% |
| 5 | dots.mocr | 3.0B | self-hosted, 1×H100 | adopted pipeline: CLAHE, structure retry, band-merge, verification | 3 | 95.3% ± 0.7 | 91.9%–97.9% | 95.5% | 95.5% | 81.5% | 89.9% |
| 6 | dots.mocr | 3.0B | self-hosted, 1×H100 | out of the box (200 dpi page) | 3 | 91.8% ± 0.4 | 87.4%–95.6% | 95.0% | 95.0% | 80.4% | 89.7% |
| 7 | Qwen3.6-27B | 27B | API | 200 dpi page, generic prompt, reasoning off | 1 | 82.7% | 75.1%–89.4% | 79.2% | 79.2% | 79.8% | 89.0% |
| 8 | Chandra OCR 1 | 8.8B | self-hosted, 1×H100 | own input size (≤ 6.3 MP) | 1 | 73.7% | 67.3%–80.5% | 74.3% | 74.1% | 89.6% | 86.5% |
| 9 | Persian–Arabic line OCR | 2.1B | self-hosted, 1×H100 | PaddleOCR line boxes, one crop per line | 1 | 72.5% | 65.7%–79.7% | 83.8% | 83.8% | 98.2% | 75.3% |
| 10 | Qwen3.8-27B | 27.8B | self-hosted, 1×H100 | 200 dpi page, generic prompt, reasoning off (official BF16 weights) | 1 | 70.8% | 61.5%–79.8% | 78.4% | 78.4% | 97.0% | 75.3% |
| 11 | Surya OCR 2 | 0.7B | self-hosted, 1×H100 | 200 dpi page, vendor pipeline | 1 | 69.3% | 61.3%–77.3% | 74.9% | 74.8% | 92.8% | 87.2% |
| 12 | Qwen3.8-27B | 27.8B | API | 200 dpi page, generic prompt, reasoning off | 1 | 64.3% | 57.0%–71.8% | 71.3% | 71.2% | 94.7% | 75.9% |
| 13 | Qwen3-VL-32B (FP8) | 33.4B | self-hosted, 1×H100 | 200 dpi page, generic prompt | 1 | 59.6% | 51.9%–67.1% | 70.4% | 70.2% | 95.0% | 79.5% |
| 14 | PaddleOCR PP-OCRv5 Arabic | – | self-hosted, CPU | classical detection + recognition | 1 | 50.8% | 40.5%–61.7% | 67.8% | 58.6% | 97.8% | 67.0% |
| 15 | Nanonets-OCR2 | 3.8B | self-hosted, 1×H100 | 200 dpi page, vendor prompt | 1 | 40.3% | 29.9%–52.3% | 51.4% | 49.1% | 79.8% | 50.3% |
| 16 | PaddleOCR-VL-1.6 | 0.96B | self-hosted, 1×H100 | vendor pipeline: layout detection + VLM (vLLM) | 1 | 22.7% | 8.6%–39.0% | 30.8% | 30.6% | 70.0% | 32.2% |
| 17 | ERNIE 4.5 VL | 424B (47B active) | API | 200 dpi page, generic prompt | 1 | 18.9% | 6.5%–33.4% | 24.8% | 24.6% | 30.1% | 35.4% |
| 18 | Command A Vision | 111.9B | API | 200 dpi page, generic prompt | 1 | 12.7% | 4.2%–22.4% | 19.2% | 18.2% | 1.1% | 29.4% |
| 19 | Nemotron Nano 12B VL | 13.2B | self-hosted, 1×H100 | 200 dpi page, generic prompt | 1 | 10.3% | 2.8%–19.1% | 11.0% | 10.7% | 0.9% | 14.8% |
| 20 | Qari-OCR v0.3 | 2.2B | self-hosted, 1×H100 | 200 dpi page, vendor prompt | 1 | 1.7% | 0.2%–3.9% | 3.5% | 3.2% | 54.2% | 18.1% |

## Ablations (all 32 filings; test split in the last column)

| System | Setting | Runs | Row recall (32 filings) | 95% CI | Figures | Row recall (test) |
|---|---|---:|---:|---|---:|---:|
| dots.mocr | out of the box (200 dpi page) | 3 | 91.8% ± 0.4 | 87.4%–95.6% | 95.0% | 93.7% ± 0.8 |
| dots.mocr | 200 dpi page + band-merge | 3 | 91.9% ± 0.4 | 87.4%–95.6% | 95.0% | 93.7% ± 0.9 |
| dots.mocr | CLAHE contrast | 3 | 90.6% ± 1.6 | 86.5%–94.3% | 93.2% | 90.8% ± 2.1 |
| dots.mocr | CLAHE + structure retry | 3 | 95.2% ± 0.6 | 91.9%–97.8% | 95.4% | 96.2% ± 0.8 |
| dots.mocr | CLAHE + structure retry + band-merge | 3 | 95.2% ± 0.7 | 91.9%–97.8% | 95.4% | 96.2% ± 0.8 |
| dots.mocr | adopted pipeline: CLAHE, structure retry, band-merge, verification | 3 | 95.3% ± 0.7 | 91.9%–97.9% | 95.5% | 96.4% ± 0.8 |
| Chandra OCR 2 | 200 dpi page | 1 | 92.1% | 88.6%–95.5% | 94.4% | 89.4% |
| Chandra OCR 2 | 200 dpi page + verification | 1 | 92.3% | 88.7%–95.7% | 94.5% | 89.6% |
| Chandra OCR 2 | own input size (≤ 6.3 MP) | 1 | 96.6% | 93.2%–99.1% | 98.3% | 95.5% |
| Chandra OCR 2 | own input size + verification | 1 | 96.6% | 93.4%–99.2% | 98.4% | 95.7% |
| Chandra OCR 1 | 200 dpi page | 1 | 70.9% | 65.0%–77.1% | 74.1% | 66.2% |
| Chandra OCR 1 | own input size (≤ 6.3 MP) | 1 | 73.7% | 67.3%–80.5% | 74.3% | 70.6% |

## Row recall by statement-page format (all 32 filings)

| System | Setting | fully scanned | images in a digital PDF | text layer |
|---|---|---:|---:|---:|
| LandingAI ADE | 200 dpi page, DPT-3 Pro (dpt-3-pro-20260710), Parse Jobs, standard tier | 97.0% | 98.8% | 97.2% |
| Mistral OCR | 200 dpi page | 98.9% | 95.3% | 99.4% |
| Cohere Parse | 200 dpi page, parse-v5.0, markdown output | 98.3% | 96.3% | 97.8% |
| Chandra OCR 2 | own input size (≤ 6.3 MP) | 98.9% | 96.0% | 96.5% |
| dots.mocr | adopted pipeline: CLAHE, structure retry, band-merge, verification | 90.4% | 96.5% | 95.4% |
| dots.mocr | out of the box (200 dpi page) | 80.1% | 95.1% | 91.9% |
| Qwen3.6-27B | 200 dpi page, generic prompt, reasoning off | 95.7% | 90.4% | 67.5% |
| Chandra OCR 1 | own input size (≤ 6.3 MP) | 70.6% | 70.7% | 78.8% |
| Persian–Arabic line OCR | PaddleOCR line boxes, one crop per line | 63.7% | 67.4% | 82.7% |
| Qwen3.8-27B | 200 dpi page, generic prompt, reasoning off (official BF16 weights) | 75.5% | 63.9% | 78.4% |
| Surya OCR 2 | 200 dpi page, vendor pipeline | 56.4% | 66.1% | 78.4% |
| Qwen3.8-27B | 200 dpi page, generic prompt, reasoning off | 61.2% | 63.7% | 66.3% |
| Qwen3-VL-32B (FP8) | 200 dpi page, generic prompt | 44.8% | 55.1% | 71.1% |
| PaddleOCR PP-OCRv5 Arabic | classical detection + recognition | 42.7% | 54.0% | 49.4% |
| Nanonets-OCR2 | 200 dpi page, vendor prompt | 38.0% | 34.5% | 49.0% |
| PaddleOCR-VL-1.6 | vendor pipeline: layout detection + VLM (vLLM) | 17.6% | 18.6% | 30.0% |
| ERNIE 4.5 VL | 200 dpi page, generic prompt | 15.9% | 13.9% | 26.6% |
| Command A Vision | 200 dpi page, generic prompt | 12.2% | 11.2% | 14.8% |
| Nemotron Nano 12B VL | 200 dpi page, generic prompt | 2.1% | 11.5% | 11.7% |
| Qari-OCR v0.3 | 200 dpi page, vendor prompt | 2.6% | 2.4% | 0.4% |

Filings per format: fully scanned 4, images in a digital PDF 14, text layer 14

## Speed

Self-hosted systems: wall-clock time for all 158 statement pages with the model alone on the H100 (server start-up excluded). Median seconds per page is the time from sending a page to receiving its full output, with the stated number of requests in flight; for APIs it depends on the provider's load.

| System | Setting | Requests in flight | Wall-clock (158 pages) | Pages per minute | Median s/page |
|---|---|---|---:|---:|---:|
| dots.mocr | out of the box (200 dpi page) | 16 | 2.3 min | 69.7 | 12.1 |
| dots.mocr | adopted pipeline: CLAHE, structure retry, band-merge, verification | 16 (+ retries) | 2.9 min | 55.1 | 12.1 |
| Chandra OCR 2 | own input size (≤ 6.3 MP) | 16 | 4.3 min | 36.6 | 24.1 |
| Chandra OCR 1 | own input size (≤ 6.3 MP) | 16 | 6.8 min | 23.3 | 33.4 |
| Nanonets-OCR2 | 200 dpi page, vendor prompt | 16 | 2.7 min | 58.5 | 10.7 |
| Qwen3-VL-32B (FP8) | 200 dpi page, generic prompt | 16 | 5.8 min | 27.3 | 31.4 |
| Nemotron Nano 12B VL | 200 dpi page, generic prompt | 16 | 2.7 min | 57.8 | 8.5 |
| Qwen3.8-27B | 200 dpi page, generic prompt, reasoning off (official BF16 weights) | 16 | 5.8 min | 27.2 | 31.6 |
| Qari-OCR v0.3 | 200 dpi page, vendor prompt | 16 | 1.2 min | 131.7 | 5.8 |
| PaddleOCR-VL-1.6 | vendor pipeline: layout detection + VLM (vLLM) | pipeline, 16 VLM requests in flight | – | – | – |
| Surya OCR 2 | 200 dpi page, vendor pipeline | 1 page at a time | 49.9 min | 3.2 | 8.9 |
| Persian–Arabic line OCR | PaddleOCR line boxes, one crop per line | 32 lines at a time (line boxes from the PaddleOCR run, not timed here) | 2.5 min | 63.0 | 0.9 |
| PaddleOCR PP-OCRv5 Arabic | classical detection + recognition | 4 processes | 18.5 min | 8.6 | 25.6 |
| Mistral OCR | 200 dpi page | API, one page per request | – | – | 1.8 |
| Cohere Parse | 200 dpi page, parse-v5.0, markdown output | API, one page per request | – | – | 17.4 |
| Qwen3.6-27B | 200 dpi page, generic prompt, reasoning off | API, one page per request | – | – | 39.0 |
| Qwen3.8-27B | 200 dpi page, generic prompt, reasoning off | API, one page per request | – | – | 20.2 |
| ERNIE 4.5 VL | 200 dpi page, generic prompt | API, one page per request | – | – | 23.1 |
| Command A Vision | 200 dpi page, generic prompt | API, one page per request | – | – | 21.2 |

## Run-to-run repeatability

The same configuration run a second time on the same VM, alone on the GPU and with 16 requests in flight instead of 6–8 (same seed and temperature).

| System | Setting | Pages with identical text | Row recall, first run | Row recall, second run |
|---|---|---:|---:|---:|
| dots.mocr | out of the box (200 dpi page) | 118 of 158 | 92.2% | 91.8% |
| dots.mocr | adopted pipeline: CLAHE, structure retry, band-merge, verification | 118 of 158 | 96.1% | 95.9% |
| Chandra OCR 2 | own input size (≤ 6.3 MP) | 95 of 158 | 96.6% | 96.5% |

## API routing

Which companies processed the 158 page images of each API run. Through OpenRouter one model name is served by several providers, each with its own serving stack and possibly its own quantisation.

| System | Route | Providers | Pages per provider |
|---|---|---:|---|
| Qwen3.8-27B | OpenRouter | 15 | Darkbloom 31, Reka 25, DekaLLM 19, DeepInfra 16, Wafer 16, Parasail 11, Mancer 2 10, Chutes 7, AkashML 6, Phala 5, Alibaba 3, Cloudflare 3, Venice 3, CoreWeave 2, Novita 1 |
| Qwen3.6-27B | OpenRouter | 6 | SiliconFlow 38, Phala 36, Venice 26, Alibaba 24, DeepInfra 22, Chutes 12 |
| Mistral OCR | vendor API | 1 | Mistral AI 158 |
| Cohere Parse | vendor API | 1 | Cohere 158 |
| LandingAI ADE | vendor API | 1 | LandingAI 158 |
| ERNIE 4.5 VL | OpenRouter | 1 | Novita 158 |
| Command A Vision | vendor API | 1 | Cohere 158 |

Row recall by provider (each statement scored on its own pages, when all of them went to one provider; each provider saw different statements, so this is indicative only):

| System | Provider | Statements | Rows | Row recall |
|---|---|---:|---:|---:|
| Qwen3.6-27B | SiliconFlow | 34 | 824 | 81.9% |
| Qwen3.6-27B | Phala | 33 | 633 | 77.3% |
| Qwen3.6-27B | Venice | 25 | 454 | 87.7% |
| Qwen3.6-27B | Alibaba | 21 | 409 | 82.9% |
| Qwen3.6-27B | DeepInfra | 21 | 399 | 67.9% |
| Qwen3.6-27B | Chutes | 10 | 174 | 82.8% |
| Qwen3.8-27B | Reka | 24 | 538 | 73.6% |
| Qwen3.8-27B | Darkbloom | 28 | 492 | 34.8% |
| Qwen3.8-27B | DekaLLM | 18 | 339 | 64.6% |
| Qwen3.8-27B | Wafer | 16 | 336 | 58.9% |
| Qwen3.8-27B | DeepInfra | 14 | 304 | 72.0% |
| Qwen3.8-27B | Parasail | 10 | 237 | 81.4% |
| Qwen3.8-27B | Mancer 2 | 7 | 163 | 69.9% |
| Qwen3.8-27B | AkashML | 6 | 132 | 47.7% |
| Qwen3.8-27B | Chutes | 7 | 123 | 78.0% |
| Qwen3.8-27B | Phala | 4 | 66 | 57.6% |
| Qwen3.8-27B | Alibaba | 4 | 58 | 51.7% |
| Qwen3.8-27B | Venice | 2 | 46 | 67.4% |
| Qwen3.8-27B | Cloudflare | 3 | 38 | 86.8% |
| Qwen3.8-27B | Novita | 1 | 19 | 68.4% |
| Qwen3.8-27B | CoreWeave | 1 | 12 | 16.7% |

A controlled test that sends the same statements to named providers (fallbacks off) is in `PROVIDERS.md`.

## Same weights: API against self-hosted

The same open-weight model called through a hosted API and served on the VM from the official checkpoint (same prompt, greedy decoding, reasoning off).

| System | Row recall, API (32 filings) | Row recall, self-hosted (32 filings) | API (test) | Self-hosted (test) | Figures, API | Figures, self-hosted |
|---|---:|---:|---:|---:|---:|---:|
| Qwen3.8-27B | 64.3% | 70.8% | 64.1% | 69.7% | 71.3% | 78.4% |

## Notes on the runs

- **Serving stack.** vLLM 0.27.1 for dots.mocr, Qwen3-VL-32B, Qwen3.8-27B, Nemotron and the Persian–Arabic line model, Qari-OCR v0.3 and PaddleOCR-VL-1.6 (whose vendor pipeline, PaddleOCR 3.7 on PaddlePaddle 3.2.1, runs layout detection and sends each block to the model on the vLLM server); the vLLM 0.17 container for Chandra OCR 1 and 2 (FlashInfer attention) and Nanonets-OCR2; the vendor's vLLM 0.20.1 recipe for Surya OCR 2.
- **Nanonets-OCR2 under vLLM 0.27.1** returned only '!!!!' (NaN logits) on every page; the same checkpoint in the vLLM 0.17 container read normally. The failed run is kept in `results32/_broken/`.
- **Qwen3.8-27B self-hosted** needed `--max-num-seqs 64`: vLLM's default of 1024 exceeds the 301 Mamba-cache blocks this hybrid-attention model gets on one H100, and the server refused to start.
- **Qari-OCR v0.3 and PaddleOCR-VL-1.6** were added on 2 Oct 2026 on the same VM, each alone on the GPU, with the checkpoint revisions in `CHECKPOINTS.md`. Qari-OCR v0.3 stopped on the loop rule on 102 of 158 pages. PaddleOCR-VL-1.6's pipeline returns all pages of a batch together, so its median seconds per page is not given.
- **North Micro Vision Instruct** was evaluated and then dropped from the evaluation; its outputs, including a re-run with the tokenizer fix of its checkpoint (revision fa548d9, 2 Oct 2026, still 0.0% row recall), stay in `results32/north_micro_*`.
- **Nemotron Nano 12B VL** tiles a page into at most 12 tiles of 512 px (6 plus a thumbnail for these pages), about 130 dpi effective; its failures are content invented at that resolution, not missing images.
- **Surya OCR 2** ran through the vendor's page-by-page pipeline, so its speed is not comparable with the 16-requests-in-flight rows.
- **Decoding.** Greedy for every system except dots.mocr (temperature 0.1, vendor setting; 3 seeds). Reasoning was switched off for the Qwen models.

Runs not scored (incomplete or not in the configuration list): north_micro_ctrl20, north_micro_fix, north_micro_plain, north_micro_vendor_s0

