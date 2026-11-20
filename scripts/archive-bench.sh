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

# transmit-side crest logs (tx_crest_log.py: digital loopback, one line per burst)
mkdir -p "$A/peaks"
scp -q "$HFBENCH_HOST:hfbench/txcrest-*.jsonl" "$A/peaks/" 2>/dev/null || true
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
# Aether HF daemon logs and configs (hfbench_start_aether.ps1; UTC), ULTRA TNC logs and the
# mic-mute helper's log (hfbench_start_ultra.ps1, ultra_rxmute.py)
mkdir -p "$A/aether/station1" "$A/aether/station2" "$A/ultra"
scp -q "$HFBENCH_HOST:hfbench/aether/*.log" "$HFBENCH_HOST:hfbench/aether/level.txt" "$A/aether/" 2>/dev/null || true
for st in 1 2; do scp -q "$HFBENCH_HOST:hfbench/aether/station$st/station.toml" "$A/aether/station$st/" 2>/dev/null || true; done
scp -q "$HFBENCH_HOST:hfbench/ultra/*.log" "$HFBENCH_HOST:hfbench/ultra/*.conf" "$A/ultra/" 2>/dev/null || true
echo "aether: $(ls "$A/aether" | wc -l | tr -d ' ') files, ultra: $(ls "$A/ultra" | wc -l | tr -d ' ') files"

# Winlink session logs and ARDOP TNC logs, both installs
for d in "${dates[@]}"; do
  for st in 1 2; do
    if [ $st = 1 ]; then inst='C:\RMS Express'; calls="VA3ZTF"; else inst='C:\RMS Express 2'; calls="VE3XZQ VA3ZTF"; fi
    out="$A/winlink/station$st"
    # station 2 has two Winlink callsigns (VE3XZQ; VA3ZTF since the VARA runs, 18 Nov 2026):
    # the first keeps the old file names, others go in a subfolder named for the callsign
    first=1
    for call in $calls; do
      o=$out; [ $first = 1 ] || { o="$out/$call"; mkdir -p "$o"; }; first=0
      for k in "RMS Express" Vara; do
        f="$inst\\$call\\Logs\\$k $d.log"
        win "if exist \"$f\" type \"$f\"" > "$o/$k $d.log"
      done
      find "$o" -name "*$d.log" -size 0 -delete
    done
    for k in ARQSession Debug Exceptions; do
      f="$inst\\Logs\\ARDOP_WinTNC_${k}_$d.log"
      win "if exist \"$f\" type \"$f\"" > "$out/ARDOP_WinTNC_${k}_$d.log"
    done
    find "$out" -name "*$d.log" -size 0 -delete
  done
  echo "logs $d: station1 $(ls "$A/winlink/station1" | grep -c "$d" || true), station2 $(ls "$A/winlink/station2" | grep -c "$d" || true)"
done
