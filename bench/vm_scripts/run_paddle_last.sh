#!/bin/zsh
# Paddle-VL (CPU, memory-hungry) runs LAST and alone: finish the plain run (8 pages) then CLAHE (11 pages).
B=/path/to/DocProcess/ocr_benchmark; cd $B; PY=/opt/anaconda3/bin/python3
until [ -f logs/EXP_SPLIT_DONE ]; do sleep 60; done
while pgrep -f "bench.py --model" >/dev/null; do sleep 30; done
run() { local name=$1; shift; echo "=== START $name  $(date '+%F %T')" >> logs/queue.log; "$@" >> logs/${name//:/_}.log 2>&1; echo "=== END   $name  rc=$?  $(date '+%F %T')" >> logs/queue.log; }
PAGES_DIR=$B/pages            run plain:paddle $PY bench.py --model paddle --out results/paddle
PAGES_DIR=$B/pages_enh_clahe  run enh:paddle   $PY bench.py --model paddle --out results_enh/paddle
touch logs/PADDLE_DONE
