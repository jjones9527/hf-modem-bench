param([int]$MaxRuns = 1, [switch]$AutoContinue, [switch]$Recover, [string]$Campaign = "pilot01", [switch]$Relay)
# -Relay: VARA-type modems. Makes sure the bench relay (hfbench_start_relay.ps1, holding
# Winlink's 5-min P2P timer DISCONNECTs) is running in front of station 2's modem, and
# writes its state into the campaign folder (relay.txt). Station 2's Winlink must use port 8320.
$ac = if ($AutoContinue) { ' --auto-continue 120' } else { '' }
if ($Recover) { $ac += ' --recover' }
$ErrorActionPreference = "Stop"
$dir = Join-Path $env:USERPROFILE 'hfbench'
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMdd-HHmm')
$out = "runs\$Campaign\console-$stamp.txt"
# Mercury's GUI can keep running after its window is closed (15 Nov: three station-2
# copies on one sound card). If any Mercury runs, require exactly one per station: the
# GUI, or a standalone engine (mercury*.exe, hfbench_start_mercury_engine.ps1).
$merc = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'mercury*.exe' })
if ($merc.Count) {
    foreach ($d in 'C:\Program Files\MercuryHF\', 'C:\Program Files\MercuryHF 2\') {
        $mine = @($merc | Where-Object { $_.ExecutablePath -and (Split-Path $_.ExecutablePath) -eq $d.TrimEnd('\') })
        if ($mine.Count -ne 1) { throw "$($mine.Count) Mercury processes from $d (need exactly 1): end the extra ones in Task Manager" }
        "Mercury in ${d}: $($mine[0].Name) (pid $($mine[0].ProcessId))"
    }
}
if ($Relay) {
    $r = & (Join-Path $env:USERPROFILE 'hfbench_start_relay.ps1')
    $state = "$stamp UTC: $r"
    Add-Content -Path (Join-Path $dir "runs\$Campaign\relay.txt") -Value $state
    $state
    Start-Sleep 3
    if (-not (Get-NetTCPConnection -LocalPort 8320 -State Listen -ErrorAction SilentlyContinue)) { throw "relay is not listening on 8320" }
}
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
