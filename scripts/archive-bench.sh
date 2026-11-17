#!/usr/bin/env bash
# Copy every raw result file from the bench machine into logs/archive/ (gitignored).
# Safe to re-run: files are overwritten with the current copy, nothing is deleted.
#
#   HFBENCH_HOST=user@host scripts/archive-bench.sh [YYYYMMDD ...]
#
# With no dates, the Winlink/ARDOP logs for today and yesterday (UTC) are copied.
# Campaign folders (run sheet, events, manifest, console output, relay.txt), listen
# recordings, tone-check results, bench-relay logs Mercury's engine logs and Data2G's host logs are
# always copied in full. Dates are YYYYMMDD (the Winlink log file names).
set -euo pipefail
: "${HFBENCH_HOST:?set HFBENCH_HOST=user@host of the bench machine}"
cd "$(dirname "$0")/.."
A=logs/archive
mkdir -p "$A/listen" "$A/levels" "$A/winlink/station1" "$A/winlink/station2" "$A/relay" "$A/mercury"

dates=("$@")
if [ ${#dates[@]} -eq 0 ]; then
  dates=("$(date -u +%Y%m%d)" "$(date -u -v-1d +%Y%m%d 2>/dev/null || date -u -d yesterday +%Y%m%d)")
fi

win() { ssh -o ConnectTimeout=10 "$HFBENCH_HOST" "$@" 2>/dev/null; }

# campaigns: every runs\<name> folder that has a run sheet
for c in $(win 'cd %USERPROFILE%\hfbench\runs && for /d %d in (*) do @if exist %d\runsheet.csv echo %d' | tr -d '\r'); do
  mkdir -p "$A/$c"
  win "cd %USERPROFILE%\\hfbench && hfbench manifest -d runs\\$c" >/dev/null || true
  scp -q "$HFBENCH_HOST:hfbench/runs/$c/*.csv" "$HFBENCH_HOST:hfbench/runs/$c/*.jsonl" "$HFBENCH_HOST:hfbench/runs/$c/*.json" \
         "$HFBENCH_HOST:hfbench/runs/$c/console-*.txt" "$HFBENCH_HOST:hfbench/runs/$c/relay.txt" "$A/$c/" 2>/dev/null || true
  echo "campaign $c: $(ls "$A/$c" | wc -l | tr -d ' ') files"
done

scp -q "$HFBENCH_HOST:hfbench/listen-*.json" "$HFBENCH_HOST:hfbench/listen-*.txt" "$A/listen/" 2>/dev/null || true
echo "listen: $(ls "$A/listen" | wc -l | tr -d ' ') files"

# bench relay logs (VARA-protocol modems) and Mercury's engine logs (local time)
scp -q "$HFBENCH_HOST:hfbench/relay-*.log" "$A/relay/" 2>/dev/null || true
scp -q "$HFBENCH_HOST:C:/Program Files/MercuryHF/logs/mercury_engine.log" "$A/mercury/station1_engine.log" 2>/dev/null || true
scp -q "$HFBENCH_HOST:C:/Program Files/MercuryHF 2/logs/mercury_engine.log" "$A/mercury/station2_engine.log" 2>/dev/null || true
# Data2G host logs (hfbench_start_data2g.ps1: stderr, local time) and its start/stop log
mkdir -p "$A/data2g"
scp -q "$HFBENCH_HOST:hfbench/data2g/*.log" "$A/data2g/" 2>/dev/null || true
echo "relay: $(ls "$A/relay" | wc -l | tr -d ' ') files, mercury: $(ls "$A/mercury" | wc -l | tr -d ' ') files, data2g: $(ls "$A/data2g" | wc -l | tr -d ' ') files"

# Winlink session logs and ARDOP TNC logs, both installs
for d in "${dates[@]}"; do
  for st in 1 2; do
    if [ $st = 1 ]; then inst='C:\RMS Express'; call=VA3ZTF; else inst='C:\RMS Express 2'; call=VE3XZQ; fi
    out="$A/winlink/station$st"
    f="$inst\\$call\\Logs\\RMS Express $d.log"
    win "if exist \"$f\" type \"$f\"" > "$out/RMS Express $d.log"
    for k in ARQSession Debug Exceptions; do
      f="$inst\\Logs\\ARDOP_WinTNC_${k}_$d.log"
      win "if exist \"$f\" type \"$f\"" > "$out/ARDOP_WinTNC_${k}_$d.log"
    done
    find "$out" -name "*$d.log" -size 0 -delete
  done
  echo "logs $d: station1 $(ls "$A/winlink/station1" | grep -c "$d" || true), station2 $(ls "$A/winlink/station2" | grep -c "$d" || true)"
done
