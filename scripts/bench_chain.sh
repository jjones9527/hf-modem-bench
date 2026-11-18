#!/usr/bin/env bash
# Run bench campaigns one after another, unattended, from this machine over SSH.
#   HFBENCH_HOST=user@host scripts/bench_chain.sh LOG MODEM CAMPAIGN:RUNS[:relay] ...
# MODEM: ARDOP, VARA, Mercury or Data2G (which hang check to use, and how to restart it).
# For each campaign: start it on the bench (hfbench_start_campaign.ps1 -AutoContinue
# -Recover [-Relay]), log every run result, watch for a hung modem (Mercury, Data2G: its
# log quiet >240 s during a session -> run dnc, restart that station's modem, recover,
# carry on), retry once after the runner's first-run COM timeout, and verify the
# results (--verify). One line per event in LOG (and stdout). Waits first if a campaign
# is already running. The bench helper scripts live in the bench user's profile folder.
set -u
H=${HFBENCH_HOST:?set HFBENCH_HOST=user@host}
L=${1:?log file}; M=${2:?modem}; shift 2
ps() { ssh -o LogLevel=error -o ServerAliveInterval=30 "$H" "powershell -NoProfile -ExecutionPolicy Bypass -File %USERPROFILE%\\$1" 2>&1 | tr -d '\r'; }
cmd() { ssh -o LogLevel=error -o ServerAliveInterval=30 "$H" "$1" 2>&1 | tr -d '\r'; }
say() { echo "$(date -u +%FT%TZ) $*" | tee -a "$L"; }
hf='"C:\Program Files\Python312\Scripts\hfbench.exe"'
pilot_running() { cmd 'schtasks /query /tn hfbench_pilot /fo csv /nh' | grep -q '"Running"'; }
newest_console() { cmd "powershell -NoProfile -Command \"Get-ChildItem %USERPROFILE%\\hfbench\\runs\\$1\\console-*.txt | Sort LastWriteTime | Select -Last 1 | % Name\""; }

restart_modem() {  # $1 station
  case $M in
    Data2G) ps "hfbench_start_data2g.ps1 -Station $1" >> "$L" ;;
    Mercury) ps "hfbench_restart_mercury.ps1 -Station $1" >> "$L" ;;
    VARA) ps "hfbench_start_vara.ps1 -Station $1" >> "$L" ;;
  esac
}

run_campaign() {  # $1 campaign $2 max runs $3 "-Relay" or ""
  local c=$1 n=$2 relay=$3 tries=0 con seen out
  while :; do
    ps "hfbench_start_campaign.ps1 -Campaign $c -MaxRuns $n -AutoContinue -Recover $relay" >> "$L"
    sleep 20; con=$(newest_console "$c"); say "$c started ($con)"; seen=0
    while pilot_running; do
      sleep 30
      local res k
      res=$(cmd "type %USERPROFILE%\\hfbench\\runs\\$c\\$con" | grep -E ' -> .*(completed|timeboxed|dnc|invalid)')
      k=$(echo "$res" | grep -c ' -> ')
      if [ "$k" -gt "$seen" ]; then echo "$res" | tail -n $((k - seen)) | while read -r l; do say "$l"; done; seen=$k; fi
      case $M in Mercury) st=$(ps hfbench_mstale.ps1) ;; Data2G) st=$(ps hfbench_dstale.ps1) ;; *) continue ;; esac
      local s1 s2 state; s1=$(echo "$st" | sed -n 1p); s2=$(echo "$st" | sed -n 2p); state=$(echo "$st" | sed -n 3p)
      if [ "$state" = INSESSION ] && { [ "${s1:-0}" -gt 240 ] || [ "${s2:-0}" -gt 240 ]; } 2>/dev/null; then
        local bad=1 rid; [ "${s2:-0}" -gt "${s1:-0}" ] && bad=2
        rid=$(cmd "type %USERPROFILE%\\hfbench\\runs\\$c\\$con" | grep '^=== ' | tail -1 | sed -E 's/^=== ([^:]+):.*/\1/')
        say "HANG $M station $bad (log quiet ${s1}s / ${s2}s) in $rid: run dnc, restart, recover"
        cmd "powershell -NoProfile -Command \"Stop-ScheduledTask hfbench_pilot; Start-Sleep 2; Get-CimInstance Win32_Process | ? { \$_.Name -eq 'hfbench.exe' -and \$_.CommandLine -match ' run ' } | % { Stop-Process -Id \$_.ProcessId -Force }\"" >> "$L"
        cmd "cd hfbench && $hf end -d runs\\$c --run-id $rid dnc --notes \"$M station $bad hung: log quiet ${s1}/${s2} s in session; restarted by bench_chain.sh\"" >> "$L"
        restart_modem $bad
        ps "hfbench_desktop.ps1 -HfArgs \"recover -d runs\\$c $rid\" -Out runs\\$c\\recover-hang.txt" >> "$L"
        continue 2
      fi
    done
    out=$(cmd "type %USERPROFILE%\\hfbench\\runs\\$c\\$con")
    if echo "$out" | grep -q 'could not prepare' && ! echo "$out" | grep -q ' -> ' && [ $tries -lt 1 ]; then
      tries=$((tries + 1)); say "$c: runner COM timeout on first run, retrying"; continue
    fi
    break
  done
  local pl=Text_5KB; case $c in *50k*|smoke*|cal*|peak*|*level*) pl=Text_50KB ;; esac
  local v; v=$(cmd "cd hfbench && $hf results -d runs\\$c --verify payloads\\$pl"); echo "$v" >> "$L"
  say "$c ended: $(echo "$v" | grep -E '^total:|attachments checked' | tr '\n' ' ')"
}

while pilot_running; do sleep 60; done
for spec in "$@"; do
  IFS=: read -r c n r <<<"$spec"
  run_campaign "$c" "$n" "$([ "${r:-}" = relay ] && echo -Relay)"
done
say "CHAIN DONE ($*)"
