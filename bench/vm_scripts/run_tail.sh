#!/bin/zsh
# Tail of the pipeline, strictly sequential: lift (8-bit) -> its probes -> Paddle-VL (plain remainder + CLAHE).
B=/path/to/DocProcess/ocr_benchmark; cd $B; MLX=$B/venv_mlx/bin/python; PY=/opt/anaconda3/bin/python3
export TOKENIZERS_PARALLELISM=false MLX_MEM_LIMIT_GB=26
run() { local name=$1; shift; echo "=== START $name  $(date '+%F %T')" >> logs/queue.log; "$@" >> logs/${name//:/_}.log 2>&1; echo "=== END   $name  rc=$?  $(date '+%F %T')" >> logs/queue.log; }
until [ -f logs/EXP_SPLIT_DONE ]; do sleep 60; done
while pgrep -f "bench.py --model" >/dev/null; do sleep 30; done
# lift: 8-bit MLX conversion (bf16 = 19 GB does not fit), then plain + CLAHE runs, then probe
[ -f models/Lift-mlx/config.json ] || { rm -rf models/Lift-mlx; . venv_mlx/bin/activate; python -m mlx_vlm.convert --hf-path datalab-to/lift --mlx-path models/Lift-mlx -q --q-bits 8 >> logs/convert_lift.log 2>&1; deactivate; }
if [ -f models/Lift-mlx/config.json ]; then
  rm -rf ~/.cache/huggingface/hub/models--datalab-to--lift
  PAGES_DIR=$B/pages run plain:lift $MLX bench.py --model lift --out results/lift
  PAGES_DIR=$B/pages_enh_clahe run enh:lift $MLX bench.py --model lift --out results_enh/lift
  [ -f results/lift/_digit_probe.json ] || $MLX digit_probe.py --model lift >> logs/digit_probe_lift.log 2>&1
fi
[ -f results/persar2b/_digit_probe.json ] || $MLX digit_probe.py --model persar2b >> logs/digit_probe_persar2b.log 2>&1
# Paddle-VL alone (memory hungry): finish plain (8 pages) then CLAHE (11)
PAGES_DIR=$B/pages           run plain:paddle $PY bench.py --model paddle --out results/paddle
PAGES_DIR=$B/pages_enh_clahe run enh:paddle   $PY bench.py --model paddle --out results_enh/paddle
echo "=== PIPELINE COMPLETE $(date '+%F %T')" >> logs/queue.log; touch logs/PIPELINE_DONE
