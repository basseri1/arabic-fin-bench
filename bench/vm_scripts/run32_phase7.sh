#!/bin/bash
# Phase 7 (RQ2 step 2): token probabilities. The adopted dots.mocr pipeline (seed 0) and Chandra OCR 2 (own input size)
# re-run alone on the GPU with BENCH_LOGPROBS=1, so every delivered figure carries the probabilities of the generation
# that produced it (a fresh generation: batching changes some outputs, so the earlier runs' text cannot be reused).
cd ~/ocr_benchmark; source ~/venv/bin/activate
export BENCH_BACKEND=vllm TOKENIZERS_PARALLELISM=false
st() { echo "$1 $(date '+%T')" >> logs/run32_status.log; }
st "phase7 start"
sudo -n systemctl start dots-vllm
ok=0; for i in $(seq 1 90); do curl -sf localhost:8001/v1/models > /dev/null && { ok=1; break; }; sleep 10; done
if [ $ok = 1 ]; then
  o=results32/dots_mocr_clahe_lp_s0; log=logs/run32_dots_clahe_lp_s0.log
  BENCH_LOGPROBS=1 PAGES_DIR=pages32/clahe BENCH_SEED=0 BENCH_CONC=16 python bench_vllm.py --model dots_mocr --out $o > $log 2>&1
  cp -r $o ${o}_raw
  BENCH_LOGPROBS=1 python3 run32_retry.py $o pages32/clahe dots_mocr >> $log 2>&1
  python3 post_dots.py $o ${o}_bm >> $log 2>&1
  python3 run32_validate.py ${o}_bm ${o}_bm_ver >> $log 2>&1
  st "dots_mocr_clahe_lp_s0 done"
else st "SERVE FAILED dots (phase 7)"; fi
sudo -n systemctl stop dots-vllm; sleep 15
sudo -n docker start chandra017 > /dev/null
ok=0; for i in $(seq 1 90); do curl -sf localhost:8003/v1/models > /dev/null && { ok=1; break; }; sleep 10; done
if [ $ok = 1 ]; then
  o=results32/chandra2_chandra_cap_lp; log=logs/run32_chandra2_cap_lp.log
  BENCH_LOGPROBS=1 VLLM_URL=http://localhost:8003/v1 PAGES_DIR=pages32/chandra_cap BENCH_CONC=16 python bench_vllm.py --model chandra2 --out $o > $log 2>&1
  python3 run32_validate.py $o ${o}_ver >> $log 2>&1
  st "chandra2_chandra_cap_lp done"
else st "SERVE FAILED chandra2 (phase 7)"; fi
sudo -n docker stop chandra017 > /dev/null
st "PHASE7 DONE"; touch logs/run32_phase7_done.flag
