#!/bin/zsh
# After the main queue: digit-script probe for every MLX model (GLM already done).
B=/path/to/DocProcess/ocr_benchmark; cd $B
until [ -f logs/ALL_DONE ]; do sleep 60; done
for m in glm_table lfm25vl qari2b dots_ocr dots_mocr qari4b chandra2 ain xcuros; do
  [ -f results/$m/_digit_probe.json ] && continue
  echo "=== PROBE $m $(date '+%T')" >> logs/probes.log
  $B/venv_mlx/bin/python digit_probe.py --model $m >> logs/digit_probe_$m.log 2>&1
done
echo "=== PROBES DONE $(date '+%T')" >> logs/probes.log
touch logs/PROBES_DONE
