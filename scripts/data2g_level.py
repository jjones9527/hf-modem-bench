#!/usr/bin/env python3
"""Data2G received burst level vs the tone reference (used to set output_volume, D5).
usage: data2g_level.py listen.json st1_host.log st2_host.log [levels.json]
The host logs are hfbench_start_data2g.ps1's (bench local time, EST = UTC-5). Each sent
burst is a 'TX b<n> <kind> <mode> x<frames> <seconds>s' line, logged as it is queued;
the burst's audio follows within the PTT on-delay and the transmit lead (100 + 100 ms),
so the window skips 0.35 s at the start and 0.1 s at the end. REF holds the tone levels
(dBFS at WGN 40, path sender->receiver) from levels.json when given (`hfbench audio
check --json`), else the 16-17 Nov tone check."""
import json, math, re, sys, statistics as st
from datetime import datetime, timedelta, timezone

EST = timezone(timedelta(hours=-5))
REF = {2: -22.8, 1: -23.4}
TX = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d),(\d{3}) INFO TX b\d+ (\w+) (\S+) x\d+ ([\d.]+)s")


def bursts(path):
    out = []
    for l in open(path, encoding="utf-8", errors="replace"):
        m = TX.match(l)
        if m:
            t = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S").replace(tzinfo=EST).timestamp() + int(m.group(2)) / 1000
            out.append((t, t + float(m.group(5)) + 0.2, m.group(3), m.group(4)))
    return out


def tone_ref(path):
    """The WGN 40 tone level on each sender->receiver path from an audio check's json."""
    ref = {}
    for run in json.load(open(path)):
        if run.get("ionos_setting") != "WGN:40":
            continue
        for name, p in run.get("paths", {}).items():
            src, dst = (int(x) for x in name.split("->"))
            if src != dst and not p.get("clipped"):
                ref[src] = float(p["tone_dbfs"])
    return ref


if __name__ == "__main__":
    d = json.load(open(sys.argv[1]))
    if len(sys.argv) > 4:
        got = tone_ref(sys.argv[4])
        if len(got) == 2:
            REF = got
        else:
            print(f"levels file not understood ({got}); using the built-in reference {REF}")
    series = {int(k): v for k, v in d["series"].items()}
    tx = {1: bursts(sys.argv[2]), 2: bursts(sys.argv[3])}
    allb = sorted((a, b) for v in tx.values() for a, b, _, _ in v)

    def busy(t):
        return any(a - 0.3 <= t <= b + 0.5 for a, b in allb)

    for sender in (2, 1):
        mic = 3 - sender
        pts = series[mic]
        t0, t1 = pts[0][0], pts[-1][0]
        noise = st.median(p for t, p in pts if not busy(t))
        rows = []
        for a, b, kind, mode in tx[sender]:
            if a < t0 or b > t1:
                continue
            v = [p for t, p in pts if a + 0.35 <= t <= b - 0.1]
            if len(v) < 5 or st.mean(v) <= noise:
                continue
            rows.append((10 * math.log10(st.mean(v) - noise), b - a, f"{kind} {mode}"))
        if not rows:
            print(f"station {sender} -> {mic}: no bursts in the recording")
            continue
        lv = sorted(r[0] for r in rows)
        med = lv[len(lv) // 2]
        print(f"station {sender} -> {mic}: {len(rows)} bursts, received level median {med:.1f} dBFS "
              f"(middle half {lv[len(lv)//4]:.1f} .. {lv[3*len(lv)//4]:.1f}), noise {10*math.log10(noise):.1f} dBFS, "
              f"tone reference {REF[sender]:.1f} -> Data2G is {med - REF[sender]:+.1f} dB vs reference")
        by = {}
        for lvl, dur, mode in rows:
            by.setdefault(mode, []).append((lvl, dur))
        for mode, v in sorted(by.items()):
            print(f"    {mode:<26} n={len(v):>3}  level median {st.median(x for x, _ in v):6.1f} dBFS  "
                  f"burst length median {st.median(y for _, y in v):.1f} s")
