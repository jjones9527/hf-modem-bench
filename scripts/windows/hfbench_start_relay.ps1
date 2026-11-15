# Start the VARA logging relay (8320/8321 -> Mercury 2 on 8310/8311) in the desktop session.
$dir = Join-Path $env:USERPROFILE 'hfbench'
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMdd-HHmm')
$cmd = Join-Path $dir 'relay.cmd'
@"
@echo off
title VARA relay 8320 to Mercury 2 (8310) - close to stop
cd /d "$dir"
"C:\Program Files\Python312\python.exe" -I "$dir\vara_relay.py" --listen 8320 --target 8310 --log "$dir\relay-$stamp.log"
pause
"@ | Set-Content -Encoding ASCII $cmd
$action = New-ScheduledTaskAction -Execute $cmd -WorkingDirectory $dir
$principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero)
Register-ScheduledTask -TaskName 'hfbench_relay' -Action $action -Principal $principal -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName 'hfbench_relay'
"started relay, log: relay-$stamp.log"
