#!/bin/zsh
# Phase 2: runs after the main queue -> the two Cohere models, then the digit-script probe for every model.
B=/path/to/DocProcess/ocr_benchmark; cd $B
MLX=$B/venv_mlx/bin/python
until [ -f logs/ALL_DONE ]; do sleep 60; done
run() { local name=$1; shift; echo "=== START $name  $(date '+%F %T')" >> logs/queue.log; "$@" >> logs/$name.log 2>&1; echo "=== END   $name  rc=$?  $(date '+%F %T')" >> logs/queue.log; }
for m in north aya8b; do [ -f models/$( $MLX -c "import bench;print(bench.SPECS['$m']['path'].split('/')[1])" )/config.json ] && run $m $MLX bench.py --model $m; done
for m in glm_table lfm25vl qari2b dots_ocr dots_mocr qari4b chandra2 ain xcuros north aya8b; do
  [ -f results/$m/_digit_probe.json ] && continue
  [ -d results/$m ] || continue
  echo "=== PROBE $m $(date '+%T')" >> logs/probes.log
  $MLX digit_probe.py --model $m >> logs/digit_probe_$m.log 2>&1
done
echo "=== PHASE2 DONE $(date '+%F %T')" >> logs/queue.log
touch logs/PHASE2_DONE
