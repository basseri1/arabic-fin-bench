#!/bin/zsh
# Side branches that were lost in the chain restarts: Command A Vision (CLAHE, API) and Paddle-VL (CLAHE, CPU).
B=/path/to/DocProcess/ocr_benchmark; cd $B; PY=/opt/anaconda3/bin/python3
run() { local name=$1; shift; echo "=== START $name  $(date '+%F %T')" >> logs/queue.log; "$@" >> logs/${name//:/_}.log 2>&1; echo "=== END   $name  rc=$?  $(date '+%F %T')" >> logs/queue.log; }
( PAGES_DIR=$B/pages_enh_clahe run enh:cmda_vision $PY run_cohere_vlm.py --model command-a-vision-07-2025 --name cmda_vision --temperature 0 --out results_enh/cmda_vision; touch logs/ENH_HOSTED_DONE ) &
( PAGES_DIR=$B/pages_enh_clahe run enh:paddle $PY bench.py --model paddle --out results_enh/paddle; touch logs/ENH_CPU_DONE ) &
wait
