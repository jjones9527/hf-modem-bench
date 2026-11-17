param([Parameter(Mandatory)][ValidateSet(1,2)][int]$Station, [switch]$Stop, [switch]$Gui, [string]$Extra = '')
# Start one station's Data2G (0.5.x) in the desktop session (it needs the sound card).
# Each station has its own settings file, hfbench\data2g\station<N>.conf: Data2G's default
# (%LOCALAPPDATA%\Data2G\data2g.conf) is shared by every copy on the machine, so both
# stations always start with --config. Default: the headless data2g-host, logging to
# hfbench\data2g\station<N>_host.log (Data2G logs only to stderr, local time). -Gui starts
# data2g-gui on the same settings instead (no log file; watch the waterfall). Only one of
# the two may run per station: they share the ports and the sound card.
#   hfbench_start_data2g.ps1 -Station 1
#   hfbench_start_data2g.ps1 -Station 2 -Extra "--log-level DEBUG"   # flags for this run only
#   hfbench_start_data2g.ps1 -Station 2 -Stop
$ErrorActionPreference = "Stop"
$d = if ($Station -eq 1) { 'C:\Program Files\Data2G' } else { 'C:\Program Files\Data2G 2' }
$port = if ($Station -eq 1) { 8300 } else { 8310 }
$dir = Join-Path $env:USERPROFILE 'hfbench\data2g'
$conf = Join-Path $dir "station$Station.conf"
$log = Join-Path $dir "station${Station}_host.log"
$restarts = Join-Path $env:USERPROFILE 'hfbench\data2g\restarts.log'
$task = "hfbench_data2g$Station"
if (-not (Test-Path $conf)) { throw "$conf not found" }

$mine = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'data2g-*.exe' -and $_.ExecutablePath -and (Split-Path $_.ExecutablePath) -eq $d })
foreach ($p in $mine) { Stop-Process -Id $p.ProcessId -Force }
if ($mine) { Start-Sleep 2 }
$stamp = (Get-Date).ToUniversalTime().ToString('yyyy-MM-dd HH:mm:ss')
if ($Stop) {
    $line = "$stamp UTC station ${Station}: stopped $(($mine | ForEach-Object { "$($_.Name) $($_.ProcessId)" }) -join ', ')"
    Add-Content $restarts $line; $line; return
}

$exe = if ($Gui) { 'data2g-gui.exe' } else { 'data2g-host.exe' }
$cmd = Join-Path $dir "station$Station.cmd"
$run = "`"$d\$exe`" --config `"$conf`" $Extra"
if (-not $Gui) { $run += " 2>> `"$log`"" }
@"
@echo off
cd /d "$d"
echo ===== %DATE% %TIME% start $exe $Extra >> "$log"
$run
"@ | Set-Content -Encoding ASCII $cmd
$action = New-ScheduledTaskAction -Execute $cmd -WorkingDirectory $d
$principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $task -Action $action -Principal $principal -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName $task
$t0 = Get-Date
while (-not (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)) {
    if (((Get-Date) - $t0).TotalSeconds -gt 60) { throw "station $Station Data2G not listening on $port after 60 s (see $log)" }
    Start-Sleep 2
}
$h = (Get-FileHash "$d\$exe" -Algorithm SHA256).Hash.ToLower()
$line = "$stamp UTC station ${Station}: started $exe --config station$Station.conf $Extra (sha256 $h)"
Add-Content $restarts $line
$line
