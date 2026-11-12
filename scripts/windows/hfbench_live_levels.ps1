# Open a visible console on the bench desktop that re-runs the tone check every few
# seconds (hfbench audio check --loop) so levels can be trimmed live. Close the window
# or press Ctrl+C in it to stop.
param([int]$Snr = 20)
$ErrorActionPreference = "Stop"
$dir = Join-Path $env:USERPROFILE 'hfbench'
$cmd = Join-Path $dir 'live_levels.cmd'
@"
@echo off
title hfbench live levels - adjust Windows speaker levels; close this window when done
cd /d "$dir"
"C:\Program Files\Python312\Scripts\hfbench.exe" audio check --loop --snr $Snr --seconds 2
pause
"@ | Set-Content -Encoding ASCII $cmd
$action = New-ScheduledTaskAction -Execute $cmd -WorkingDirectory $dir
$principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive
Register-ScheduledTask -TaskName 'hfbench_live_levels' -Action $action -Principal $principal -Force | Out-Null
Start-ScheduledTask -TaskName 'hfbench_live_levels'
"started live levels (WGN $Snr)"
