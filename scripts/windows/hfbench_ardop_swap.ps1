param([Parameter(Mandatory)][ValidateSet('dev', 'release')][string]$Build)
# Put an ARDOP_Win.exe build into both Winlink installs (C:\RMS Express, C:\RMS Express 2).
#   dev:     hfbench\ardop-dev\bin\ARDOP_Win.exe (Phil's 1.0.3.3 development build, built on the
#            bench; not published). The installed 1.0.2.9 is first kept as ARDOP_Win.exe.1.0.2.9
#            (once: an existing backup is never overwritten).
#   release: copy ARDOP_Win.exe.1.0.2.9 back.
# Refuses while any ARDOP_Win.exe runs (Winlink starts it with an ARDOP session). Prints each
# install's file version and sha256 after the copy, and appends them to hfbench\ardop-swap.log.
$ErrorActionPreference = "Stop"
$dev = Join-Path $env:USERPROFILE 'hfbench\ardop-dev\bin\ARDOP_Win.exe'
$log = Join-Path $env:USERPROFILE 'hfbench\ardop-swap.log'
if (Get-Process ARDOP_Win -ErrorAction SilentlyContinue) { throw "ARDOP_Win.exe is running: close the ARDOP sessions first" }
foreach ($inst in 'C:\RMS Express', 'C:\RMS Express 2') {
    $exe = Join-Path $inst 'ARDOP_Win.exe'
    $bak = Join-Path $inst 'ARDOP_Win.exe.1.0.2.9'
    if ($Build -eq 'dev') {
        if (-not (Test-Path $bak)) {
            $v = (Get-Item $exe).VersionInfo.FileVersion
            if ($v -notlike '1.0.2.9*') { throw "$exe is $v, not 1.0.2.9: not backing it up" }
            Copy-Item $exe $bak
        }
        Copy-Item $dev $exe -Force
    } else {
        if (-not (Test-Path $bak)) { throw "no backup $bak" }
        Copy-Item $bak $exe -Force
    }
    $line = "{0:u} {1} {2}: {3} sha256 {4}" -f (Get-Date).ToUniversalTime(), $Build, $exe,
        (Get-Item $exe).VersionInfo.FileVersion, (Get-FileHash $exe -Algorithm SHA256).Hash.ToLower()
    $line
    Add-Content $log $line
}
