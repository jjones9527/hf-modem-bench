param([Parameter(Mandatory)][ValidateSet(1,2)][int]$Station)
# Start (or restart) one station's VARA HF 4.9.1 in the desktop session (task hfbench_vara<N>):
# stop every VARA.exe from that station's folder (C:\VARA or C:\VARA 2), start one again,
# and wait until it listens on its control port (8300 / 8310). Winlink's VARA auto launch stays off.
# Its settings (sound card, ALC drive level, ports) are in VARA.ini in the same folder.
# Every start is appended to hfbench\vara-restarts.log.
$ErrorActionPreference = "Stop"
$d = if ($Station -eq 1) { 'C:\VARA' } else { 'C:\VARA 2' }
$port = if ($Station -eq 1) { 8300 } else { 8310 }
$exe = Join-Path $d 'VARA.exe'
$log = Join-Path $env:USERPROFILE 'hfbench\vara-restarts.log'
$old = @(Get-CimInstance Win32_Process -Filter "Name='VARA.exe'" | Where-Object { $_.ExecutablePath -eq $exe })
foreach ($p in $old) { Stop-Process -Id $p.ProcessId -Force }
Start-Sleep 3
$action = New-ScheduledTaskAction -Execute $exe -WorkingDirectory $d
$principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName "hfbench_vara$Station" -Action $action -Principal $principal -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName "hfbench_vara$Station"
$t0 = Get-Date
while (-not (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)) {
    if (((Get-Date) - $t0).TotalSeconds -gt 90) { throw "station $Station VARA not listening on $port after 90 s" }
    Start-Sleep 2
}
$new = @(Get-CimInstance Win32_Process -Filter "Name='VARA.exe'" | Where-Object { $_.ExecutablePath -eq $exe })
$line = "{0} UTC station {1}: stopped {2}, started {3}" -f (Get-Date).ToUniversalTime().ToString('yyyy-MM-dd HH:mm:ss'), $Station, (($old | ForEach-Object ProcessId) -join ','), (($new | ForEach-Object ProcessId) -join ',')
Add-Content -Path $log -Value $line
$line
