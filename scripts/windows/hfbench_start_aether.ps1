param([Parameter(Mandatory)][ValidateSet(1,2)][int]$Station, [switch]$Stop, [double]$Level = -1,
      [string]$Extra = '')
# Start one station's Aether HF daemon (aetherd 0.2.0-beta.x, its own install per station:
# %LOCALAPPDATA%\Aether HF and %LOCALAPPDATA%\Aether HF 2) headless in the desktop session (it
# needs the sound card). Writes the station's config, hfbench\aether\station<N>\station.toml (own folder: aetherd keeps profiles beside it):
#   station 1 VA3ZTF, C-Media (PID 0008), host (VARA-compatible) port 8300, control 8515
#   station 2 VE3XZQ, "3- USB Audio Device" (PID 0014), host port 8310, control 8525
# Bench settings: PTT none (VOX, as every modem here), wait_for_clear off (busy detection off,
# test plan), no CW ID, compression only if offered (Aether's default: off), regulatory profile
# "none" (Canadian calls, bench simulator, no radio), record.send_to_project OFF (Aether's
# default uploads session audio, logs and settings to its project; nothing leaves this bench).
# -Level is Aether's tx_level (the amplitude of a sine with the data's RMS; the tone check's
# reference is 0.5), saved to hfbench\aether\level.txt and reused when -Level is left out.
#   hfbench_start_aether.ps1 -Station 1 -Level 0.25
#   hfbench_start_aether.ps1 -Station 2 -Stop
$ErrorActionPreference = "Stop"
$d = Join-Path $env:LOCALAPPDATA ($(if ($Station -eq 1) { 'Aether HF' } else { 'Aether HF 2' }))
$exe = Join-Path $d 'aetherd.exe'
$port = if ($Station -eq 1) { 8300 } else { 8310 }
$ctl = if ($Station -eq 1) { 8515 } else { 8525 }
$call = if ($Station -eq 1) { 'VA3ZTF' } else { 'VE3XZQ' }
$dev = if ($Station -eq 1) { 'C-Media USB Audio Device   )' } else { '3- USB Audio Device)' }
$dir = Join-Path $env:USERPROFILE 'hfbench\aether'
New-Item -ItemType Directory -Force -Path $dir | Out-Null
# each station's config in its own folder: aetherd keeps profiles/ beside it
$sdir = Join-Path $dir "station$Station"
New-Item -ItemType Directory -Force -Path $sdir | Out-Null
$conf = Join-Path $sdir 'station.toml'
$log = Join-Path $dir "station${Station}_aetherd.log"
$restarts = Join-Path $dir 'restarts.log'
$task = "hfbench_aether$Station"
$levelFile = Join-Path $dir 'level.txt'
if ($Level -lt 0) { $Level = if (Test-Path $levelFile) { [double](Get-Content $levelFile -TotalCount 1) } else { 0.25 } }
else { Set-Content -Encoding ASCII $levelFile $Level }

$mine = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'aetherd.exe' -and $_.ExecutablePath -and (Split-Path $_.ExecutablePath) -eq $d })
foreach ($p in $mine) { Stop-Process -Id $p.ProcessId -Force }
if ($mine) { Start-Sleep 2 }
$stamp = (Get-Date).ToUniversalTime().ToString('yyyy-MM-dd HH:mm:ss')
if ($Stop) {
    $line = "$stamp UTC station ${Station}: stopped $(($mine | ForEach-Object { "aetherd $($_.ProcessId)" }) -join ', ')"
    Add-Content $restarts $line; $line; return
}

@"
# hfbench station $Station (written by hfbench_start_aether.ps1; see its header)
schema_version = 13
callsign = "$call"

[audio]
input = "Microphone ($dev"
output = "Speakers ($dev"
sample_rate = 48000
tx_level = $Level

[ptt]
kind = "none"

[radio]
wait_for_clear = false
# busy detection off (test plan): wait_for_clear only stops Aether waiting; its detector still
# reports BUSY ON to Winlink, which then holds its call (crest-aether-0001, 20 Nov: BUSY ON for
# 71 s after the IONOS setting changed, no CONNECT sent). A threshold no noise change reaches.
busy_threshold_db = 60.0
bandwidth = 2300
answer_only = false
turnaround_ms = 0
answer_gap_ms = 0
compress = false
cw_id = false

[control]
enabled = true
bind = "127.0.0.1:$ctl"

[host]
enabled = true
bind = "127.0.0.1:$port"
trace = true

[kiss]
enabled = false

[log]
format = "text"
file = '$log'

[record]
auto = false
send_to_project = false

[regulatory]
profile = "none"
"@ | Set-Content -Encoding ASCII $conf

$cmd = Join-Path $dir "station$Station.cmd"
@"
@echo off
cd /d "$d"
echo ===== %DATE% %TIME% start tx_level $Level $Extra >> "$dir\station${Station}_console.log"
"$exe" --config "$conf" $Extra >> "$dir\station${Station}_console.log" 2>&1
"@ | Set-Content -Encoding ASCII $cmd
if (-not (Get-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue)) {
    $action = New-ScheduledTaskAction -Execute $cmd -WorkingDirectory $d
    $principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive
    $settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    Register-ScheduledTask -TaskName $task -Action $action -Principal $principal -Settings $settings -Force | Out-Null
}
$t1 = Get-Date
while ((Get-ScheduledTask -TaskName $task).State -eq 'Running' -and ((Get-Date) - $t1).TotalSeconds -lt 15) { Start-Sleep 1 }
Start-ScheduledTask -TaskName $task
$t0 = Get-Date
while (-not (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)) {
    if (((Get-Date) - $t0).TotalSeconds -gt 60) { throw "station $Station Aether not listening on $port after 60 s (see $dir\station${Station}_console.log)" }
    Start-Sleep 2
}
$h = (Get-FileHash $exe -Algorithm SHA256).Hash.ToLower()
$line = "$stamp UTC station ${Station}: started aetherd tx_level $Level $Extra (sha256 $h)"
Add-Content $restarts $line
$line
