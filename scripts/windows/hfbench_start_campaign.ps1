param([int]$MaxRuns = 1, [switch]$AutoContinue, [string]$Campaign = "pilot01")
$ac = if ($AutoContinue) { ' --auto-continue 120' } else { '' }
$ErrorActionPreference = "Stop"
$dir = Join-Path $env:USERPROFILE 'hfbench'
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMdd-HHmm')
$out = "runs\$Campaign\console-$stamp.txt"
$cmd = Join-Path $dir 'pilot.cmd'
@"
@echo off
set PYTHONUNBUFFERED=1
cd /d "$dir"
title hfbench $Campaign - keep hands off the Winlink windows
powershell -NoProfile -Command "& 'C:\Program Files\Python312\Scripts\hfbench.exe' run -d runs\$Campaign --automate --max-runs $MaxRuns$ac 2>&1 | Tee-Object -FilePath '$out'"
"@ | Set-Content -Encoding ASCII $cmd
$action = New-ScheduledTaskAction -Execute $cmd -WorkingDirectory $dir
$principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive
Register-ScheduledTask -TaskName 'hfbench_pilot' -Action $action -Principal $principal -Force | Out-Null
Start-ScheduledTask -TaskName 'hfbench_pilot'
"started pilot, console log: $out"
