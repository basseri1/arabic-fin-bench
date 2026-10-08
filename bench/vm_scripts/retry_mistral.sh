#!/bin/zsh
# Retry Mistral OCR (OpenRouter) every 10 min until all 11 pages are in (402 = no credits yet; retries are free).
B=/path/to/DocProcess/ocr_benchmark; cd $B
for i in $(seq 1 144); do   # up to 24h
  /opt/anaconda3/bin/python3 run_mistral_ocr.py >> logs/mistral_ocr.log 2>&1
  n=$(ls results/mistral_ocr/*.md 2>/dev/null | xargs -I{} sh -c 'test -s {} && echo x' | wc -l | tr -d ' ')
  if [ "$n" -ge 11 ]; then echo "=== MISTRAL OCR COMPLETE $(date '+%F %T')" >> logs/queue.log; exit 0; fi
  sleep 600
done
