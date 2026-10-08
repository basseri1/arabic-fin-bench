#!/bin/zsh
# Regenerate REPORT.html after every model finishes (one regeneration at a time, never concurrently with itself).
B=/path/to/DocProcess/ocr_benchmark; cd $B
last=$(grep -c "^=== END" logs/queue.log)
while true; do
  n=$(grep -c "^=== END" logs/queue.log)
  if [ "$n" -gt "$last" ]; then
    last=$n
    echo "$(date '+%F %T') regenerating after END #$n" >> logs/auto_report.log
    /opt/anaconda3/bin/python3 make_report.py >> logs/auto_report.log 2>&1
  fi
  sleep 30
done
