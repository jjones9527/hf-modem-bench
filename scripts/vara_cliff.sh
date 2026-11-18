#!/usr/bin/env bash
# VARA HF cliff search (operator, 18 Nov 2026): after the VARA chain in LOG ends, for each
# drive level set VARA's ALC drive on both stations, reconnect Winlink (recover), run the
# cliff-vara-d<N> campaign (scripts/bench_chain.sh), and stop after the first step that
# delivers nothing. Restores the bench level (-3) and reconnects at the end.
#   HFBENCH_HOST=user@host scripts/vara_cliff.sh LOG 6 9 12 15
set -u
H=${HFBENCH_HOST:?set HFBENCH_HOST=user@host}
L=${1:?log file}; shift
here=$(cd "$(dirname "$0")" && pwd)
ps() { ssh -o LogLevel=error -o ServerAliveInterval=30 "$H" "powershell -NoProfile -ExecutionPolicy Bypass -File %USERPROFILE%\\$1" 2>&1 | tr -d '\r'; }
cmd() { ssh -o LogLevel=error -o ServerAliveInterval=30 "$H" "$1" 2>&1 | tr -d '\r'; }
say() { echo "$(date -u +%FT%TZ) $*" | tee -a "$L"; }
hf='"C:\Program Files\Python312\Scripts\hfbench.exe"'
until grep -q 'CHAIN DONE (sweep-vara-50k' "$L" 2>/dev/null; do sleep 60; done
for d in "$@"; do
  c=cliff-vara-d$d
  say "CLIFF: VARA drive -$d"
  ps "hfbench_vara_drive.ps1 -Level -$d" >> "$L"
  ps "hfbench_desktop.ps1 -HfArgs \"recover -d runs\\$c $c-0001\" -Out runs\\$c\\recover-pre.txt" >> "$L"
  "$here/bench_chain.sh" "$L" VARA "$c:2:relay"
  got=$(cmd "cd hfbench && $hf results -d runs\\$c" | grep -E '^total:' | sed -E 's/^total: ([0-9]+)\/.*/\1/')
  say "CLIFF: $c delivered ${got:-?}"
  [ "${got:-1}" = 0 ] && { say "CLIFF: reached at drive -$d"; break; }
done
ps "hfbench_vara_drive.ps1 -Level -3" >> "$L"
ps "hfbench_desktop.ps1 -HfArgs \"recover -d runs\\cliff-vara-d6 cliff-vara-d6-0001\" -Out runs\\cliff-vara-d6\\recover-end.txt" >> "$L"
say "CLIFF DONE: VARA back at drive -3"
