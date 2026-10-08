#!/bin/zsh
# Enhanced pass v6: fastest-first GPU chain; new models get a CLAHE run AND a plain run (for the main ranking).
B=/path/to/DocProcess/ocr_benchmark; cd $B
MLX=$B/venv_mlx/bin/python; PY=/opt/anaconda3/bin/python3
export TOKENIZERS_PARALLELISM=false MLX_MEM_LIMIT_GB=26
run() { local name=$1; shift; echo "=== START $name  $(date '+%F %T')" >> logs/queue.log; "$@" >> logs/${name//:/_}.log 2>&1; echo "=== END   $name  rc=$?  $(date '+%F %T')" >> logs/queue.log; }
conv() { [ -f models/$2/config.json ] || { . venv_mlx/bin/activate; python -m mlx_vlm.convert --hf-path $1 --mlx-path models/$2 --dtype bfloat16 >> logs/convert_$3.log 2>&1; deactivate; }; }
E() { PAGES_DIR=$B/pages_enh_clahe run enh:$1 $MLX bench.py --model $1 --out results_enh/$1; }      # CLAHE run
P() { PAGES_DIR=$B/pages            run plain:$1 $MLX bench.py --model $1 --out results/$1; }        # plain run
# tier 1 (fast)
E qari2b; E dots_mocr
P north
until [ -f models/NanonetsOCR2-mlx/config.json ]; do sleep 30; done; P nanonets; E nanonets
[ -x "$(command -v llama-server)" ] && { PAGES_DIR=$B/pages_enh_clahe run enh:surya2 $B/venv_surya/bin/python run_surya.py --out results_enh/surya2; PAGES_DIR=$B/pages run plain:surya2 $B/venv_surya/bin/python run_surya.py --out results/surya2; }
conv bakrianoo/arabic-legal-documents-ocr-1.0 LegalOCR-mlx legalocr; [ -f models/LegalOCR-mlx/config.json ] && { E legalocr; P legalocr; }
# tier 2
E qari4b; E dots_ocr; E aya8b; P aya8b
conv mohajesmaeili/Qwen3-VL-2B-Persian-Arabic-Ocr-v1.0 PersAr2B-mlx persar
until [ -f results_enh/paddle_ar/_timing.jsonl ] && [ $(wc -l < results_enh/paddle_ar/_timing.jsonl) -ge 11 ]; do sleep 30; done
[ -f models/PersAr2B-mlx/config.json ] && { PAGES_DIR=$B/pages_enh_clahe BOXES_DIR=$B/results_enh/paddle_ar run enh:persar2b $MLX run_linelevel.py --out results_enh/persar2b; PAGES_DIR=$B/pages BOXES_DIR=$B/results/paddle_ar run plain:persar2b $MLX run_linelevel.py --out results/persar2b; }
# tier 3 (slow)
E chandra2; E xcuros; E chandra1; P chandra1
conv thelamapi/next-ocr NextOCR-mlx nextocr; [ -f models/NextOCR-mlx/config.json ] && { E nextocr; P nextocr; }
[ -f models/Lift-mlx/config.json ] || { . venv_mlx/bin/activate; python -m mlx_vlm.convert --hf-path datalab-to/lift --mlx-path models/Lift-mlx -q --q-bits 8 >> logs/convert_lift.log 2>&1; deactivate; }; [ -f models/Lift-mlx/config.json ] && { E lift; P lift; }
# digit probes
for m in north aya8b chandra1 legalocr nextocr lift nanonets glm_table lfm25vl qari2b dots_ocr dots_mocr qari4b chandra2 xcuros; do
  [ -f results/$m/_digit_probe.json ] && continue; mkdir -p results/$m
  echo "=== PROBE $m $(date '+%T')" >> logs/probes.log; $MLX digit_probe.py --model $m >> logs/digit_probe_$m.log 2>&1
done
[ ! -f results/surya2/_digit_probe.json ] && [ -x "$(command -v llama-server)" ] && { mkdir -p results/surya2; $B/venv_surya/bin/python digit_probe.py --model surya2 >> logs/digit_probe_surya2.log 2>&1; }
[ ! -f results/paddle_ar/_digit_probe.json ] && $PY digit_probe.py --model paddle_ar >> logs/digit_probe_paddle_ar.log 2>&1
[ ! -f results/persar2b/_digit_probe.json ] && [ -f models/PersAr2B-mlx/config.json ] && { mkdir -p results/persar2b; $MLX digit_probe.py --model persar2b >> logs/digit_probe_persar2b.log 2>&1; }
until [ -f logs/ENH_HOSTED_DONE ] && [ -f logs/ENH_CPU_DONE ]; do sleep 60; done
echo "=== ENHANCED PASS DONE $(date '+%F %T')" >> logs/queue.log; touch logs/ENH_DONE
