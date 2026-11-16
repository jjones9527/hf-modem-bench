param([Parameter(Mandatory)][ValidateSet(1,2)][int]$Station)
# Restart one station's Mercury GUI (operator-approved 16 Nov 2026, for Mercury freezes):
# stop every mercury-ui.exe from that station's folder, start one again in the desktop
# session (task hfbench_mercury<N>), and wait until it listens on its control port.
# Its settings (sound card, tx_gain_db, ports) are in mercury.ini in the same folder.
# Every restart is appended to hfbench\mercury-restarts.log.
$ErrorActionPreference = "Stop"
$d = if ($Station -eq 1) { 'C:\Program Files\MercuryHF' } else { 'C:\Program Files\MercuryHF 2' }
$port = if ($Station -eq 1) { 8300 } else { 8310 }
$exe = Join-Path $d 'mercury-ui.exe'
$log = Join-Path $env:USERPROFILE 'hfbench\mercury-restarts.log'
$old = @(Get-CimInstance Win32_Process -Filter "Name='mercury-ui.exe'" | Where-Object { $_.ExecutablePath -eq $exe })
foreach ($p in $old) { Stop-Process -Id $p.ProcessId -Force }
Start-Sleep 3
$action = New-ScheduledTaskAction -Execute $exe -WorkingDirectory $d
$principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName "hfbench_mercury$Station" -Action $action -Principal $principal -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName "hfbench_mercury$Station"
$t0 = Get-Date
while (-not (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)) {
    if (((Get-Date) - $t0).TotalSeconds -gt 90) { throw "station $Station Mercury not listening on $port after 90 s" }
    Start-Sleep 2
}
$new = @(Get-CimInstance Win32_Process -Filter "Name='mercury-ui.exe'" | Where-Object { $_.ExecutablePath -eq $exe })
$line = "{0} UTC station {1}: stopped {2}, started {3}" -f (Get-Date).ToUniversalTime().ToString('yyyy-MM-dd HH:mm:ss'), $Station, (($old | ForEach-Object ProcessId) -join ','), (($new | ForEach-Object ProcessId) -join ',')
Add-Content -Path $log -Value $line
$line
