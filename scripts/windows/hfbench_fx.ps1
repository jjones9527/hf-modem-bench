foreach ($kind in 'Render','Capture') {
  Get-ChildItem "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\$kind" | ForEach-Object {
    if ((Get-ItemProperty $_.PSPath).DeviceState -ne 1) { return }
    $p = Get-ItemProperty "$($_.PSPath)\Properties" -ErrorAction SilentlyContinue
    $iface = $p.'{b3f8fa53-0004-438e-9003-51a46e139bfc},6'
    if ($iface -notmatch 'USB') { return }
    "== $kind  $($p.'{a45c254e-df1c-4efd-8020-67d146a850e0},2') ($iface)  id $($_.PSChildName)"
    $fx = Get-ItemProperty "$($_.PSPath)\FxProperties" -ErrorAction SilentlyContinue
    if (-not $fx) { "   (no FxProperties key: no enhancement processing installed)"; return }
    $fx.PSObject.Properties | Where-Object { $_.Name -like '{*' } | ForEach-Object {
      $v = $_.Value; if ($v -is [byte[]]) { $v = ($v[0..([Math]::Min(15,$v.Length-1))] | ForEach-Object { $_.ToString('x2') }) -join ' ' }
      "   $($_.Name) = $v" }
  }
}
