#!/usr/bin/env bash
# Aether HF cliff search (operator, 20 Nov 2026; as VARA's, 18 Nov): after the Aether chain in LOG ends, for each
# step (dB under the bench level) set Aether's tx_level on both stations (saved, so recovery's
# restarts keep it), reconnect Winlink (recover), run the
# cliff-aether-d<N> campaign (scripts/bench_chain.sh), and stop after the first step that
# delivers nothing. Restores the bench level (0.35) and reconnects at the end.
#   HFBENCH_HOST=user@host scripts/aether_cliff.sh LOG 3 6 9 12 15 18
set -u
H=${HFBENCH_HOST:?set HFBENCH_HOST=user@host}
L=${1:?log file}; shift
here=$(cd "$(dirname "$0")" && pwd)
ps() { ssh -o LogLevel=error -o ServerAliveInterval=30 "$H" "powershell -NoProfile -ExecutionPolicy Bypass -File %USERPROFILE%\\$1" 2>&1 | tr -d '\r'; }
cmd() { ssh -o LogLevel=error -o ServerAliveInterval=30 "$H" "$1" 2>&1 | tr -d '\r'; }
say() { echo "$(date -u +%FT%TZ) $*" | tee -a "$L"; }
hf='"C:\Program Files\Python312\Scripts\hfbench.exe"'
until grep -q 'CHAIN DONE (sweep-aether-50k' "$L" 2>/dev/null; do sleep 60; done
for d in "$@"; do
  c=cliff-aether-d$d; lv=$(python3 -c "print(round(0.35*10**(-$d/20),3))")
  say "CLIFF: Aether tx_level $lv (-$d dB)"
  for s in 1 2; do ps "hfbench_start_aether.ps1 -Station $s -Level $lv" >> "$L"; done
  ps "hfbench_desktop.ps1 -HfArgs \"recover -d runs\\$c $c-0001\" -Out runs\\$c\\recover-pre.txt" >> "$L"
  "$here/bench_chain.sh" "$L" Aether "$c:2:relay"
  # delivered = the 'deliv' column summed over the step's runs (the summary prints no
  # 'total:' line when nothing was attempted, so it can't be read from there)
  got=$(cmd "cd hfbench && $hf results -d runs\\$c" | awk -v c="$c" '$1 ~ "^"c"-" {s += $3} END {print s + 0}')
  say "CLIFF: $c delivered ${got:-?}"
  [ "${got:-1}" = 0 ] && { say "CLIFF: reached at -$d dB (tx_level $lv)"; break; }
done
for s in 1 2; do ps "hfbench_start_aether.ps1 -Station $s -Level 0.35" >> "$L"; done
ps "hfbench_desktop.ps1 -HfArgs \"recover -d runs\\cliff-aether-d3 cliff-aether-d3-0001\" -Out runs\\cliff-aether-d3\\recover-end.txt" >> "$L"
say "CLIFF DONE: Aether back at tx_level 0.35"
