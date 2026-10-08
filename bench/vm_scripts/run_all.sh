#!/bin/zsh
# Serial benchmark queue (fast models first so partial results are usable early).
# Launch detached:  python3 detach.py caffeinate -i zsh run_all.sh     (caffeinate = no idle sleep)
B=/path/to/DocProcess/ocr_benchmark
cd $B
MLX=$B/venv_mlx/bin/python
PY=/opt/anaconda3/bin/python3
export TOKENIZERS_PARALLELISM=false
run() {
  local name=$1; shift
  echo "=== START $name  $(date '+%F %T')" >> logs/queue.log
  "$@" >> logs/$name.log 2>&1
  echo "=== END   $name  rc=$?  $(date '+%F %T')" >> logs/queue.log
}
for m in glm glm_table lfm25vl qari2b dots_ocr dots_mocr qari4b chandra2 ain xcuros; do
  run $m $MLX bench.py --model $m
done
run paddle $PY bench.py --model paddle
echo "=== ALL DONE $(date '+%F %T')" >> logs/queue.log
touch logs/ALL_DONE
