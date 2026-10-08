#!/bin/bash
# Re-launch a sequential hosted run as N parallel workers over the pages it has not finished (no page is sent twice).
# usage: split_hosted.sh <name> <out_dir> <N> <runner args...>
cd ~/ocr_benchmark; name=$1; out=$2; n=$3; shift 3
pkill -f -- "--name $name " ; sleep 3
ls pages32/plain/*.png | xargs -n1 basename | sed 's/\.png$//' | while read pg; do
  [ -s "$out/$pg.md" ] || echo $pg; done > _tmp/remaining_$name.txt
rm -f _tmp/rem_${name}_*; split -n l/$n -d _tmp/remaining_$name.txt _tmp/rem_${name}_
for part in _tmp/rem_${name}_*; do
  [ -s $part ] || continue
  PAGES_DIR=pages32/plain ~/venv/bin/python "$@" --name $name --out $out --only "$(paste -sd, $part)" > logs/run32_${name}_$(basename $part).log 2>&1 &
done
echo "$name: $(wc -l < _tmp/remaining_$name.txt) pages left, $n workers"
