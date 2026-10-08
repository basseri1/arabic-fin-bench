#!/bin/zsh
# After the enhanced pass: Chandra-2 on the equity column-group crops (pipeline remedy for wide tables), then merge + score.
B=/path/to/DocProcess/ocr_benchmark; cd $B; MLX=$B/venv_mlx/bin/python
until [ -f logs/ENH_DONE ]; do sleep 60; done
echo "=== START exp:chandra2_split  $(date '+%F %T')" >> logs/queue.log
PAGES_DIR=$B/pages_exp/split $MLX bench.py --model chandra2 --out results_exp/chandra2_split >> logs/exp_chandra2_split.log 2>&1
/opt/anaconda3/bin/python3 exp_merge.py results_exp/chandra2_split --write >> logs/exp_chandra2_split.log 2>&1
echo "=== END   exp:chandra2_split  rc=$?  $(date '+%F %T')" >> logs/queue.log; touch logs/EXP_SPLIT_DONE
