#!/bin/bash
# Q-19: model/serving regression gate. Runs the frozen 17-page ground-truth benchmark through both models
# and fails (exit 1) if row recall drops below the floors. Run before shipping ANY model/server/prompt change.
set -e
cd "$(dirname "$0")"
source ~/venv/bin/activate
export BENCH_BACKEND=vllm BENCH_CONC=8
TS=$(date +%s)
echo "== regression gate $(date '+%F %T')"
rm -rf results_gate; mkdir -p results_gate logs
PAGES_DIR=pages_pipe/clahe BENCH_TEMP=0.0 python bench_vllm.py --model dots_mocr --out results_gate/dots_mocr_gate > logs/gate_dots.log 2>&1
python3 post_dots.py results_gate/dots_mocr_gate results_gate/dots_mocr_gate_bm > /dev/null
VLLM_URL=http://localhost:8003/v1 PAGES_DIR=pages_pipe/chandra_cap python bench_vllm.py --model chandra2 --out results_gate/chandra2_gate > logs/gate_chandra.log 2>&1
EVAL_DOCS=aramco,maaden,drilling python3 eval2.py --results results_gate 2>/dev/null | tee logs/gate_eval.log | grep -E "ALL"
DOTS=$(grep "^dots_mocr_gate_bm ALL" logs/gate_eval.log | awk '{gsub("%","",$7); print $7}')
CHAN=$(grep "^chandra2_gate ALL" logs/gate_eval.log | awk '{gsub("%","",$7); print $7}')
echo "dots.mocr (band-merged) row recall: ${DOTS}%  (floor 98.0)"
echo "chandra-2 (at-cap)     row recall: ${CHAN}%  (floor 94.0)"
python3 -c "import sys; d, c = float('${DOTS:-0}'), float('${CHAN:-0}'); ok = d >= 98.0 and c >= 94.0; print('GATE ' + ('PASS' if ok else 'FAIL')); sys.exit(0 if ok else 1)"
