#!/bin/zsh
# CPU pipelines on CLAHE-only pages (their detectors downscale internally, so the 2x upscale only costs time)
B=/path/to/DocProcess/ocr_benchmark; cd $B; PY=/opt/anaconda3/bin/python3
export PAGES_DIR=$B/pages_enh_clahe
run() { local name=$1; shift; echo "=== START enh:$name  $(date '+%F %T')" >> logs/queue.log; "$@" >> logs/enh_$name.log 2>&1; echo "=== END   enh:$name  rc=$?  $(date '+%F %T')" >> logs/queue.log; }
run paddle_ar $PY run_paddle_classic.py --out results_enh/paddle_ar
run paddle    $PY bench.py --model paddle --out results_enh/paddle
touch logs/ENH_CPU_DONE
