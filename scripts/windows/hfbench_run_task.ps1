$ErrorActionPreference = "Stop"
"identity: " + [Security.Principal.WindowsIdentity]::GetCurrent().Name
$dir = Join-Path $env:USERPROFILE 'hfbench'
New-Item -ItemType Directory -Force -Path $dir | Out-Null
Copy-Item (Join-Path $env:USERPROFILE 'audio_check.cmd') $dir -Force
Remove-Item (Join-Path $dir 'check.txt'),(Join-Path $dir 'levels.json') -ErrorAction SilentlyContinue
$action = New-ScheduledTaskAction -Execute (Join-Path $dir 'audio_check.cmd') -WorkingDirectory $dir
$principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive
Register-ScheduledTask -TaskName 'hfbench_audio_check' -Action $action -Principal $principal -Force | Out-Null
Start-ScheduledTask -TaskName 'hfbench_audio_check'
$t0 = Get-Date
do { Start-Sleep 3; $st = (Get-ScheduledTask -TaskName 'hfbench_audio_check').State } while ($st -eq 'Running' -and ((Get-Date) - $t0).TotalSeconds -lt 180)
"task state: $st after $([int]((Get-Date) - $t0).TotalSeconds) s"
Unregister-ScheduledTask -TaskName 'hfbench_audio_check' -Confirm:$false
Get-Content (Join-Path $dir 'check.txt')
