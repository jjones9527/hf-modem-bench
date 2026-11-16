# prints seconds since each Mercury engine log was last written, and whether a session is connected
foreach ($d in 'C:\Program Files\MercuryHF','C:\Program Files\MercuryHF 2') {
  $f = Get-Item "$d\logs\mercury_engine.log"; [int]((Get-Date) - $f.LastWriteTime).TotalSeconds }
$c = Get-ChildItem "$env:USERPROFILE\hfbench\runs\*\console-*.txt" | Sort-Object LastWriteTime | Select-Object -Last 1
$last = Get-Content $c.FullName | Where-Object { $_ -match '^===|Session detected| -> |Recovery' } | Select-Object -Last 1
if ($last -match 'Session detected') { 'INSESSION' } else { 'IDLE' }
