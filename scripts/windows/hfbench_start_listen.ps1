param([double]$Minutes = 15, [double]$Setting = 20)
$ErrorActionPreference = "Stop"
$dir = Join-Path $env:USERPROFILE 'hfbench'
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMdd-HHmm')
$cmd = Join-Path $dir "audio_listen-$stamp.cmd"
@"
@echo off
cd /d "$dir"
"C:\Program Files\Python312\Scripts\hfbench.exe" audio listen --minutes $Minutes --setting $Setting --json listen-$stamp.json > listen-$stamp.txt 2>&1
echo EXIT %ERRORLEVEL% >> listen-$stamp.txt
"@ | Set-Content -Encoding ASCII $cmd
$action = New-ScheduledTaskAction -Execute $cmd -WorkingDirectory $dir
$principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive
Register-ScheduledTask -TaskName "hfbench_audio_listen_$stamp" -Action $action -Principal $principal -Force | Out-Null
Start-ScheduledTask -TaskName "hfbench_audio_listen_$stamp"
"started: listen-$stamp ($Minutes min, setting $Setting)"
