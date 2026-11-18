param([Parameter(Mandatory)][int]$Level)
# Set VARA HF's ALC Drive Level (dB) in both installs (C:\VARA, C:\VARA 2) and restart both:
# VARA is stopped while VARA.ini is edited (backups VARA.ini.before-drive kept), then started
# again with hfbench_start_vara.ps1. Bench level: -3 (D5 exception, 18 Nov 2026); lower for
# the cliff search. Winlink must reconnect afterwards (hfbench recover).
foreach ($d in 'C:\VARA','C:\VARA 2') {
  Get-CimInstance Win32_Process -Filter "Name='VARA.exe'" | Where-Object { $_.ExecutablePath -eq "$d\VARA.exe" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
}
Start-Sleep 3
foreach ($d in 'C:\VARA','C:\VARA 2') {
  $f = "$d\VARA.ini"; if (-not (Test-Path "$f.before-drive")) { Copy-Item $f "$f.before-drive" }
  $t = Get-Content $f; $t = $t -replace '^ALC Drive Level=.*$', "ALC Drive Level=$Level"; Set-Content $f $t -Encoding Ascii
  "$d : " + (Select-String -Path $f -Pattern '^ALC Drive Level=').Line
}
foreach ($n in 1, 2) { & "$env:USERPROFILE\hfbench_start_vara.ps1" -Station $n }
