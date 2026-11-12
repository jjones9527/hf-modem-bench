# Run one hfbench.winlink_ui action in the desktop session and print its log.
#   hfbench_ui_do.ps1 -Call VA3ZTF -Do delete-outbox [-Arg X] [-TimeoutS 300]
param([Parameter(Mandatory)][string]$Call, [Parameter(Mandatory)][string]$Do, [string]$Arg = "", [int]$TimeoutS = 300)
$ErrorActionPreference = "Stop"
$dir = Join-Path $env:USERPROFILE 'hfbench'
$log = Join-Path $dir "ui_do.log"
Remove-Item $log, "$log.err" -ErrorAction SilentlyContinue
$cmd = Join-Path $dir 'ui_do.cmd'
$q = if ($Arg) { "`"$Arg`"" } else { "" }
"@echo off`r`ncd /d `"$dir`"`r`n`"C:\Program Files\Python312\python.exe`" -m hfbench.winlink_ui `"$log`" $Call $Do $q > `"$log.err`" 2>&1" | Set-Content -Encoding ASCII $cmd
$action = New-ScheduledTaskAction -Execute $cmd -WorkingDirectory $dir
$principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive
Register-ScheduledTask -TaskName 'hfbench_ui_do' -Action $action -Principal $principal -Force | Out-Null
Start-ScheduledTask -TaskName 'hfbench_ui_do'
$t0 = Get-Date
do { Start-Sleep 2 } while ((Get-ScheduledTask -TaskName 'hfbench_ui_do').State -eq 'Running' -and ((Get-Date) - $t0).TotalSeconds -lt $TimeoutS)
"task state: " + (Get-ScheduledTask -TaskName 'hfbench_ui_do').State + " after $([int]((Get-Date) - $t0).TotalSeconds) s"
Unregister-ScheduledTask -TaskName 'hfbench_ui_do' -Confirm:$false
Get-Content $log -ErrorAction SilentlyContinue
Get-Content "$log.err" -ErrorAction SilentlyContinue
