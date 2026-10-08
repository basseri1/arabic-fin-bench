#!/bin/bash
# All 32 filings (158 statement pages) through the models served on this VM. Logs: logs/run32_*.log
cd ~/ocr_benchmark; source ~/venv/bin/activate
export BENCH_BACKEND=vllm TOKENIZERS_PARALLELISM=false
R=results32; mkdir -p $R logs; rm -f logs/run32_done.flag
echo "start $(date '+%F %T')" > logs/run32_status.log
until curl -sf localhost:8003/v1/models >/dev/null; do sleep 10; done
echo "chandra up $(date '+%T')" >> logs/run32_status.log
(
  for prep in chandra_cap plain; do
    out=$R/chandra2_$prep
    VLLM_URL=http://localhost:8003/v1 PAGES_DIR=pages32/$prep BENCH_CONC=6 python bench_vllm.py --model chandra2 --out $out > logs/run32_chandra2_$prep.log 2>&1
    python3 run32_validate.py $out ${out}_ver >> logs/run32_chandra2_$prep.log 2>&1
    echo "chandra2_$prep done $(date '+%T')" >> logs/run32_status.log
  done
) &
for seed in 0 1 2; do
  for prep in clahe plain; do
    out=$R/dots_mocr_${prep}_s$seed; log=logs/run32_dots_${prep}_s$seed.log
    PAGES_DIR=pages32/$prep BENCH_SEED=$seed BENCH_CONC=8 python bench_vllm.py --model dots_mocr --out $out > $log 2>&1
    if [ "$prep" = "clahe" ]; then          # adopted pipeline: structure retry -> band-merge -> verification
      cp -r $out ${out}_raw
      python3 run32_retry.py $out pages32/$prep dots_mocr >> $log 2>&1
      python3 post_dots.py $out ${out}_bm >> $log 2>&1
      python3 run32_validate.py ${out}_bm ${out}_bm_ver >> $log 2>&1
    else                                    # out of the box: band-merge only (layout JSON -> table text), no retry/verification
      python3 post_dots.py $out ${out}_bm >> $log 2>&1
    fi
    echo "dots_mocr_${prep}_s$seed done $(date '+%T')" >> logs/run32_status.log
  done
done
wait
echo "ALL DONE $(date '+%F %T')" >> logs/run32_status.log
touch logs/run32_done.flag
