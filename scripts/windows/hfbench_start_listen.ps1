param([double]$Minutes = 15, [double]$Setting = 20, [int]$Repeat = 1)
# Records true per-direction S:N during runs: listen-<stamp>[-<n>].json/.txt in %USERPROFILE%\hfbench.
# -Repeat N records N back-to-back files of -Minutes each (long campaigns), with a gap of a few seconds.
$ErrorActionPreference = "Stop"
$dir = Join-Path $env:USERPROFILE 'hfbench'
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMdd-HHmm')
$cmd = Join-Path $dir "audio_listen-$stamp.cmd"
$exe = '"C:\Program Files\Python312\Scripts\hfbench.exe"'
if ($Repeat -le 1) {
@"
@echo off
cd /d "$dir"
$exe audio listen --minutes $Minutes --setting $Setting --json listen-$stamp.json > listen-$stamp.txt 2>&1
echo EXIT %ERRORLEVEL% >> listen-$stamp.txt
"@ | Set-Content -Encoding ASCII $cmd
} else {
@"
@echo off
cd /d "$dir"
for /L %%i in (1,1,$Repeat) do (
  $exe audio listen --minutes $Minutes --setting $Setting --json listen-$stamp-%%i.json > listen-$stamp-%%i.txt 2>&1
  echo EXIT %%ERRORLEVEL%% >> listen-$stamp-%%i.txt
)
"@ | Set-Content -Encoding ASCII $cmd
}
$action = New-ScheduledTaskAction -Execute $cmd -WorkingDirectory $dir
$principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName "hfbench_audio_listen_$stamp" -Action $action -Principal $principal -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName "hfbench_audio_listen_$stamp"
"started: listen-$stamp ($Repeat x $Minutes min, setting $Setting)"
