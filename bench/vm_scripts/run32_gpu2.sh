#!/bin/bash
# Phase 2 on the VM GPU: further open models, one server at a time, after the dots.mocr / Chandra-2 batch.
cd ~/ocr_benchmark; source ~/venv/bin/activate
export BENCH_BACKEND=vllm TOKENIZERS_PARALLELISM=false
st() { echo "$1 $(date '+%T')" >> logs/run32_status.log; }
until [ -f logs/run32_done.flag ]; do sleep 30; done
sudo -n systemctl stop dots-vllm; sudo -n docker stop chandra017 > /dev/null; sleep 20; st "phase2 start (dots/chandra servers stopped)"
serve_venv() {   # name, model dir, extra vllm args
  vllm serve "$2" --served-model-name model --port 8010 --max-model-len 32768 --gpu-memory-utilization 0.90 \
      --limit-mm-per-prompt '{"image": 1}' $3 > logs/serve32_$1.log 2>&1 &
  SPID=$!
  for i in $(seq 1 90); do curl -sf localhost:8010/v1/models > /dev/null && return 0; kill -0 $SPID 2>/dev/null || break; sleep 10; done
  st "SERVE FAILED $1"; kill $SPID 2>/dev/null; wait $SPID 2>/dev/null; sleep 10; return 1
}
stop_venv() { kill $SPID 2>/dev/null; wait $SPID 2>/dev/null; sleep 20; }
bench() { PAGES_DIR=pages32/$2 BENCH_CONC=${4:-16} python bench_vllm.py --model $1 --out results32/$3 > logs/run32_$3.log 2>&1; }
if serve_venv nanonets ~/models/NanonetsOCR2 ""; then bench nanonets plain nanonets_plain; stop_venv; st "nanonets_plain done"; fi
if serve_venv qwen3vl32b ~/models/Qwen3VL32B-FP8 ""; then bench qwen3vl_32b plain qwen3vl_32b_plain; stop_venv; st "qwen3vl_32b_plain done"; fi
until [ -f ~/logs/dl2_done.flag ]; do sleep 30; done
if serve_venv nemotron ~/models/NemotronNanoVL12B "--trust-remote-code"; then bench nemotron12b_vl plain nemotron12b_vl_plain; stop_venv; st "nemotron12b_vl_plain done"; fi
until grep -q "paddle_ar done" logs/run32_status.log; do sleep 30; done
if serve_venv persar ~/models/PersAr2B ""; then python run32_linelevel.py --out results32/persar2b_plain > logs/run32_persar2b_plain.log 2>&1; stop_venv; st "persar2b_plain done"; fi
# Chandra OCR 1: same image and flags as the Chandra-2 container
sudo -n docker rm -f chandra1_32 > /dev/null 2>&1
sudo -n docker run -d --name chandra1_32 --gpus all -p 8011:8000 --ipc=host -v $HOME/models/Chandra1:/model -e VLLM_ATTENTION_BACKEND=FLASHINFER \
  vllm/vllm-openai:v0.17.0 --model /model --no-enforce-eager --max-num-seqs 64 --dtype bfloat16 --max-model-len 18000 \
  --max_num_batched_tokens 16384 --gpu-memory-utilization 0.85 --enable-prefix-caching \
  --mm-processor-kwargs '{"min_pixels": 3136, "max_pixels": 6291456}' --served-model-name model --trust-remote-code > logs/serve32_chandra1.log 2>&1
ok=0; for i in $(seq 1 90); do curl -sf localhost:8011/v1/models > /dev/null && { ok=1; break; }; sleep 10; done
if [ $ok = 1 ]; then VLLM_URL=http://localhost:8011/v1 bench chandra1 plain chandra1_plain 6; st "chandra1_plain done"; else st "SERVE FAILED chandra1"; fi
sudo -n docker logs chandra1_32 > logs/serve32_chandra1_container.log 2>&1; sudo -n docker stop chandra1_32 > /dev/null; sleep 15
# Surya OCR 2: the surya package's NVIDIA recipe (vllm v0.20.1 image, MTP=2, H100 sizing), started here since docker needs sudo
until [ -f ~/logs/pull_v0201.done ] && [ -f ~/logs/pip_surya.done ]; do sleep 30; done
sudo -n docker rm -f surya_32 > /dev/null 2>&1
sudo -n docker run -d --name surya_32 --runtime nvidia --gpus device=0 -v $HOME/.cache/huggingface:/root/.cache/huggingface -p 8012:8000 --ipc=host \
  vllm/vllm-openai:v0.20.1 --model datalab-to/surya-ocr-2 --no-enforce-eager --max-num-seqs 104 --dtype bfloat16 --max-model-len 18000 \
  --max-num-batched-tokens 16384 --gpu-memory-utilization 0.85 --enable-prefix-caching \
  --mm-processor-kwargs '{"min_pixels": 3136, "max_pixels": 6291456}' --served-model-name datalab-to/surya-ocr-2 \
  --speculative-config '{"method": "mtp", "num_speculative_tokens": 2}' > logs/serve32_surya.log 2>&1
ok=0; for i in $(seq 1 120); do curl -sf localhost:8012/health > /dev/null && { ok=1; break; }; sleep 10; done
if [ $ok = 1 ]; then
  SURYA_INFERENCE_BACKEND=vllm SURYA_INFERENCE_URL=http://127.0.0.1:8012/v1 VLLM_GPU_TYPE=h100 PAGES_DIR=pages32/plain \
    ~/venv_surya/bin/python run_surya.py --out results32/surya2_plain > logs/run32_surya2_plain.log 2>&1; st "surya2_plain done"
else st "SERVE FAILED surya"; fi
sudo -n docker logs surya_32 > logs/serve32_surya_container.log 2>&1; sudo -n docker stop surya_32 > /dev/null
st "PHASE2 DONE"; touch logs/run32_phase2_done.flag
