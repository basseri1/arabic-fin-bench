#!/bin/bash
cd /path/to/DocProcess/ocr_benchmark
MLX=venv_mlx/bin/python
for spec in "glm:aramco_p13" "qari2b:aramco_p12" "dots_ocr:aramco_p13" "lfm25vl:aramco_p13" "ain:aramco_p12" "chandra2:aramco_p13"; do
  m=${spec%%:*}; pg=${spec##*:}
  echo "### SMOKE $m $pg $(date '+%T')"
  $MLX bench.py --model $m --only $pg --out results_smoke/$m 2>&1 | grep -E "^\[|Error|Traceback|error" | tail -6
done
echo "### SMOKE ALL DONE $(date '+%T')"
