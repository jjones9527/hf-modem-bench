param([Parameter(Mandatory)][ValidateSet(1,2)][int]$Station, [string]$Exe = 'mercury-pr581.exe', [switch]$Gui)
# Run one station's Mercury as the standalone engine instead of the GUI, for testing a
# development build (Rhizomatica/mercury PR #581): the Windows GUI has the engine built in
# (mercury-ui.exe), so a branch's mercury.exe only takes effect when it runs on its own.
# It reads the same mercury.ini (sound cards, ports, tx_gain_db) from the station's folder
# and logs to logs\mercury_engine.log there. The GUI must be closed first (by the operator).
#   hfbench_start_mercury_engine.ps1 -Station 2               # start mercury-pr581.exe -C mercury.ini
#   hfbench_start_mercury_engine.ps1 -Station 2 -Gui          # back to the GUI (stops the engine)
$ErrorActionPreference = "Stop"
$d = if ($Station -eq 1) { 'C:\Program Files\MercuryHF' } else { 'C:\Program Files\MercuryHF 2' }
$port = if ($Station -eq 1) { 8300 } else { 8310 }
$log = Join-Path $env:USERPROFILE 'hfbench\mercury-restarts.log'
$path = Join-Path $d $Exe
$engines = @(Get-CimInstance Win32_Process -Filter "Name='$Exe'" | Where-Object { $_.ExecutablePath -eq $path })
if ($Gui) {
    foreach ($p in $engines) { Stop-Process -Id $p.ProcessId -Force }
    Start-Sleep 3
    & (Join-Path $env:USERPROFILE 'hfbench_restart_mercury.ps1') -Station $Station
    return
}
if (-not (Test-Path $path)) { throw "$path not found" }
$gui = @(Get-CimInstance Win32_Process -Filter "Name='mercury-ui.exe'" | Where-Object { $_.ExecutablePath -eq (Join-Path $d 'mercury-ui.exe') })
if ($gui) { throw "station $Station's Mercury GUI is running (pid $(($gui | ForEach-Object ProcessId) -join ',')): close it first" }
foreach ($p in $engines) { Stop-Process -Id $p.ProcessId -Force }
$action = New-ScheduledTaskAction -Execute $path -Argument '-C mercury.ini' -WorkingDirectory $d
$principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName "hfbench_mercury${Station}_engine" -Action $action -Principal $principal -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName "hfbench_mercury${Station}_engine"
$t0 = Get-Date
while (-not (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)) {
    if (((Get-Date) - $t0).TotalSeconds -gt 60) { throw "station $Station engine not listening on $port after 60 s" }
    Start-Sleep 2
}
$h = (Get-FileHash $path -Algorithm SHA256).Hash.ToLower()
$line = "{0} UTC station {1}: started engine {2} (sha256 {3})" -f (Get-Date).ToUniversalTime().ToString('yyyy-MM-dd HH:mm:ss'), $Station, $Exe, $h
Add-Content -Path $log -Value $line
$line
