#!/bin/bash
# Classical PaddleOCR PP-OCRv5 Arabic (CPU, paddleocr 3.3.2 / paddlepaddle 3.2.2 as in the pilot) on all 158 pages.
cd ~/ocr_benchmark; export PAGES_DIR=pages32/plain OMP_NUM_THREADS=4
ls pages32/plain/*.png | xargs -n1 basename | sed 's/\.png$//' > _tmp/pages32_list.txt
split -n l/4 -d _tmp/pages32_list.txt _tmp/pages32_part_
for part in _tmp/pages32_part_0*; do
  ~/venv_paddle/bin/python run_paddle_classic.py --only "$(paste -sd, $part)" --out results32/paddle_ar_plain > logs/run32_paddle_$(basename $part).log 2>&1 &
done
wait
echo "paddle_ar done $(date '+%F %T')" >> logs/run32_status.log
