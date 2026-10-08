#!/bin/zsh
B=/path/to/DocProcess/ocr_benchmark; cd $B; MLX=$B/venv_mlx/bin/python
until [ -f logs/EXP_DONE ]; do sleep 60; done
echo "=== START exp2_chandra2_enhance  $(date '+%F %T')" >> logs/queue.log
for var in clahe up2x clahe_up2x; do PAGES_DIR=$B/pages_exp/$var $MLX bench.py --model chandra2 --out results_exp/chandra2_$var >> logs/exp_chandra2.log 2>&1; done
echo "=== END   exp2_chandra2_enhance  $(date '+%F %T')" >> logs/queue.log; touch logs/EXP2_DONE
