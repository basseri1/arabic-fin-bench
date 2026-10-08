#!/bin/zsh
# Aya Vision 32B on Cohere's API currently 422s on every image request; retry every 30 min for 4h.
B=/path/to/DocProcess/ocr_benchmark; cd $B
for i in $(seq 1 8); do
  /opt/anaconda3/bin/python3 run_cohere_vlm.py --model c4ai-aya-vision-32b --name aya32b_api --temperature 0.3 >> logs/aya32b_api.log 2>&1
  n=$(for f in results/aya32b_api/*.md; do [ -s "$f" ] && echo x; done 2>/dev/null | wc -l | tr -d ' ')
  if [ "$n" -ge 11 ]; then
    /opt/anaconda3/bin/python3 digit_probe.py --model aya32b_api >> logs/digit_probe_aya32b_api.log 2>&1
    echo "=== AYA32B API COMPLETE $(date '+%F %T')" >> logs/queue.log; exit 0
  fi
  echo "attempt $i: $n/11 pages ok ($(date '+%T'))" >> logs/aya32b_api.log
  sleep 1800
done
echo "=== AYA32B API GAVE UP $(date '+%F %T')" >> logs/queue.log
