#!/bin/zsh
B=/path/to/DocProcess/ocr_benchmark; cd $B; MLX=$B/venv_mlx/bin/python
until [ -f logs/ALL_DONE ]; do sleep 60; done
until grep -q "^DONE" logs/download_lift.log 2>/dev/null; do sleep 60; done
run() { local name=$1; shift; echo "=== START $name  $(date '+%F %T')" >> logs/queue.log; "$@" >> logs/$name.log 2>&1; echo "=== END   $name  rc=$?  $(date '+%F %T')" >> logs/queue.log; }
[ -f models/Lift-mlx/config.json ] || { . venv_mlx/bin/activate; python -m mlx_vlm.convert --hf-path datalab-to/lift --mlx-path models/Lift-mlx --dtype bfloat16 >> logs/convert_lift.log 2>&1; deactivate; }
[ -f models/Lift-mlx/config.json ] && run lift $MLX bench.py --model lift
[ -d results/lift ] && [ ! -f results/lift/_digit_probe.json ] && $MLX digit_probe.py --model lift >> logs/digit_probe_lift.log 2>&1
echo "=== LIFT DONE $(date '+%F %T')" >> logs/queue.log; touch logs/LIFT_DONE
