#!/bin/zsh
B=/path/to/DocProcess/ocr_benchmark; cd $B; MLX=$B/venv_mlx/bin/python
export TOKENIZERS_PARALLELISM=false MLX_MEM_LIMIT_GB=22
echo "=== START enh2x:chandra2 (solo, CLAHE+2x)  $(date '+%F %T')" >> logs/queue.log
PAGES_DIR=$B/pages_enh $MLX bench.py --model chandra2 --out results_enh2x/chandra2 >> logs/enh2x_chandra2.log 2>&1
echo "=== END   enh2x:chandra2  rc=$?  $(date '+%F %T')" >> logs/queue.log
# then resume the CLAHE-only pass for everyone
exec caffeinate -i zsh run_enh3.sh
