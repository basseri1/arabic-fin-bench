#!/bin/zsh
# Enhanced-input pass: every model on pages_enh (CLAHE 2.0/8x8 -> 2x Lanczos -> unsharp). Results in results_enh/.
B=/path/to/DocProcess/ocr_benchmark; cd $B
MLX=$B/venv_mlx/bin/python; PY=/opt/anaconda3/bin/python3
export TOKENIZERS_PARALLELISM=false PAGES_DIR=$B/pages_enh
run() { local name=$1; shift; echo "=== START enh:$name  $(date '+%F %T')" >> logs/queue.log; "$@" >> logs/enh_$name.log 2>&1; echo "=== END   enh:$name  rc=$?  $(date '+%F %T')" >> logs/queue.log; }
# 0) (no wait - started on user request)
echo "=== ENHANCED PASS START $(date '+%F %T')" >> logs/queue.log
# A) hosted models in parallel (no GPU)
( run mistral_ocr $PY run_mistral_native.py --out results_enh/mistral_ocr
  run qwen38_27b  $PY run_openrouter_vlm.py --model qwen/qwen3.8-27b --name qwen38_27b --no-think --out results_enh/qwen38_27b
  run qwen36_27b  $PY run_openrouter_vlm.py --model qwen/qwen3.6-27b --name qwen36_27b --no-think --out results_enh/qwen36_27b
  run qwen3vl_32b $PY run_openrouter_vlm.py --model qwen/qwen3-vl-32b-instruct --name qwen3vl_32b --out results_enh/qwen3vl_32b
  run ernie45_vl  $PY run_openrouter_vlm.py --model baidu/ernie-4.5-vl-424b-a47b --name ernie45_vl --out results_enh/ernie45_vl
  run cmda_vision $PY run_cohere_vlm.py --model command-a-vision-07-2025 --name cmda_vision --temperature 0 --out results_enh/cmda_vision
  touch logs/ENH_HOSTED_DONE ) &
# B) CPU pipelines in parallel
( run paddle_ar $PY run_paddle_classic.py --out results_enh/paddle_ar
  run paddle    $PY bench.py --model paddle --out results_enh/paddle
  touch logs/ENH_CPU_DONE ) &
# C) GPU chain
for m in chandra2 dots_mocr glm glm_table lfm25vl qari2b dots_ocr qari4b xcuros north aya8b chandra1; do
  run $m $MLX bench.py --model $m --out results_enh/$m
done
[ -x "$(command -v llama-server)" ] && run surya2 $B/venv_surya/bin/python run_surya.py --out results_enh/surya2
[ -f models/LegalOCR-mlx/config.json ] || { . venv_mlx/bin/activate; python -m mlx_vlm.convert --hf-path bakrianoo/arabic-legal-documents-ocr-1.0 --mlx-path models/LegalOCR-mlx --dtype bfloat16 >> logs/convert_legalocr.log 2>&1; deactivate; }
[ -f models/LegalOCR-mlx/config.json ] && run legalocr $MLX bench.py --model legalocr --out results_enh/legalocr
[ -f models/NextOCR-mlx/config.json ] || { . venv_mlx/bin/activate; python -m mlx_vlm.convert --hf-path thelamapi/next-ocr --mlx-path models/NextOCR-mlx --dtype bfloat16 >> logs/convert_nextocr.log 2>&1; deactivate; }
[ -f models/NextOCR-mlx/config.json ] && run nextocr $MLX bench.py --model nextocr --out results_enh/nextocr
[ -f models/PersAr2B-mlx/config.json ] || { . venv_mlx/bin/activate; python -m mlx_vlm.convert --hf-path mohajesmaeili/Qwen3-VL-2B-Persian-Arabic-Ocr-v1.0 --mlx-path models/PersAr2B-mlx --dtype bfloat16 >> logs/convert_persar.log 2>&1; deactivate; }
until [ -f results_enh/paddle_ar/_timing.jsonl ] && [ $(wc -l < results_enh/paddle_ar/_timing.jsonl) -ge 11 ]; do sleep 30; done
[ -f models/PersAr2B-mlx/config.json ] && BOXES_DIR=$B/results_enh/paddle_ar run persar2b $MLX run_linelevel.py --out results_enh/persar2b
[ -f models/Lift-mlx/config.json ] || { . venv_mlx/bin/activate; python -m mlx_vlm.convert --hf-path datalab-to/lift --mlx-path models/Lift-mlx --dtype bfloat16 >> logs/convert_lift.log 2>&1; deactivate; }
[ -f models/Lift-mlx/config.json ] && run lift $MLX bench.py --model lift --out results_enh/lift
# D) digit probes for models that never had one (page-independent; stored under results/<model>)
for m in north aya8b chandra1 legalocr nextocr lift; do
  [ -f results/$m/_digit_probe.json ] && continue; mkdir -p results/$m
  echo "=== PROBE $m $(date '+%T')" >> logs/probes.log; $MLX digit_probe.py --model $m >> logs/digit_probe_$m.log 2>&1
done
[ ! -f results/surya2/_digit_probe.json ] && [ -x "$(command -v llama-server)" ] && { mkdir -p results/surya2; $B/venv_surya/bin/python digit_probe.py --model surya2 >> logs/digit_probe_surya2.log 2>&1; }
[ ! -f results/paddle_ar/_digit_probe.json ] && $PY digit_probe.py --model paddle_ar >> logs/digit_probe_paddle_ar.log 2>&1
[ ! -f results/persar2b/_digit_probe.json ] && [ -f models/PersAr2B-mlx/config.json ] && { mkdir -p results/persar2b; $MLX digit_probe.py --model persar2b >> logs/digit_probe_persar2b.log 2>&1; }
for m in glm_table lfm25vl qari2b dots_ocr dots_mocr qari4b chandra2 xcuros; do [ -f results/$m/_digit_probe.json ] || $MLX digit_probe.py --model $m >> logs/digit_probe_$m.log 2>&1; done
wait
echo "=== ENHANCED PASS DONE $(date '+%F %T')" >> logs/queue.log; touch logs/ENH_DONE
