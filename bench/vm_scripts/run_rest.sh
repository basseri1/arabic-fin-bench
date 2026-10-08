#!/bin/zsh
# Consolidated remaining queue (replaces phases 1-4). Order per user: Chandra-2 (stop-token) first.
B=/path/to/DocProcess/ocr_benchmark; cd $B
MLX=$B/venv_mlx/bin/python; PY=/opt/anaconda3/bin/python3
export TOKENIZERS_PARALLELISM=false
run() { local name=$1; shift; echo "=== START $name  $(date '+%F %T')" >> logs/queue.log; "$@" >> logs/$name.log 2>&1; echo "=== END   $name  rc=$?  $(date '+%F %T')" >> logs/queue.log; }
# 0) let the running XCurOS process finish (its parent script was replaced)
while pgrep -f "bench.py --model xcuros" >/dev/null; do sleep 20; done
echo "=== END   xcuros  rc=done  $(date '+%F %T')" >> logs/queue.log
# 1) Chandra-2 with <|im_end|> stop token: one-page test, then full rerun if it stops cleanly
[ -d results_extra/chandra2_noeos ] || mv results/chandra2 results_extra/chandra2_noeos
rm -rf results_smoke/chandra2_eos
echo "=== START chandra2_eos_test  $(date '+%F %T')" >> logs/queue.log
$MLX bench.py --model chandra2 --only aramco_p13 --out results_smoke/chandra2_eos >> logs/chandra2_eos_test.log 2>&1
if grep -qE '"finish": "(stop|loop)"' results_smoke/chandra2_eos/_timing.jsonl 2>/dev/null; then
  echo "=== END   chandra2_eos_test  rc=stops-cleanly  $(date '+%F %T')" >> logs/queue.log
  rm -rf results/chandra2; run chandra2 $MLX bench.py --model chandra2
else
  echo "=== END   chandra2_eos_test  rc=still-capped  $(date '+%F %T')" >> logs/queue.log
  [ -d results/chandra2 ] || cp -r results_extra/chandra2_noeos results/chandra2
fi
# 2) classical PaddleOCR Arabic baseline (CPU, fast)
run paddle_ar $PY run_paddle_classic.py
# 3) PaddleOCR-VL pipeline (CPU)
run paddle $PY bench.py --model paddle
# 4) remaining local VLMs
run north $MLX bench.py --model north
run aya8b $MLX bench.py --model aya8b
[ -f models/Chandra1-mlx/config.json ] && run chandra1 $MLX bench.py --model chandra1
[ -x "$(command -v llama-server)" ] && run surya2 $B/venv_surya/bin/python run_surya.py
# 5) legal OCR (convert first)
until grep -q "^DONE" logs/download_legalocr.log 2>/dev/null; do sleep 60; done
[ -f models/LegalOCR-mlx/config.json ] || { . venv_mlx/bin/activate; python -m mlx_vlm.convert --hf-path bakrianoo/arabic-legal-documents-ocr-1.0 --mlx-path models/LegalOCR-mlx --dtype bfloat16 >> logs/convert_legalocr.log 2>&1; deactivate; }
[ -f models/LegalOCR-mlx/config.json ] && run legalocr $MLX bench.py --model legalocr
# 6) next-ocr (convert first)
until grep -q "DONE thelamapi/next-ocr" logs/download_nextocr_persar.log 2>/dev/null; do sleep 60; done
[ -f models/NextOCR-mlx/config.json ] || { . venv_mlx/bin/activate; python -m mlx_vlm.convert --hf-path thelamapi/next-ocr --mlx-path models/NextOCR-mlx --dtype bfloat16 >> logs/convert_nextocr.log 2>&1; deactivate; }
[ -f models/NextOCR-mlx/config.json ] && run nextocr $MLX bench.py --model nextocr
# 7) Persian-Arabic 2B line-level pipeline (convert first; needs paddle_ar boxes + run_linelevel.py)
until grep -q "DONE mohajesmaeili" logs/download_nextocr_persar.log 2>/dev/null; do sleep 60; done
[ -f models/PersAr2B-mlx/config.json ] || { . venv_mlx/bin/activate; python -m mlx_vlm.convert --hf-path mohajesmaeili/Qwen3-VL-2B-Persian-Arabic-Ocr-v1.0 --mlx-path models/PersAr2B-mlx --dtype bfloat16 >> logs/convert_persar.log 2>&1; deactivate; }
[ -f models/PersAr2B-mlx/config.json ] && [ -f run_linelevel.py ] && run persar2b $MLX run_linelevel.py
# 8) digit probes for every local model lacking one
for m in glm_table lfm25vl qari2b dots_ocr dots_mocr qari4b chandra2 xcuros north aya8b chandra1 legalocr nextocr persar2b; do
  [ -d results/$m ] || continue; [ -f results/$m/_digit_probe.json ] && continue
  echo "=== PROBE $m $(date '+%T')" >> logs/probes.log
  $MLX digit_probe.py --model $m >> logs/digit_probe_$m.log 2>&1
done
[ -d results/surya2 ] && [ ! -f results/surya2/_digit_probe.json ] && $B/venv_surya/bin/python digit_probe.py --model surya2 >> logs/digit_probe_surya2.log 2>&1
[ -d results/paddle_ar ] && [ ! -f results/paddle_ar/_digit_probe.json ] && $PY digit_probe.py --model paddle_ar >> logs/digit_probe_paddle_ar.log 2>&1
echo "=== ALL DONE $(date '+%F %T')" >> logs/queue.log
touch logs/ALL_DONE
