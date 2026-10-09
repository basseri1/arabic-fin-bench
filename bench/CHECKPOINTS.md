# Self-hosted checkpoints: exact revisions

The Hugging Face revision of every self-hosted checkpoint: the latest commit available at the time
of the runs (27–28 Sep 2026; 2 Oct 2026 for Qari-OCR v0.3 and PaddleOCR-VL-1.6; 9 Oct 2026 for LightOnOCR-3), read from the Hugging Face API on 2 Oct 2026 and 9 Oct 2026. To reproduce a run, load the checkpoint at
this revision (e.g. `revision="e539fbb52280393adc081b289ec597430a0f9031"`).

| System | Checkpoint | Revision (commit) | Commit date |
|---|---|---|---|
| dots.mocr | dots-studio/dots.mocr | e539fbb52280393adc081b289ec597430a0f9031 | 2026-07-04 |
| Chandra OCR 2 | datalab-to/chandra-ocr-2 | af93b47dba1b47b6640c86ccf487ed2260ab9a09 | 2026-06-26 |
| Chandra OCR 1 | datalab-to/chandra | bd40c21576564d31ba99f204e28ccd5c4c1751fa | 2026-03-26 |
| Surya OCR 2 | datalab-to/surya-ocr-2 | 3b3d4cdf88d6928b0acdc75181b13206ea67c4a3 | 2026-05-27 |
| Nanonets-OCR2 | nanonets/Nanonets-OCR2-3B | c3886ff00bb037ce7da24988c9eafaf1fe2bed72 | 2025-10-16 |
| Persian–Arabic line OCR | mohajesmaeili/Qwen3-VL-2B-Persian-Arabic-Ocr-v1.0 | f595ee658b9d9d9fb51d5d7a7647a44154051491 | 2025-12-23 |
| Qari-OCR v0.3 | NAMAA-Space/Qari-OCR-v0.3-VL-2B-Instruct | dabe11e3990176858b26eacfef3ee16fff1d5970 | 2025-06-10 |
| PaddleOCR-VL-1.6 | PaddlePaddle/PaddleOCR-VL-1.6 | c5630abae1d940eafe0697512a0325494b02ab42 | 2026-08-08 |
| LightOnOCR-3 0.8B | lightonai/LightOnOCR-3-0.8B | 36d8636925327c671bd8e479c517a004f7566bd9 | 2026-10-09 |
| LightOnOCR-3 1B | lightonai/LightOnOCR-3-1B | 23d544085c886bbdace647bcfab91203299417e2 | 2026-10-09 |
| LightOnOCR-3 4B | lightonai/LightOnOCR-3-4B | b71010f095dc3735de7ee6b9969bff8f8f50b39a | 2026-10-09 |
| PaddleOCR-VL-1.6 pipeline: layout model | PaddlePaddle/PP-DocLayoutV3 | 241f8bdfc77a7c7bee915a5057aaee58c235a8d3 | 2026-09-30 |
| Qwen3.8-27B | Qwen/Qwen3.8-27B | 1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0 | 2026-08-14 |
| Qwen3-VL-32B (FP8) | Qwen/Qwen3-VL-32B-Instruct-FP8 | 4bf2c2f39c37c0fede78bede4056e1f18cdf8109 | 2025-10-22 |
| Nemotron Nano 12B VL | nvidia/NVIDIA-Nemotron-Nano-12B-v2-VL-BF16 | ca9543b126e8bf3176916d3d305ccc415f89fd4d | 2026-08-25 |

North Micro Vision Instruct (CohereLabs/North-Micro-Vision-Instruct) was evaluated and then dropped from the evaluation. It was run at revision 46b719694e3bad142f3e931774f4622f1024009e (27 Sep 2026) and re-run on 2 Oct 2026 at revision fa548d9aa62c1220bfd21fc6cfc465f1bd2a1a40, whose only change is the tokenizer configuration; row recall was 0.0% both times. Outputs: results32/north_micro_*.

Not on Hugging Face: PaddleOCR PP-OCRv5 Arabic (PaddleOCR 3, CPU); the API systems are identified by endpoint and date.
