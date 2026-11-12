foreach ($kind in 'Render','Capture') {
  $root = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\$kind"
  Get-ChildItem $root | ForEach-Object {
    $p = Get-ItemProperty "$($_.PSPath)\Properties" -ErrorAction SilentlyContinue
    $st = (Get-ItemProperty $_.PSPath).DeviceState
    if ($st -ne 1) { return }
    $name = $p.'{a45c254e-df1c-4efd-8020-67d146a850e0},2'
    $iface = $p.'{b3f8fa53-0004-438e-9003-51a46e139bfc},6'
    $fmt = $p.'{f19f064d-082c-4e27-bc73-6882a1bb8e4c},0'
    if ($fmt) { $ch = [BitConverter]::ToUInt16($fmt,10); $sr = [BitConverter]::ToUInt32($fmt,12); $bits = [BitConverter]::ToUInt16($fmt,22) } else { $ch=$sr=$bits='?' }
    "{0,-8} {1,-12} {2,-35} ch={3} rate={4} bits={5}" -f $kind, $name, $iface, $ch, $sr, $bits
  }
}
