#!/bin/zsh
# Enhanced pass v4: GPU chain only, fastest models first, slowest last (hosted + CPU branches already running).
B=/path/to/DocProcess/ocr_benchmark; cd $B
MLX=$B/venv_mlx/bin/python; PY=/opt/anaconda3/bin/python3
export TOKENIZERS_PARALLELISM=false PAGES_DIR=$B/pages_enh_clahe MLX_MEM_LIMIT_GB=22
run() { local name=$1; shift; echo "=== START enh:$name  $(date '+%F %T')" >> logs/queue.log; "$@" >> logs/enh_$name.log 2>&1; echo "=== END   enh:$name  rc=$?  $(date '+%F %T')" >> logs/queue.log; }
conv() { [ -f models/$2/config.json ] || { . venv_mlx/bin/activate; python -m mlx_vlm.convert --hf-path $1 --mlx-path models/$2 --dtype bfloat16 >> logs/convert_$3.log 2>&1; deactivate; }; }
# tier 1: fast
for m in lfm25vl glm glm_table north qari2b dots_mocr; do run $m $MLX bench.py --model $m --out results_enh/$m; done
[ -x "$(command -v llama-server)" ] && run surya2 $B/venv_surya/bin/python run_surya.py --out results_enh/surya2
conv bakrianoo/arabic-legal-documents-ocr-1.0 LegalOCR-mlx legalocr; [ -f models/LegalOCR-mlx/config.json ] && run legalocr $MLX bench.py --model legalocr --out results_enh/legalocr
# tier 2: medium
for m in qari4b dots_ocr aya8b; do run $m $MLX bench.py --model $m --out results_enh/$m; done
conv mohajesmaeili/Qwen3-VL-2B-Persian-Arabic-Ocr-v1.0 PersAr2B-mlx persar
until [ -f results_enh/paddle_ar/_timing.jsonl ] && [ $(wc -l < results_enh/paddle_ar/_timing.jsonl) -ge 11 ]; do sleep 30; done
[ -f models/PersAr2B-mlx/config.json ] && BOXES_DIR=$B/results_enh/paddle_ar run persar2b $MLX run_linelevel.py --out results_enh/persar2b
# tier 3: slow (Chandra-2 resumes its remaining pages)
run chandra2 $MLX bench.py --model chandra2 --out results_enh/chandra2
run xcuros  $MLX bench.py --model xcuros  --out results_enh/xcuros
run chandra1 $MLX bench.py --model chandra1 --out results_enh/chandra1
conv thelamapi/next-ocr NextOCR-mlx nextocr; [ -f models/NextOCR-mlx/config.json ] && run nextocr $MLX bench.py --model nextocr --out results_enh/nextocr
conv datalab-to/lift Lift-mlx lift; [ -f models/Lift-mlx/config.json ] && run lift $MLX bench.py --model lift --out results_enh/lift
# digit probes for models without one
for m in north aya8b chandra1 legalocr nextocr lift glm_table lfm25vl qari2b dots_ocr dots_mocr qari4b chandra2 xcuros; do
  [ -f results/$m/_digit_probe.json ] && continue; mkdir -p results/$m
  echo "=== PROBE $m $(date '+%T')" >> logs/probes.log; $MLX digit_probe.py --model $m >> logs/digit_probe_$m.log 2>&1
done
[ ! -f results/surya2/_digit_probe.json ] && [ -x "$(command -v llama-server)" ] && { mkdir -p results/surya2; $B/venv_surya/bin/python digit_probe.py --model surya2 >> logs/digit_probe_surya2.log 2>&1; }
[ ! -f results/paddle_ar/_digit_probe.json ] && $PY digit_probe.py --model paddle_ar >> logs/digit_probe_paddle_ar.log 2>&1
[ ! -f results/persar2b/_digit_probe.json ] && [ -f models/PersAr2B-mlx/config.json ] && { mkdir -p results/persar2b; $MLX digit_probe.py --model persar2b >> logs/digit_probe_persar2b.log 2>&1; }
until [ -f logs/ENH_HOSTED_DONE ] && [ -f logs/ENH_CPU_DONE ]; do sleep 60; done
echo "=== ENHANCED PASS DONE $(date '+%F %T')" >> logs/queue.log; touch logs/ENH_DONE
