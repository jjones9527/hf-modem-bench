#!/usr/bin/env python3
"""Record both bench microphones and keep each ~21 ms block's peak (|x| max, dBFS) and
3 kHz band power, to find what drives the IONOS Lvl meter (D5: never red).
usage (bench, desktop session): python peak_log.py SECONDS OUT.json
Devices by name as in hfbench (station 1 C-Media, station 2 '3- USB Audio Device')."""
import json, math, queue, sys, time
import numpy as np
import sounddevice as sd
from hfbench.audio import band_power, pick_device, _extra

MICS = {1: "Microphone (C-Media USB Audio Device   )", 2: "Microphone (3- USB Audio Device)"}
secs, out = float(sys.argv[1]), sys.argv[2]
devs, apis = sd.query_devices(), sd.query_hostapis()
q, streams, fs_of = queue.Queue(), [], {}
for st, name in MICS.items():
    dev = pick_device(devs, apis, name, "in"); fs = float(sd.query_devices(dev)["default_samplerate"]); fs_of[st] = fs
    def cb(indata, frames, t, status, st=st):
        q.put((st, time.time(), indata[:, 0].copy()))
    streams.append(sd.InputStream(device=dev, channels=1, samplerate=fs, dtype="float32", blocksize=1024,
                                  callback=cb, extra_settings=_extra(sd, dev)))
rows = {1: [], 2: []}
for s in streams: s.start()
t_end = time.time() + secs
while time.time() < t_end:
    try: st, t, x = q.get(timeout=0.5)
    except queue.Empty: continue
    pk = float(np.max(np.abs(x))) if len(x) else 0.0
    rows[st].append((round(t, 3), round(20 * math.log10(max(pk, 1e-9)), 2), band_power(x, fs_of[st])))
for s in streams: s.stop(); s.close()
json.dump({"mics": MICS, "rows": rows}, open(out, "w"))
for st, r in rows.items():
    pk = sorted(p for _, p, _ in r)
    if pk: print(f"mic {st}: {len(pk)} blocks, peak max {pk[-1]:.1f} dBFS, 99.9% {pk[int(len(pk)*0.999)-1]:.1f}, 99% {pk[int(len(pk)*0.99)-1]:.1f}")
