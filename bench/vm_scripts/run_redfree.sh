#!/bin/zsh
B=/path/to/DocProcess/ocr_benchmark; cd $B; MLX=$B/venv_mlx/bin/python
export TOKENIZERS_PARALLELISM=false MLX_MEM_LIMIT_GB=22 PAGES_DIR=$B/pages_exp/abl_clahe_redfree
for m in dots_mocr chandra2; do
  echo "=== START exp:${m}_redfree  $(date '+%F %T')" >> logs/queue.log
  $MLX bench.py --model $m --out results_exp/${m}_redfree >> logs/exp_redfree.log 2>&1
  echo "=== END   exp:${m}_redfree  rc=$?  $(date '+%F %T')" >> logs/queue.log
done
touch logs/REDFREE_DONE
