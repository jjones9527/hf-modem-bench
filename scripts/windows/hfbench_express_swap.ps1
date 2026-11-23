param([Parameter(Mandatory)][ValidateSet('apply', 'revert')][string]$Action, [string]$Source = '', [string]$Label = '',
      [string]$Backup = '')
# Put a set of Winlink Express files (an Express build's exe and DLLs, an ARDOP_Win.exe) into both
# installs (C:\RMS Express, C:\RMS Express 2), or put the originals back.
#   apply:  -Source <folder> -Label <name>. Every file in the folder (and its subfolders, flattened)
#           replaces the install's file of the same name. Each install's originals are first copied
#           to <install>\backup-<installed RMS Express.exe version>\ (once: an existing backup is
#           never overwritten), with a list of what the label replaced.
#   revert: copies every exe and DLL in the newest backup folder back, or in -Backup <folder name>.
#           Settings are not touched: a newer Express may migrate RMS Express.ini on first start
#           (keeping RMS Express.ini.before-radio-profiles.bak), so going back to the older release
#           also needs that .bak copied over RMS Express.ini (keep a copy of the current one).
# Refuses while Winlink Express or ARDOP_Win.exe runs. Logs every file's version and sha256 to
# hfbench\express-swap.log.
#   hfbench_express_swap.ps1 apply -Source %USERPROFILE%\hfbench\some-build -Label some-build
#   hfbench_express_swap.ps1 revert [-Backup backup-1.8.6.0]
$ErrorActionPreference = "Stop"
$log = Join-Path $env:USERPROFILE 'hfbench\express-swap.log'
if (Get-Process 'RMS Express', 'ARDOP_Win' -ErrorAction SilentlyContinue) { throw "Winlink Express or ARDOP_Win.exe is running: close them first" }
$stamp = (Get-Date).ToUniversalTime().ToString('yyyy-MM-dd HH:mm:ss')
foreach ($inst in 'C:\RMS Express', 'C:\RMS Express 2') {
    $ver = (Get-Item (Join-Path $inst 'RMS Express.exe')).VersionInfo.FileVersion
    if ($Action -eq 'apply') {
        if (-not $Source -or -not (Test-Path $Source)) { throw "no -Source folder" }
        $files = Get-ChildItem $Source -Recurse -File
        $bak = Join-Path $inst "backup-$ver"
        if (-not (Test-Path $bak)) {
            New-Item -ItemType Directory $bak | Out-Null
            foreach ($f in $files) {
                $cur = Join-Path $inst $f.Name
                if (Test-Path $cur) { Copy-Item $cur $bak }
            }
            ($files | ForEach-Object Name) | Set-Content (Join-Path $bak "replaced-by-$Label.txt")
        }
        foreach ($f in $files) { Copy-Item $f.FullName (Join-Path $inst $f.Name) -Force }
        $names = $files | ForEach-Object Name
    } else {
        # -Backup <name> picks a folder (e.g. backup-1.8.6.0, the original release after a second
        # apply); otherwise the newest, which only undoes the last apply
        $bak = if ($Backup) { Get-Item (Join-Path $inst $Backup) -ErrorAction SilentlyContinue }
               else { Get-ChildItem $inst -Directory -Filter 'backup-*' | Sort-Object LastWriteTime | Select-Object -Last 1 }
        if (-not $bak) { throw "no backup folder $Backup in $inst" }
        $files = Get-ChildItem $bak.FullName -File | Where-Object { $_.Extension -in '.exe', '.dll' }
        foreach ($f in $files) { Copy-Item $f.FullName (Join-Path $inst $f.Name) -Force }
        $names = $files | ForEach-Object Name
    }
    foreach ($n in $names) {
        $p = Join-Path $inst $n
        $line = "{0} {1} {2} {3}: {4} sha256 {5}" -f $stamp, $Action, $Label, $p, (Get-Item $p).VersionInfo.FileVersion,
            (Get-FileHash $p -Algorithm SHA256).Hash.ToLower()
        $line
        Add-Content $log $line
    }
}
