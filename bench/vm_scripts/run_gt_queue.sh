#!/bin/zsh
export IMG_DIR=/path/to/DocProcess/ocr_benchmark/images_gt
B=/path/to/DocProcess/ocr_benchmark
O=$B/output
$B/venv_glm/bin/python $B/run_glm.py > $O/glm_gt.log 2>&1 &
GLM_PID=$!
python3 $B/run_qari04.py > $O/qari04_gt.log 2>&1
python3 $B/run_vlm_ocr.py --model-id MBZUAI/AIN --arch qwen2vl --prompt ain --out-dir $O/ain_gt > $O/ain_gt.log 2>&1
python3 $B/run_vlm_ocr.py --model-id NAMAA-Space/Qari-OCR-v0.3-VL-2B-Instruct --arch qwen2vl --prompt qari --out-dir $O/qari2b_gt > $O/qari2b_gt.log 2>&1
wait $GLM_PID
echo ALL_DONE
