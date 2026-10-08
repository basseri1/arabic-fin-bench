#!/bin/zsh
B=/path/to/DocProcess/ocr_benchmark; cd $B; export MLX_MEM_LIMIT_GB=22 TOKENIZERS_PARALLELISM=false
until grep -q "HIRES DONE" logs/abl_dots_dpi600_clahe.log 2>/dev/null; do sleep 30; done
for pg in maaden_p15 maaden_p16; do
  mkdir -p _tmp/p600_$pg; cp pages_abl/dpi600_clahe/$pg.png _tmp/p600_$pg/
  PAGES_DIR=_tmp/p600_$pg venv_mlx/bin/python bench.py --model dots_mocr --out results_abl/dots_dpi600_clahe >> logs/abl_dots_dpi600_clahe.log 2>&1
done
echo "HIRES2 DONE" >> logs/abl_dots_dpi600_clahe.log
