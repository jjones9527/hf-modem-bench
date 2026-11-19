param([switch]$Stop, [double]$Tail = 0.6)
# Start (or -Stop) ultra_rxmute.py in the desktop session: mutes each station's microphone
# while its ULTRA transmits, plus -Tail seconds (see the script). Needs pycaw. Log:
# hfbench\ultra\rxmute.log. Only for ULTRA: stop it before testing another modem.
$ErrorActionPreference = "Stop"
$dir = Join-Path $env:USERPROFILE 'hfbench\ultra'
$task = 'hfbench_rxmute'
$mine = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match 'ultra_rxmute\.py' })
foreach ($p in $mine) { Stop-Process -Id $p.ProcessId -Force }
if ($mine) {
    Start-Sleep 1
    # a killed helper can't unmute: do it here
    & "C:\Program Files\Python312\python.exe" -c "import sys; sys.path.insert(0, r'$dir'); from ultra_rxmute import microphone, STATIONS; [microphone(n)[1].SetMute(False, None) for _, n in STATIONS.values()]"
}
if ($Stop) { "rxmute stopped ($($mine.Count) process(es)); microphones unmuted"; return }
$cmd = Join-Path $dir 'rxmute.cmd'
"@echo off`r`ncd /d `"$dir`"`r`n`"C:\Program Files\Python312\python.exe`" ultra_rxmute.py --tail $Tail >> rxmute-console.txt 2>&1" | Set-Content -Encoding ASCII $cmd
if (-not (Get-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue)) {
    $action = New-ScheduledTaskAction -Execute $cmd -WorkingDirectory $dir
    $principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive
    $settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    Register-ScheduledTask -TaskName $task -Action $action -Principal $principal -Settings $settings -Force | Out-Null
}
Start-ScheduledTask -TaskName $task
Start-Sleep 4
Get-Content (Join-Path $dir 'rxmute.log') -Tail 1
