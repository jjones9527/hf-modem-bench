# Swap the sound devices between the two ARDOP_Win instances (station 1 <-> station 2).
# Run only while ARDOP_Win is closed: it rewrites its .ini on exit.
# Backs up each .ini as "ARDOP_Win TNC.ini.<stamp>.bak" before changing it.
$ErrorActionPreference = "Stop"
if (Get-Process ARDOP_Win -ErrorAction SilentlyContinue) { throw "ARDOP_Win is running; close both Peer-to-Peer session windows first" }
$files = 'C:\RMS Express\ARDOP_Win TNC.ini', 'C:\RMS Express 2\ARDOP_Win TNC.ini'
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMdd-HHmm')
$text = $files | ForEach-Object { [IO.File]::ReadAllText($_) }
function Get-Line($t, $key) { if ($t -match "(?m)^$key=(.*?)\r?$") { $Matches[1] } else { throw "no $key in ini" } }
$dev = foreach ($t in $text) { @{ Capture = Get-Line $t 'CaptureDevice'; Playback = Get-Line $t 'PlaybackDevice' } }
for ($i = 0; $i -lt 2; $i++) {
    $o = $dev[1 - $i]
    Copy-Item $files[$i] "$($files[$i]).$stamp.bak"
    $t = $text[$i] -replace '(?m)^CaptureDevice=.*?(\r?)$', ("CaptureDevice=" + $o.Capture + '$1')
    $t = $t -replace '(?m)^PlaybackDevice=.*?(\r?)$', ("PlaybackDevice=" + $o.Playback + '$1')
    [IO.File]::WriteAllText($files[$i], $t, [Text.UTF8Encoding]::new($true))   # keep the BOM ARDOP writes
    "station $($i + 1): capture '$(Get-Line $t 'CaptureDevice')', playback '$(Get-Line $t 'PlaybackDevice')'"
}
