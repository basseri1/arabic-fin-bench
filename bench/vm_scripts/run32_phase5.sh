#!/bin/bash
# Phase 5: Qwen3.8-27B self-hosted again, after phase 4. The first start failed: vLLM's default max_num_seqs (1024)
# exceeds the 301 Mamba-cache blocks this hybrid-attention model gets on one H100; 64 is ample for 16 requests in flight.
cd ~/ocr_benchmark; source ~/venv/bin/activate
export BENCH_BACKEND=vllm TOKENIZERS_PARALLELISM=false
st() { echo "$1 $(date '+%T')" >> logs/run32_status.log; }
until [ -f logs/run32_phase4_done.flag ]; do sleep 30; done
st "phase5 start"
mv logs/serve32_qwen38.log logs/serve32_qwen38_failed_maxseqs.log 2>/dev/null
vllm serve ~/models/Qwen38_27B --served-model-name model --port 8010 --max-model-len 32768 --gpu-memory-utilization 0.90 \
  --max-num-seqs 64 --limit-mm-per-prompt '{"image": 1}' > logs/serve32_qwen38.log 2>&1 &
SPID=$!
ok=0; for i in $(seq 1 120); do curl -sf localhost:8010/v1/models > /dev/null && { ok=1; break; }; kill -0 $SPID 2>/dev/null || break; sleep 10; done
if [ $ok = 1 ]; then
  rm -rf _tmp/q38_smoke _tmp/q38_smoke_pages; mkdir -p _tmp/q38_smoke_pages
  cp pages32/plain/aramco_FY2024_p12.png pages32/plain/almarai_FY2024_p09.png _tmp/q38_smoke_pages/
  PAGES_DIR=_tmp/q38_smoke_pages BENCH_CONC=2 python bench_vllm.py --model qwen38_27b --out _tmp/q38_smoke > logs/run32_qwen38_smoke.log 2>&1
  if python3 _tmp/sane.py _tmp/q38_smoke >> logs/run32_qwen38_smoke.log 2>&1; then
    st "qwen38 smoke ok"; t0=$(date +%s)
    PAGES_DIR=pages32/plain BENCH_CONC=16 python bench_vllm.py --model qwen38_27b --out results32/qwen38_27b_local_plain > logs/run32_qwen38_27b_local_plain.log 2>&1
    echo "{\"run\": \"qwen38_27b_local_plain\", \"secs\": $(( $(date +%s) - t0 )), \"conc\": 16, \"pages\": 158}" >> results32/_solo/_wall.jsonl
    st "qwen38_27b_local_plain done"
  else st "qwen38 smoke degenerate"; fi
else st "SERVE FAILED qwen38 (max-num-seqs 64)"; fi
kill $SPID 2>/dev/null; wait $SPID 2>/dev/null; sleep 10
st "PHASE5 DONE"; touch logs/run32_phase5_done.flag
