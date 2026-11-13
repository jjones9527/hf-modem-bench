# Set BusyDet=0 (busy detector off) in both ARDOP_Win TNC.ini files. ARDOP must be closed,
# because it rewrites its ini on exit. Keeps a .busydet5.bak copy and the file's encoding (BOM).
foreach ($inst in 'C:\RMS Express', 'C:\RMS Express 2') {
  $f = Join-Path $inst 'ARDOP_Win TNC.ini'
  $bytes = [IO.File]::ReadAllBytes($f)
  $bom = $bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF
  Copy-Item $f "$f.busydet5.bak" -Force
  $text = [IO.File]::ReadAllText($f)
  $new = $text -replace '(?m)^BusyDet=\d+', 'BusyDet=0'
  [IO.File]::WriteAllText($f, $new, (New-Object Text.UTF8Encoding($bom)))
  "$f : BOM=$bom : " + ((Select-String -Path $f -Pattern '^BusyDet=').Line)
}
