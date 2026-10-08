#!/bin/zsh
# Experiments for Chandra-2 after everything else: native-dpi Ma'aden pages and the equity column-group split.
B=/path/to/DocProcess/ocr_benchmark; cd $B; MLX=$B/venv_mlx/bin/python
until [ -f logs/LIFT_DONE ]; do sleep 60; done
echo "=== START exp_chandra2  $(date '+%F %T')" >> logs/queue.log
PAGES_DIR=$B/pages_exp/native $MLX bench.py --model chandra2 --out results_exp/chandra2_native >> logs/exp_chandra2.log 2>&1
PAGES_DIR=$B/pages_exp/split  $MLX bench.py --model chandra2 --out results_exp/chandra2_split  >> logs/exp_chandra2.log 2>&1
/opt/anaconda3/bin/python3 exp_merge.py results_exp/chandra2_split --write >> logs/exp_chandra2.log 2>&1
echo "=== END   exp_chandra2  rc=$?  $(date '+%F %T')" >> logs/queue.log; touch logs/EXP_DONE
