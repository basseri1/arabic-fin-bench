#!/bin/zsh
# confidence capture run: CLAHE pages, all 17 pages, token logprobs on (after the hires validation frees the GPU)
B=/path/to/DocProcess/ocr_benchmark; cd $B
until grep -q "_bm_ver ALL\|Traceback" logs/pipe_dots_hires_portrait.log; do sleep 60; done; sleep 30
mkdir -p pages_pipe/clahe_all; cp pages_enh_clahe/*.png pages_pipe/clahe_all/ 2>/dev/null; cp pages_drill_clahe/*.png pages_pipe/clahe_all/ 2>/dev/null
BENCH_LOGPROBS=1 PAGES_DIR=pages_pipe/clahe_all MLX_MEM_LIMIT_GB=22 TOKENIZERS_PARALLELISM=false venv_mlx/bin/python bench.py --model dots_mocr --out results_conf/dots_mocr_clahe > logs/conf_run.log 2>&1
echo "CONF RUN DONE" >> logs/conf_run.log
