# Set Data2G's output_volume in both station configs (hfbench\data2g\station1.conf, station2.conf),
# keeping a dated copy of each. Data2G reads it at start, so restart it afterwards
# (hfbench_start_data2g.ps1 -Station N); bench_chain.sh's hang restart keeps it too.
# Edit $Volume here: passing "-5.0" as a parameter through powershell -File is read as a parameter name.
# 26 Nov 2026: -5.0 (at -1.0 and -3.0 the IONOS Lvl passed 1,200 mV p-p at MPG S:N 0).
$Volume = "-5.0"
$d = Join-Path $env:USERPROFILE 'hfbench\data2g'
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMdd-HHmm')
foreach ($n in 1, 2) {
  $f = Join-Path $d "station$n.conf"
  Copy-Item $f "$f.$stamp.bak"
  (Get-Content $f) -replace '^output_volume=.*', "output_volume=$Volume" | Set-Content -Encoding ASCII $f
  "$f : " + (Select-String -Path $f -Pattern '^output_volume=' | % Line)
}
