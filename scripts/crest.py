#!/usr/bin/env python3
"""Crest factor (peak over average) of a modem's bursts as received, from peak_log.py's json,
keyed by Data2G's TX lines. Peak: the burst's highest block peak; average: its mean 3 kHz band
power (both dBFS, same microphone). A sine's crest is 3.0 dB; the tone check's tone gives the
mV p-p scale: TONE_PP mV p-p at the meter for the tone's peak dBFS at that microphone.
usage: crest.py peaks.json st1_host.log st2_host.log"""
import json, math, statistics as st, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from data2g_level import bursts

TONE_PEAK = {1: -19.8, 2: -22.3}   # tone peak dBFS at mic 1 (2->1) and mic 2 (1->2), WGN 40, 17 Nov tone check
TONE_PP = 400.0                    # mV p-p on the IONOS Lvl meter at the reference (bench-setup)
d = json.load(open(sys.argv[1]))
rows = {int(k): v for k, v in d["rows"].items()}
for sender, log in ((2, sys.argv[3]), (1, sys.argv[2])):
    mic = 3 - sender
    pts = rows[mic]
    by = {}
    for a, b, kind, mode in bursts(log):
        if a < pts[0][0] or b > pts[-1][0]:
            continue
        v = [(p, bp) for t, p, bp in pts if a + 0.35 <= t <= b - 0.1]
        if len(v) < 5:
            continue
        pk = max(p for p, _ in v); avg = 10 * math.log10(st.mean(bp for _, bp in v))
        by.setdefault(f"{kind} {mode}", []).append((pk, avg))
    for m, v in sorted(by.items()):
        pk = max(x for x, _ in v); cr = st.median(x - y for x, y in v)
        print(f"station {sender} -> {mic}  {m:<26} n={len(v):>3}  avg {st.median(y for _, y in v):6.1f} dBFS  "
              f"peak max {pk:6.1f} dBFS (~{TONE_PP * 10 ** ((pk - TONE_PEAK[mic]) / 20):4.0f} mV p-p)  crest {cr:4.1f} dB "
              f"({cr - 3.0:+.1f} vs a sine)")
