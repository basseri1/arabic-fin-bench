#!/bin/bash
# LightOnOCR-3 (0.8B, 1B, 4B; released 8 Oct 2026) on the 158 pages (pages32/plain, 200 dpi), each model alone on the
# GPU with 16 requests in flight, as for the other self-hosted document models. Served per the vendor's README
# (github.com/lightonai/LightOnOCR, read 9 Oct 2026): vLLM 0.30.0 with transformers 5.16.1, in a venv of its own,
# because the benchmark's vLLM 0.27.1 makes these models loop (vendor note); the vendor's serve flags; port 8012.
# Transcription prompt (empty), greedy decoding, thinking disabled for the Qwen3.5-based 0.8B and 4B (vendor flag).
# Writes results32/lightonocr3_{08b,1b,4b}_plain and the wall time of each run to results32/_solo/_wall.jsonl.
# Run on the GPU VM:  bash run32_lightonocr3.sh   (logs: logs/run32_lightonocr3_*.log, logs/vllm_lightonocr3_*.log)
cd ~/ocr_benchmark; source ~/venv/bin/activate      # the benchmark's own environment runs the client (bench_vllm.py)
export TOKENIZERS_PARALLELISM=false
st() { echo "$1 $(date '+%T')" >> logs/run32_status.log; }
st "lightonocr3 start"
# free the GPU: the services of the earlier runs start at boot
sudo -n systemctl stop dots-vllm 2>/dev/null; sudo -n docker stop chandra017 2>/dev/null; sleep 10
if [ ! -d ~/venv-lightonocr ]; then
  python3 -m venv ~/venv-lightonocr && ~/venv-lightonocr/bin/pip install -q --upgrade pip \
    && ~/venv-lightonocr/bin/pip install -q "vllm==0.30.0" "transformers==5.16.1" requests pillow || { st "VENV FAILED"; exit 1; }
fi
~/venv-lightonocr/bin/pip list 2>/dev/null | grep -iE '^(vllm|transformers) ' > logs/lightonocr3_versions.txt
mkdir -p results32/_solo

run_one() {   # $1 results name, $2 checkpoint, $3 max-model-len, $4 thinking flag (0/1)
  name=$1; ckpt=$2; mml=$3; think=$4
  extra=""; [ "$think" = 1 ] && extra='--default-chat-template-kwargs {"enable_thinking":false}'
  ~/venv-lightonocr/bin/vllm serve "$ckpt" --port 8012 --served-model-name model --limit-mm-per-prompt '{"image": 1}' \
      --max-model-len $mml --mm-processor-cache-gb 0 --no-enable-prefix-caching --gpu-memory-utilization 0.85 $extra \
      > logs/vllm_$name.log 2>&1 &
  pid=$!
  ok=0; for i in $(seq 1 120); do curl -sf localhost:8012/v1/models > /dev/null && { ok=1; break; }; sleep 10; done
  if [ $ok = 1 ]; then
    o=results32/${name}_plain; log=logs/run32_${name}.log; t0=$(date +%s)
    VLLM_URL=http://localhost:8012/v1 PAGES_DIR=pages32/plain BENCH_CONC=16 python bench_vllm.py --model $name --out $o > $log 2>&1
    secs=$(( $(date +%s) - t0 ))
    echo "{\"run\": \"${name}_plain\", \"secs\": $secs, \"conc\": 16, \"pages\": 158, \"server\": \"vllm-0.30.0\", \"checkpoint\": \"$ckpt\"}" >> results32/_solo/_wall.jsonl
    python3 - "$ckpt" "$o" <<'EOF'
import json, sys, pathlib
# record the served checkpoint revision next to the outputs (from the Hugging Face cache snapshot directory name)
ckpt, out = sys.argv[1], pathlib.Path(sys.argv[2])
snap = pathlib.Path.home() / ".cache/huggingface/hub" / ("models--" + ckpt.replace("/", "--")) / "snapshots"
revs = [p.name for p in snap.iterdir()] if snap.exists() else []
meta = json.loads((out / "_meta.json").read_text()); meta["checkpoint"] = ckpt; meta["revision"] = revs
(out / "_meta.json").write_text(json.dumps(meta, indent=1))
EOF
    st "$name done (${secs}s)"
  else
    st "SERVE FAILED $name"
  fi
  kill $pid 2>/dev/null; sleep 20
}

run_one lightonocr3_08b lightonai/LightOnOCR-3-0.8B 18000 1
run_one lightonocr3_1b  lightonai/LightOnOCR-3-1B   16384 0
run_one lightonocr3_4b  lightonai/LightOnOCR-3-4B   18000 1
st "LIGHTONOCR3 DONE"; touch logs/run32_lightonocr3_done.flag
