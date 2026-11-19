param([Parameter(Mandatory)][ValidateSet(1,2)][int]$Station, [switch]$Stop, [double]$Drive = -1,
      [string]$LogLevel = 'info', [string]$Extra = '')
# Start one station's ProjectUltra TNC (ultra_tnc 0.6.x, C:\ProjectUltra) in the desktop session
# (it needs the sound card). Both stations run the same install, each with its own settings file,
# hfbench\ultra\station<N>.conf (written here: callsign VA3ZTF / VE3XZQ, sound card, port), and its own log,
# hfbench\ultra\station<N>_tnc.log. Station 1: C-Media (PID 0008), port 8300; station 2: the
# "3- USB Audio Device" (PID 0014), port 8310 (data port = command port + 1). -Drive is ULTRA's
# --tx-drive (target peak of each burst, 0.05..0.70): the level control (D5). -Drive is saved to
# hfbench\ultra\drive.txt; without -Drive the saved value is used (else ULTRA's default 0.50),
# so recovery's restarts (bench.py, profile ULTRA) keep the level.
#   hfbench_start_ultra.ps1 -Station 1 -Drive 0.35
#   hfbench_start_ultra.ps1 -Station 2 -LogLevel debug
#   hfbench_start_ultra.ps1 -Station 2 -Stop
$ErrorActionPreference = "Stop"
$d = 'C:\ProjectUltra'
$exe = Join-Path $d 'ultra_tnc.exe'
$port = if ($Station -eq 1) { 8300 } else { 8310 }
$dev = if ($Station -eq 1) { 'C-Media USB Audio Device   )' } else { '3- USB Audio Device)' }
# each station its own callsign: ULTRA rejects a CONNECT from its own callsign as a collision
# ("Simultaneous CONNECT with identical callsign", cal-ultra 19 Nov), so not VA3ZTF at both ends
$call = if ($Station -eq 1) { 'VA3ZTF' } else { 'VE3XZQ' }
$dir = Join-Path $env:USERPROFILE 'hfbench\ultra'
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$conf = Join-Path $dir "station$Station.conf"
$log = Join-Path $dir "station${Station}_tnc.log"
$restarts = Join-Path $dir 'restarts.log'
$task = "hfbench_ultra$Station"
$driveFile = Join-Path $dir 'drive.txt'
if ($Drive -lt 0) { $Drive = if (Test-Path $driveFile) { [double](Get-Content $driveFile -TotalCount 1) } else { 0.50 } }
else { Set-Content -Encoding ASCII $driveFile $Drive }

# this station's ultra_tnc is the one whose command line names its config file
$mine = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'ultra_tnc.exe' -and $_.CommandLine -match "station$Station\.conf" })
foreach ($p in $mine) { Stop-Process -Id $p.ProcessId -Force }
if ($mine) { Start-Sleep 2 }
$stamp = (Get-Date).ToUniversalTime().ToString('yyyy-MM-dd HH:mm:ss')
if ($Stop) {
    $line = "$stamp UTC station ${Station}: stopped $(($mine | ForEach-Object { "ultra_tnc $($_.ProcessId)" }) -join ', ')"
    Add-Content $restarts $line; $line; return
}

@"
# hfbench station $Station (written by hfbench_start_ultra.ps1)
callsign     = $call
audio_output = Speakers ($dev
audio_input  = Microphone ($dev
port         = $port
bind         = 127.0.0.1
"@ | Set-Content -Encoding ASCII $conf

$cmd = Join-Path $dir "station$Station.cmd"
$run = "`"$exe`" --config `"$conf`" --tx-drive $Drive --log-level $LogLevel --log-file `"$log`" $Extra"
@"
@echo off
cd /d "$d"
echo ===== %DATE% %TIME% start --tx-drive $Drive --log-level $LogLevel $Extra >> "$dir\station${Station}_console.log"
$run >> "$dir\station${Station}_console.log" 2>&1
"@ | Set-Content -Encoding ASCII $cmd
$action = New-ScheduledTaskAction -Execute $cmd -WorkingDirectory $d
$principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
# register once (needs the elevated SSH session); recovery runs this script from the desktop
# session, which may start the existing task but not re-register it ("Access is denied")
if (-not (Get-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue)) {
    Register-ScheduledTask -TaskName $task -Action $action -Principal $principal -Settings $settings -Force | Out-Null
}
$t1 = Get-Date   # the stopped TNC's task instance ends with it
while ((Get-ScheduledTask -TaskName $task).State -eq 'Running' -and ((Get-Date) - $t1).TotalSeconds -lt 15) { Start-Sleep 1 }
Start-ScheduledTask -TaskName $task
$t0 = Get-Date
while (-not (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)) {
    if (((Get-Date) - $t0).TotalSeconds -gt 60) { throw "station $Station ULTRA not listening on $port after 60 s (see $log)" }
    Start-Sleep 2
}
$h = (Get-FileHash $exe -Algorithm SHA256).Hash.ToLower()
$line = "$stamp UTC station ${Station}: started ultra_tnc --tx-drive $Drive --log-level $LogLevel $Extra (sha256 $h)"
Add-Content $restarts $line
$line
