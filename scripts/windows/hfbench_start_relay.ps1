param([string]$Extra = "--hold-timeout-disconnect", [switch]$Restart)
# The bench relay for VARA-type modems (VARA HF, Mercury, Data2G): station 2's Winlink
# connects to 8320/8321, the relay passes everything to station 2's modem on 8310/8311
# and logs it (relay-<stamp>.log). By default it holds Winlink's 5-min P2P timer
# DISCONNECTs (see vara_relay.py); -Extra "" makes it a plain logger.
# If a relay is already running it is left alone (restarting it would drop Winlink's
# connection to the modem); -Restart stops it first.
$dir = Join-Path $env:USERPROFILE 'hfbench'
$running = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match 'vara_relay\.py' }
if ($running -and -not $Restart) {
    $log = if ($running[0].CommandLine -match '--log "?([^"]+?\.log)') { Split-Path $Matches[1] -Leaf } else { '?' }
    $hold = if ($running[0].CommandLine -match 'hold-timeout-disconnect') { 'holding timer DISCONNECTs' } else { 'logging only' }
    "relay already running ($hold), log: $log"
    return
}
if ($running) { Stop-ScheduledTask -TaskName 'hfbench_relay' -ErrorAction SilentlyContinue; $running | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }; Start-Sleep 2 }
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMdd-HHmm')
$cmd = Join-Path $dir 'relay.cmd'
@"
@echo off
title hfbench relay 8320 to station 2 modem (8310) - leave running during VARA-type campaigns
cd /d "$dir"
"C:\Program Files\Python312\python.exe" -I "$dir\vara_relay.py" --listen 8320 --target 8310 --log "$dir\relay-$stamp.log" $Extra
pause
"@ | Set-Content -Encoding ASCII $cmd
$action = New-ScheduledTaskAction -Execute $cmd -WorkingDirectory $dir
$principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero)
Register-ScheduledTask -TaskName 'hfbench_relay' -Action $action -Principal $principal -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName 'hfbench_relay'
"started relay, log: relay-$stamp.log"
