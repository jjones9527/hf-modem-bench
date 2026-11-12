# Run one hfbench command in the logged-in desktop session (audio access) and wait for it.
#   hfbench_desktop.ps1 -HfArgs "audio qam --json qam.json" -Out qam.txt [-TimeoutS 600]
# Output goes to %USERPROFILE%\hfbench\<Out>, which is printed when the command finishes.
param([Parameter(Mandatory)][string]$HfArgs, [Parameter(Mandatory)][string]$Out, [int]$TimeoutS = 600)
$ErrorActionPreference = "Stop"
$dir = Join-Path $env:USERPROFILE 'hfbench'
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMdd-HHmmss')
$cmd = Join-Path $dir "desktop-$stamp.cmd"
@"
@echo off
cd /d "$dir"
"C:\Program Files\Python312\Scripts\hfbench.exe" $HfArgs > "$Out" 2>&1
echo EXIT %ERRORLEVEL% >> "$Out"
"@ | Set-Content -Encoding ASCII $cmd
$task = "hfbench_desktop_$stamp"
$action = New-ScheduledTaskAction -Execute $cmd -WorkingDirectory $dir
$principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive
Register-ScheduledTask -TaskName $task -Action $action -Principal $principal -Force | Out-Null
Start-ScheduledTask -TaskName $task
$t0 = Get-Date
do { Start-Sleep 3; $st = (Get-ScheduledTask -TaskName $task).State } while ($st -eq 'Running' -and ((Get-Date) - $t0).TotalSeconds -lt $TimeoutS)
"task state: $st after $([int]((Get-Date) - $t0).TotalSeconds) s"
Unregister-ScheduledTask -TaskName $task -Confirm:$false
Remove-Item $cmd -ErrorAction SilentlyContinue
Get-Content (Join-Path $dir $Out)
