#!/bin/bash
# Phase 3 on the VM GPU, after phase 2:
#  (0) Nanonets-OCR2 rerun (degenerate output under vLLM 0.27.1);
#  (a) Chandra OCR 1 at its native input size (6.3 MP cap), the setting used for Chandra OCR 2;
#  (b) throughput of dots.mocr and Chandra OCR 2 with the GPU to themselves (in phase 1 they shared it), at the
#      concurrency of the phase-2 models (16). Wall-clock per run -> results32/_solo/_wall.jsonl. The outputs double
#      as a run-to-run repeatability check against the phase-1 runs of the same configuration.
cd ~/ocr_benchmark; source ~/venv/bin/activate
export BENCH_BACKEND=vllm TOKENIZERS_PARALLELISM=false
st() { echo "$1 $(date '+%T')" >> logs/run32_status.log; }
wall() { echo "{\"run\": \"$1\", \"secs\": $2, \"conc\": 16, \"pages\": 158}" >> results32/_solo/_wall.jsonl; }
until [ -f logs/run32_phase2_done.flag ]; do sleep 30; done
mkdir -p results32/_solo; st "phase3 start"
# (0) Nanonets-OCR2 again: under vLLM 0.27.1 every page came out as '!!!!' (NaN logits). Try the vLLM 0.17 image used
#     for Chandra (default attention, then FlashInfer), then 0.27.1 in float32; smoke-test 2 pages before the full run.
nano_serve() {   # label, docker env args | "venv-fp32"
  if [ "$2" = "venv-fp32" ]; then
    vllm serve ~/models/NanonetsOCR2 --served-model-name model --port 8010 --max-model-len 32768 --gpu-memory-utilization 0.90       --limit-mm-per-prompt '{"image": 1}' --dtype float32 > logs/serve32_nanonets_$1.log 2>&1 & NPID=$!
  else
    sudo -n docker rm -f nanonets_32 > /dev/null 2>&1
    sudo -n docker run -d --name nanonets_32 --gpus all -p 8010:8000 --ipc=host -v $HOME/models/NanonetsOCR2:/model $2       vllm/vllm-openai:v0.17.0 --model /model --served-model-name model --max-model-len 32768 --gpu-memory-utilization 0.90       --dtype bfloat16 --limit-mm-per-prompt '{"image": 1}' > /dev/null 2>&1
  fi
  for i in $(seq 1 90); do
    curl -sf localhost:8010/v1/models > /dev/null && return 0
    if [ -n "$NPID" ]; then kill -0 $NPID 2>/dev/null || return 1
    else [ "$(sudo -n docker inspect -f '{{.State.Running}}' nanonets_32 2>/dev/null)" = true ] || return 1; fi
    sleep 10
  done; return 1
}
nano_stop() { sudo -n docker inspect nanonets_32 > /dev/null 2>&1 && { sudo -n docker logs nanonets_32 > logs/serve32_nanonets_$1.log 2>&1; sudo -n docker rm -f nanonets_32 > /dev/null 2>&1; }; [ -n "$NPID" ] && { kill $NPID; wait $NPID; NPID=; }; sleep 15; }
mkdir -p results32/_broken _tmp/nano_smoke_pages; [ -d results32/nanonets_plain ] && mv results32/nanonets_plain results32/_broken/nanonets_plain_vllm0271
[ -f logs/run32_nanonets_plain.log ] && mv logs/run32_nanonets_plain.log logs/run32_nanonets_plain_vllm0271.log
cp pages32/plain/aramco_FY2024_p08.png pages32/plain/al_khodari_FY2018_p08.png _tmp/nano_smoke_pages/
nano_done=0
for cfg in "v017|" "v017fi|-e VLLM_ATTENTION_BACKEND=FLASHINFER" "fp32|venv-fp32"; do
  label=${cfg%%|*}; args=${cfg#*|}
  if nano_serve $label "$args"; then
    rm -rf _tmp/nano_smoke_$label
    PAGES_DIR=_tmp/nano_smoke_pages BENCH_CONC=2 python bench_vllm.py --model nanonets --out _tmp/nano_smoke_$label > logs/run32_nanonets_smoke_$label.log 2>&1
    if python3 _tmp/sane.py _tmp/nano_smoke_$label >> logs/run32_nanonets_smoke_$label.log 2>&1; then
      st "nanonets smoke ok ($label)"; t0=$(date +%s)
      PAGES_DIR=pages32/plain BENCH_CONC=16 python bench_vllm.py --model nanonets --out results32/nanonets_plain > logs/run32_nanonets_plain.log 2>&1
      echo "{\"run\": \"nanonets_plain\", \"secs\": $(( $(date +%s) - t0 )), \"conc\": 16, \"pages\": 158, \"server\": \"$label\"}" >> results32/_solo/_wall.jsonl
      nano_stop $label; st "nanonets_plain done ($label)"; nano_done=1; break
    fi
    st "nanonets smoke degenerate ($label)"
  else st "SERVE FAILED nanonets ($label)"; fi
  nano_stop $label
done
[ $nano_done = 1 ] || st "nanonets FAILED in every configuration"
# (a) Chandra OCR 1, 6.3 MP cap (same container flags as phase 2)
sudo -n docker rm -f chandra1_32 > /dev/null 2>&1
sudo -n docker run -d --name chandra1_32 --gpus all -p 8011:8000 --ipc=host -v $HOME/models/Chandra1:/model -e VLLM_ATTENTION_BACKEND=FLASHINFER \
  vllm/vllm-openai:v0.17.0 --model /model --no-enforce-eager --max-num-seqs 64 --dtype bfloat16 --max-model-len 18000 \
  --max_num_batched_tokens 16384 --gpu-memory-utilization 0.85 --enable-prefix-caching \
  --mm-processor-kwargs '{"min_pixels": 3136, "max_pixels": 6291456}' --served-model-name model --trust-remote-code > /dev/null 2>&1
ok=0; for i in $(seq 1 90); do curl -sf localhost:8011/v1/models > /dev/null && { ok=1; break; }; sleep 10; done
if [ $ok = 1 ]; then
  t0=$(date +%s)
  VLLM_URL=http://localhost:8011/v1 PAGES_DIR=pages32/chandra_cap BENCH_CONC=16 python bench_vllm.py --model chandra1 --out results32/chandra1_chandra_cap > logs/run32_chandra1_chandra_cap.log 2>&1
  wall chandra1_chandra_cap $(( $(date +%s) - t0 )); st "chandra1_chandra_cap done"
else st "SERVE FAILED chandra1 (phase 3)"; fi
sudo -n docker stop chandra1_32 > /dev/null; sleep 15
# (b1) dots.mocr alone: out of the box, then the adopted pipeline end to end (CLAHE pass, retry, band-merge, verification)
sudo -n systemctl start dots-vllm
ok=0; for i in $(seq 1 90); do curl -sf localhost:8001/v1/models > /dev/null && { ok=1; break; }; sleep 10; done
if [ $ok = 1 ]; then
  t0=$(date +%s)
  PAGES_DIR=pages32/plain BENCH_SEED=0 BENCH_CONC=16 python bench_vllm.py --model dots_mocr --out results32/_solo/dots_mocr_plain_s0 > logs/run32_solo_dots_plain.log 2>&1
  wall dots_mocr_plain $(( $(date +%s) - t0 ))
  t0=$(date +%s); o=results32/_solo/dots_mocr_clahe_s0; log=logs/run32_solo_dots_clahe.log
  PAGES_DIR=pages32/clahe BENCH_SEED=0 BENCH_CONC=16 python bench_vllm.py --model dots_mocr --out $o > $log 2>&1
  wall dots_mocr_clahe_pass $(( $(date +%s) - t0 ))
  cp -r $o ${o}_raw
  python3 run32_retry.py $o pages32/clahe dots_mocr >> $log 2>&1
  python3 post_dots.py $o ${o}_bm >> $log 2>&1
  python3 run32_validate.py ${o}_bm ${o}_bm_ver >> $log 2>&1
  wall dots_mocr_clahe_bm_ver $(( $(date +%s) - t0 )); st "dots solo timing done"
else st "SERVE FAILED dots (phase 3)"; fi
sudo -n systemctl stop dots-vllm; sleep 15
# (b2) Chandra OCR 2 alone, 6.3 MP cap
sudo -n docker start chandra017 > /dev/null
ok=0; for i in $(seq 1 90); do curl -sf localhost:8003/v1/models > /dev/null && { ok=1; break; }; sleep 10; done
if [ $ok = 1 ]; then
  t0=$(date +%s)
  VLLM_URL=http://localhost:8003/v1 PAGES_DIR=pages32/chandra_cap BENCH_CONC=16 python bench_vllm.py --model chandra2 --out results32/_solo/chandra2_chandra_cap > logs/run32_solo_chandra2.log 2>&1
  wall chandra2_chandra_cap $(( $(date +%s) - t0 )); st "chandra2 solo timing done"
else st "SERVE FAILED chandra2 (phase 3)"; fi
sudo -n docker stop chandra017 > /dev/null
st "PHASE3 DONE"; touch logs/run32_phase3_done.flag
