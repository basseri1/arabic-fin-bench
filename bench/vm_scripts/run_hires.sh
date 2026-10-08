#!/bin/zsh
# 300 dpi on all six Ma'aden pages, then 600 dpi on the stubborn pages one at a time (memory-monitored; watchdog running)
B=/path/to/DocProcess/ocr_benchmark; cd $B
export MLX_MEM_LIMIT_GB=22 TOKENIZERS_PARALLELISM=false
PAGES_DIR=pages_abl/dpi300_clahe venv_mlx/bin/python bench.py --model dots_mocr --out results_abl/dots_dpi300_clahe > logs/abl_dots_dpi300_clahe.log 2>&1
for pg in maaden_p13 maaden_p14 maaden_p11; do
  mkdir -p _tmp/p600_$pg; cp pages_abl/dpi600_clahe/$pg.png _tmp/p600_$pg/
  ( while pgrep -f "bench.py --model dots_mocr" >/dev/null; do echo "$(date '+%T') $(top -l 1 -s 0 | grep PhysMem | cut -c1-70) swap=$(sysctl -n vm.swapusage | awk '{print $6}')"; sleep 20; done ) >> logs/mem_600.log 2>&1 &
  PAGES_DIR=_tmp/p600_$pg venv_mlx/bin/python bench.py --model dots_mocr --out results_abl/dots_dpi600_clahe >> logs/abl_dots_dpi600_clahe.log 2>&1
  sleep 5
done
echo "HIRES DONE" >> logs/abl_dots_dpi600_clahe.log
