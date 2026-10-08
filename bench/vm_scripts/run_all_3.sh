#!/bin/zsh
# Phase 3 (after phase 2): Chandra-2 with proper stop tokens, Chandra 1, Surya OCR 2, then their digit probes.
B=/path/to/DocProcess/ocr_benchmark; cd $B
MLX=$B/venv_mlx/bin/python
until [ -f logs/PHASE2_DONE ]; do sleep 60; done
run() { local name=$1; shift; echo "=== START $name  $(date '+%F %T')" >> logs/queue.log; "$@" >> logs/$name.log 2>&1; echo "=== END   $name  rc=$?  $(date '+%F %T')" >> logs/queue.log; }
# 1) Chandra-2: one-page test with <|im_end|> stop token; if it stops normally, re-run all pages
[ -d results_extra/chandra2_noeos ] || mv results/chandra2 results_extra/chandra2_noeos
rm -rf results_smoke/chandra2_eos
$MLX bench.py --model chandra2 --only aramco_p13 --out results_smoke/chandra2_eos >> logs/chandra2_eos_test.log 2>&1
if grep -q '"finish": "stop"' results_smoke/chandra2_eos/_timing.jsonl 2>/dev/null; then
  echo "=== chandra2 eos fix works -> full rerun $(date '+%T')" >> logs/queue.log
  run chandra2 $MLX bench.py --model chandra2
else
  echo "=== chandra2 eos fix did NOT stop generation; restoring no-eos run $(date '+%T')" >> logs/queue.log
  cp -r results_extra/chandra2_noeos results/chandra2
fi
# 2) Chandra 1
[ -f models/Chandra1-mlx/config.json ] && run chandra1 $MLX bench.py --model chandra1
# 3) Surya OCR 2 (llama.cpp backend)
[ -x "$(command -v llama-server)" ] && [ -f run_surya.py ] && run surya2 $B/venv_surya/bin/python run_surya.py
# 4) probes
for m in chandra2 chandra1 surya2; do
  [ -d results/$m ] || continue
  [ -f results/$m/_digit_probe.json ] && continue
  echo "=== PROBE $m $(date '+%T')" >> logs/probes.log
  if [ $m = surya2 ]; then $B/venv_surya/bin/python digit_probe.py --model surya2 >> logs/digit_probe_surya2.log 2>&1; else $MLX digit_probe.py --model $m >> logs/digit_probe_$m.log 2>&1; fi
done
echo "=== PHASE3 DONE $(date '+%F %T')" >> logs/queue.log
touch logs/PHASE3_DONE
