#!/bin/bash
# Phase 6: North Micro Vision Instruct with the model card's Transformers sampling (T 0.7, top-p 0.8, top-k 20, seed 0),
# as an ablation next to its greedy run (greedy decoding looped on 151 of 158 pages). Alone on the GPU after phase 5.
cd ~/ocr_benchmark
st() { echo "$1 $(date '+%T')" >> logs/run32_status.log; }
until [ -f logs/run32_phase5_done.flag ]; do sleep 30; done
st "phase6 start"; t0=$(date +%s)
PAGES_DIR=pages32/plain ~/venv_surya/bin/python run_north_micro.py --out results32/north_micro_vendor_s0 --batch 16 \
  --temperature 0.7 --top-p 0.8 --top-k 20 --seed 0 > logs/run32_north_micro_vendor_s0.log 2>&1
if grep -q "ERROR" logs/run32_north_micro_vendor_s0.log; then
  PAGES_DIR=pages32/plain ~/venv_surya/bin/python run_north_micro.py --out results32/north_micro_vendor_s0 --batch 4 \
    --temperature 0.7 --top-p 0.8 --top-k 20 --seed 0 >> logs/run32_north_micro_vendor_s0.log 2>&1
fi
echo "{\"run\": \"north_micro_vendor_s0\", \"secs\": $(( $(date +%s) - t0 )), \"conc\": 16, \"pages\": 158}" >> results32/_solo/_wall.jsonl
st "north_micro_vendor_s0 done"
st "PHASE6 DONE"; touch logs/run32_phase6_done.flag
