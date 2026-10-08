#!/bin/bash
# Phase 4 on the VM GPU (models added on request), after phase 3, each model alone on the GPU:
#  Qwen3.8-27B self-hosted: official BF16 checkpoint, vLLM 0.27.1, reasoning off, same prompt as its hosted run;
#  North Micro Vision Instruct (CohereLabs, 2.4B): Transformers 5.17 in venv_surya (vLLM has no support for it yet).
cd ~/ocr_benchmark; source ~/venv/bin/activate
export BENCH_BACKEND=vllm TOKENIZERS_PARALLELISM=false
st() { echo "$1 $(date '+%T')" >> logs/run32_status.log; }
until [ -f logs/run32_phase3_done.flag ]; do sleep 30; done
st "phase4 start"
vllm serve ~/models/Qwen38_27B --served-model-name model --port 8010 --max-model-len 32768 --gpu-memory-utilization 0.90 \
  --limit-mm-per-prompt '{"image": 1}' > logs/serve32_qwen38.log 2>&1 &
SPID=$!
ok=0; for i in $(seq 1 120); do curl -sf localhost:8010/v1/models > /dev/null && { ok=1; break; }; kill -0 $SPID 2>/dev/null || break; sleep 10; done
if [ $ok = 1 ]; then
  rm -rf _tmp/q38_smoke; mkdir -p _tmp/q38_smoke_pages; cp pages32/plain/aramco_FY2024_p08.png pages32/plain/almarai_FY2024_p09.png _tmp/q38_smoke_pages/
  PAGES_DIR=_tmp/q38_smoke_pages BENCH_CONC=2 python bench_vllm.py --model qwen38_27b --out _tmp/q38_smoke > logs/run32_qwen38_smoke.log 2>&1
  if python3 _tmp/sane.py _tmp/q38_smoke >> logs/run32_qwen38_smoke.log 2>&1; then
    t0=$(date +%s)
    PAGES_DIR=pages32/plain BENCH_CONC=16 python bench_vllm.py --model qwen38_27b --out results32/qwen38_27b_local_plain > logs/run32_qwen38_27b_local_plain.log 2>&1
    echo "{\"run\": \"qwen38_27b_local_plain\", \"secs\": $(( $(date +%s) - t0 )), \"conc\": 16, \"pages\": 158}" >> results32/_solo/_wall.jsonl
    st "qwen38_27b_local_plain done"
  else st "qwen38 smoke degenerate"; fi
else st "SERVE FAILED qwen38"; fi
kill $SPID 2>/dev/null; wait $SPID 2>/dev/null; sleep 20
t0=$(date +%s)
PAGES_DIR=pages32/plain ~/venv_surya/bin/python run_north_micro.py --out results32/north_micro_plain --batch 16 > logs/run32_north_micro_plain.log 2>&1
if grep -q "ERROR" logs/run32_north_micro_plain.log; then      # e.g. out of memory on a batch: redo only the empty pages, smaller batches
  PAGES_DIR=pages32/plain ~/venv_surya/bin/python run_north_micro.py --out results32/north_micro_plain --batch 4 >> logs/run32_north_micro_plain.log 2>&1
fi
echo "{\"run\": \"north_micro_plain\", \"secs\": $(( $(date +%s) - t0 )), \"conc\": 16, \"pages\": 158}" >> results32/_solo/_wall.jsonl
st "north_micro_plain done"
st "PHASE4 DONE"; touch logs/run32_phase4_done.flag
