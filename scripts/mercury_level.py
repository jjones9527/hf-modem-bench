#!/usr/bin/env python3
"""Mercury received burst level vs the tone reference (used to set tx_gain_db, D5).
usage: mercury_level.py listen.json st1_engine.log st2_engine.log  (Mercury logs in bench local time, EST = UTC-5)
REF holds the tone levels (dBFS, WGN 40) from the latest tone check; update it from levels.json."""
import json, math, re, sys, statistics as st
from datetime import datetime, timedelta, timezone

REF = {2: -22.84, 1: -23.39}   # tone dBFS at WGN 40, path sender->receiver (2->1, 1->2), knee pre-check
EST = timezone(timedelta(hours=-5))

def ptt(path):
    out, on, mode = [], None, ""
    for l in open(path, encoding="utf-8", errors="replace"):
        m = re.match(r"(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+)", l)
        if not m:
            continue
        t = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=EST).timestamp()
        mm = re.search(r"mode[= ]+(\w+)", l)
        if mm:
            mode = mm.group(1)
        if "PTT ON" in l:
            on = t
        elif "PTT OFF" in l and on:
            out.append((on, t, mode)); on = None
    return out

d = json.load(open(sys.argv[1]))
series = {int(k): v for k, v in d["series"].items()}
tx = {1: ptt(sys.argv[2]), 2: ptt(sys.argv[3])}
allb = sorted((a, b) for v in tx.values() for a, b, _ in v)

def busy(t):
    return any(a - 0.3 <= t <= b + 0.3 for a, b in allb)

for sender in (2, 1):
    mic = 3 - sender
    pts = series[mic]
    t0, t1 = pts[0][0], pts[-1][0]
    noise = st.median(p for t, p in pts if not busy(t))
    rows = []
    for a, b, mode in tx[sender]:
        if a < t0 or b > t1:
            continue
        v = [p for t, p in pts if a + 0.15 <= t <= b - 0.08]
        if len(v) < 5:
            continue
        sig = st.mean(v) - noise
        if sig <= 0:
            continue
        rows.append((10 * math.log10(sig), b - a, mode))
    if not rows:
        print(f"station {sender} -> {mic}: no bursts in the recording"); continue
    lv = sorted(r[0] for r in rows)
    med = lv[len(lv) // 2]
    print(f"station {sender} -> {mic}: {len(rows)} bursts, received level median {med:.1f} dBFS "
          f"(middle half {lv[len(lv)//4]:.1f} .. {lv[3*len(lv)//4]:.1f}), noise {10*math.log10(noise):.1f} dBFS, "
          f"tone reference {REF[sender]:.1f} -> Mercury is {med - REF[sender]:+.1f} dB vs reference")
    by = {}
    for lvl, dur, mode in rows:
        by.setdefault(mode or "?", []).append((lvl, dur))
    for mode, v in sorted(by.items()):
        print(f"    mode {mode:<12} n={len(v):>3}  level median {st.median(x for x, _ in v):6.1f} dBFS  "
              f"burst length median {st.median(y for _, y in v):.1f} s")
