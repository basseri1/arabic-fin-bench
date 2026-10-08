#!/bin/zsh
# Phase 4 (after phase 3): Arabic legal-documents OCR (Gemma-3-4B finetune) -> convert to MLX, run, probe.
B=/path/to/DocProcess/ocr_benchmark; cd $B
MLX=$B/venv_mlx/bin/python
until [ -f logs/PHASE3_DONE ]; do sleep 60; done
run() { local name=$1; shift; echo "=== START $name  $(date '+%F %T')" >> logs/queue.log; "$@" >> logs/$name.log 2>&1; echo "=== END   $name  rc=$?  $(date '+%F %T')" >> logs/queue.log; }
until grep -q "^DONE" logs/download_legalocr.log 2>/dev/null; do sleep 60; done
[ -f models/LegalOCR-mlx/config.json ] || { . venv_mlx/bin/activate; python -m mlx_vlm.convert --hf-path bakrianoo/arabic-legal-documents-ocr-1.0 --mlx-path models/LegalOCR-mlx --dtype bfloat16 >> logs/convert_legalocr.log 2>&1; }
[ -f models/LegalOCR-mlx/config.json ] && run legalocr $MLX bench.py --model legalocr
[ -d results/legalocr ] && [ ! -f results/legalocr/_digit_probe.json ] && $MLX digit_probe.py --model legalocr >> logs/digit_probe_legalocr.log 2>&1
echo "=== PHASE4 DONE $(date '+%F %T')" >> logs/queue.log
touch logs/PHASE4_DONE
