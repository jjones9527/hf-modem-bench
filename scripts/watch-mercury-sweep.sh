#!/bin/bash
# Watch the Mercury sweep: alert on a Mercury freeze, chain 50k -> 5k, report the end.
: "${HFBENCH_HOST:?set HFBENCH_HOST=user@host of the bench machine}"; H=$HFBENCH_HOST; stage=${1:-50k}
sleep 60
while true; do
  out=$(ssh $H 'powershell -NoProfile -ExecutionPolicy Bypass -File %USERPROFILE%\hfbench_mstale.ps1' 2>/dev/null | tr -d '\r')
  s1=$(echo "$out" | sed -n 1p); s2=$(echo "$out" | sed -n 2p); st=$(echo "$out" | sed -n 3p)
  if [ "$st" = INSESSION ] && { [ "${s1:-0}" -gt 180 ] || [ "${s2:-0}" -gt 180 ]; }; then
    echo "ALERT $(date -u +%T): Mercury log quiet during a session: station 1 ${s1}s, station 2 ${s2}s"; exit 2
  fi
  if ssh $H 'schtasks /query /fo csv /nh' 2>/dev/null | grep -q '"\\hfbench_pilot","N/A","Ready"'; then
    if [ "$stage" = 50k ]; then
      echo "50K ENDED $(date -u +%T)"
      ssh $H 'powershell -NoProfile -Command "Get-Content (Get-ChildItem $env:USERPROFILE\hfbench\runs\sweep-mercury-50k\console-*.txt | Sort-Object LastWriteTime | Select-Object -Last 1).FullName"' 2>/dev/null | grep -E "^===|->|Recovery done|\*\*\*"
      ssh $H 'powershell -NoProfile -ExecutionPolicy Bypass -File %USERPROFILE%\hfbench_start_listen.ps1 -Minutes 150 -Setting 0 -Repeat 8' 2>/dev/null
      ssh $H 'powershell -NoProfile -ExecutionPolicy Bypass -File %USERPROFILE%\hfbench_start_campaign.ps1 -Campaign sweep-mercury-5k -MaxRuns 21 -AutoContinue -Recover -Relay' 2>&1 | grep -v -i "post-quantum\|store now\|pq.html"
      echo "5K STARTED $(date -u +%T)"; stage=5k; sleep 120; continue
    else
      echo "5K ENDED $(date -u +%T)"; exit 0
    fi
  fi
  sleep 120
done
