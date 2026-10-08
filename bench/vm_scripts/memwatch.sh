#!/bin/zsh
# Memory watchdog: if system free memory stays critically low (or swap balloons), kill the running
# benchmark model process so the machine never locks up; the queue moves on to the next model.
B=/path/to/DocProcess/ocr_benchmark; cd $B
low=0
while true; do
  free=$(memory_pressure -Q 2>/dev/null | awk -F': ' '/free percentage/ {gsub("%","",$2); print int($2)}')
  swap=$(sysctl -n vm.swapusage 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="used") {gsub("M","",$(i+2)); print $(i+2)}}')
  [ -z "$free" ] && free=100; [ -z "$swap" ] && swap=0
  if [ "$free" -lt 8 ] || [ "${swap%.*}" -gt 10000 ]; then low=$((low+1)); else low=0; fi
  if [ $low -ge 2 ]; then
    victims=$(pgrep -f "bench.py --model|run_surya.py|llama-server|digit_probe.py" | tr '\n' ' ')
    echo "$(date '+%F %T') CRITICAL free=${free}% swap=${swap}MB -> killing: $victims" >> logs/memwatch.log
    [ -n "$victims" ] && { kill -9 $victims 2>/dev/null; sleep 5; for v in $victims; do kill -0 $v 2>/dev/null && echo "$(date '+%T') pid $v survived kill -9 (state: $(ps -o stat= -p $v))" >> logs/memwatch.log; done; }
    low=0; sleep 30
  fi
  [ $(( $(date +%s) % 600 )) -lt 20 ] && echo "$(date '+%F %T') free=${free}% swap=${swap}MB" >> logs/memwatch.log
  sleep 20
done
