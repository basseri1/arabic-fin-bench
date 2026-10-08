#!/bin/sh
# Stage D: after Stage C, test whether CLAHE's gain for dots survives once the retry step exists (plain + retry, 17 pages)
cd /path/to/DocProcess/ocr_benchmark
until grep -q "STAGE C DONE" logs/stage_c.log; do sleep 120; done
echo "##### pipeline dots_mocr / plain (retry on)  $(date '+%H:%M')"
python3 pipeline.py --model dots_mocr --prep plain > logs/pipe_dots_plain.log 2>&1
tail -20 logs/pipe_dots_plain.log
echo "STAGE D DONE"
