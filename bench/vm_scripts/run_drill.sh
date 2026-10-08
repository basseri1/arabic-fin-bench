#!/bin/zsh
B=/path/to/DocProcess/ocr_benchmark; cd $B; MLX=$B/venv_mlx/bin/python; PY=/opt/anaconda3/bin/python3
export TOKENIZERS_PARALLELISM=false MLX_MEM_LIMIT_GB=22
run() { local name=$1; shift; echo "=== START drill:$name  $(date '+%F %T')" >> logs/queue.log; "$@" >> logs/drill_$name.log 2>&1; echo "=== END   drill:$name  rc=$?  $(date '+%F %T')" >> logs/queue.log; }
( PAGES_DIR=$B/pages_drill         run mistral_ocr         $PY run_mistral_native.py --out results_drill/mistral_ocr
  PAGES_DIR=$B/pages_drill_clahe   run mistral_ocr_clahe   $PY run_mistral_native.py --out results_drill/mistral_ocr_clahe
  PAGES_DIR=$B/pages_drill_clahe2x run mistral_ocr_clahe2x $PY run_mistral_native.py --out results_drill/mistral_ocr_clahe2x ) &
PAGES_DIR=$B/pages_drill       run dots_mocr       $MLX bench.py --model dots_mocr --out results_drill/dots_mocr
PAGES_DIR=$B/pages_drill_clahe run dots_mocr_clahe $MLX bench.py --model dots_mocr --out results_drill/dots_mocr_clahe
PAGES_DIR=$B/pages_drill       run chandra2        $MLX bench.py --model chandra2 --out results_drill/chandra2
PAGES_DIR=$B/pages_drill_clahe run chandra2_clahe  $MLX bench.py --model chandra2 --out results_drill/chandra2_clahe
wait
# verification stage (second reader: Mistral for the locals, Chandra-2 for Mistral)
for r in "mistral_ocr:chandra2" "mistral_ocr_clahe:chandra2_clahe" "mistral_ocr_clahe2x:chandra2_clahe" "dots_mocr:mistral_ocr" "dots_mocr_clahe:mistral_ocr_clahe" "chandra2:mistral_ocr" "chandra2_clahe:mistral_ocr_clahe"; do
  IFS=: read m sec <<< "$r"; $PY validate.py results_drill/$m --doc drilling --second results_drill/$sec --apply results_drill/${m}_verified >> logs/drill_validate.log 2>&1
done
touch logs/DRILL_DONE; echo "=== DRILL DONE $(date '+%F %T')" >> logs/queue.log
