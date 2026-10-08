#!/bin/zsh
B=/path/to/DocProcess/ocr_benchmark
O=$B/output
export IMG_DIR=$B/images_small
nice -n 10 $B/venv_glm/bin/python $B/run_glm.py > $O/glm_small.log 2>&1
nice -n 10 python3 $B/run_dots.py > $O/dots_small.log 2>&1
nice -n 10 python3 $B/run_vlm_ocr.py --model-id MBZUAI/AIN --arch qwen2vl --prompt ain --out-dir $O/ain_small > $O/ain_small.log 2>&1
nice -n 10 python3 $B/run_vlm_ocr.py --model-id NAMAA-Space/Qari-OCR-v0.3-VL-2B-Instruct --arch qwen2vl --prompt qari --out-dir $O/qari2b_small > $O/qari2b_small.log 2>&1
nice -n 10 env OUT_DIR=$O/paddle_small IMG_DIR=$B/images_small python3 $B/run_paddle.py > $O/paddle_small.log 2>&1
echo ALL_DONE > $O/queue_done.flag
