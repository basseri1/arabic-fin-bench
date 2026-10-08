#!/bin/bash
# Sequential MLX conversions (each loads a full model into RAM -> never overlap).
cd /path/to/DocProcess/ocr_benchmark
. venv_mlx/bin/activate
log() { echo "[$(date '+%T')] $*"; }
while pgrep -f "mlx_vlm.convert --hf-path NAMAA-Space/Qari-OCR-v0.3" >/dev/null; do sleep 10; done
log "qari2b convert finished: $(grep -c CONVERT_OK logs/convert_qari2b.log)"
[ -f models/Chandra2-mlx-bf16/config.json ] || { log "convert chandra2"; python -m mlx_vlm.convert --hf-path datalab-to/chandra-ocr-2 --mlx-path models/Chandra2-mlx-bf16 --dtype bfloat16 && log "chandra2 OK"; }
[ -f models/DotsMOCR-mlx/config.json ] || { log "convert dots.mocr"; python -m mlx_vlm.convert --hf-path models/DotsMOCR --mlx-path models/DotsMOCR-mlx --dtype bfloat16 && log "dots.mocr OK"; }
[ -f models/Qari04-merged-hf/config.json ] || { log "merge qari04 lora (torch cpu)"; /opt/anaconda3/bin/python3 merge_qari04.py && log "merge OK"; }
[ -f models/Qari04-mlx-bf16/config.json ] || { log "convert qari04"; python -m mlx_vlm.convert --hf-path models/Qari04-merged-hf --mlx-path models/Qari04-mlx-bf16 --dtype bfloat16 && log "qari04 OK"; }
until grep -q "DONE XCurOS" logs/download_new.log; do sleep 20; done
[ -f models/XCurOS-mlx-bf16/config.json ] || { log "convert xcuros"; python -m mlx_vlm.convert --hf-path XCurOS/XCurOS1.2-8B-VLBF16-Instruct --mlx-path models/XCurOS-mlx-bf16 --dtype bfloat16 && log "xcuros OK"; }
log "CHAIN DONE"
