#!/bin/zsh
B=/path/to/DocProcess/ocr_benchmark; cd $B; MLX=$B/venv_mlx/bin/python
for var in clahe up2x clahe_up2x; do
  PAGES_DIR=$B/pages_exp/$var $MLX bench.py --model dots_mocr --out results_exp/dots_mocr_$var >> logs/exp_dots_mocr.log 2>&1
done
echo "EXP_DOTS_DONE" >> logs/exp_dots_mocr.log
