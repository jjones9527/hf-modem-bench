# prints seconds since each Data2G host log was last written, and whether a session is connected
# (Data2G logs every burst and a stats line each minute of a connection, so a quiet log in a session is a hang)
foreach ($n in 1, 2) {
  $f = Get-Item "$env:USERPROFILE\hfbench\data2g\station${n}_host.log"; [int]((Get-Date) - $f.LastWriteTime).TotalSeconds }
$c = Get-ChildItem "$env:USERPROFILE\hfbench\runs\*\console-*.txt" | Sort-Object LastWriteTime | Select-Object -Last 1
$last = Get-Content $c.FullName | Where-Object { $_ -match '^===|Session detected| -> |Recovery' } | Select-Object -Last 1
if ($last -match 'Session detected') { 'INSESSION' } else { 'IDLE' }
