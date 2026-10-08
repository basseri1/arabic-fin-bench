#!/bin/bash
# Hosted (API) models on all 158 statement pages, launched from this VM (same client machine as every other run).
cd ~/ocr_benchmark; P=~/venv/bin/python; export PAGES_DIR=pages32/plain
$P run_openrouter_vlm.py --model qwen/qwen3.6-27b --name qwen36_27b --no-think --max-tokens 8192 --out results32/qwen36_27b_plain > logs/run32_qwen36.log 2>&1 &
$P run_openrouter_vlm.py --model qwen/qwen3.8-27b --name qwen38_27b --no-think --max-tokens 8192 --out results32/qwen38_27b_plain > logs/run32_qwen38.log 2>&1 &
$P run_openrouter_vlm.py --model baidu/ernie-4.5-vl-424b-a47b --name ernie45_vl --max-tokens 8192 --out results32/ernie45_vl_plain > logs/run32_ernie.log 2>&1 &
$P run_openrouter_vlm.py --model nvidia/nemotron-nano-12b-v2-vl --name nemotron12b_vl --max-tokens 8192 --out results32/nemotron12b_vl_plain > logs/run32_nemotron.log 2>&1 &
$P run_cohere_vlm.py --model command-a-vision-07-2025 --name cmda_vision --max-tokens 8192 --out results32/cmda_vision_plain > logs/run32_cohere.log 2>&1 &
wait
echo "hosted done $(date '+%F %T')" >> logs/run32_status.log
