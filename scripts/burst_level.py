#!/usr/bin/env python3
"""Any modem's received burst level against the tone reference (D5), keyed by the
transmit log (tx_crest_log.py: every burst each station sent, start and end, taken
digitally before the IONOS). Used to set a modem's drive level at bring-up.
usage: burst_level.py listen.json txcrest.jsonl [levels.json] [--from UTC --to UTC]
For each sending station: its bursts inside the recording, received on the OTHER
station's microphone (blocks 0.2 s inside each burst), noise = median of blocks outside
every burst of either station, level = 10 log(mean - noise). Long bursts (>= 2 s, data)
and short ones (replies) are reported apart. REF: the tone levels at WGN 40 from
levels.json (`hfbench audio check --json`), sender -> receiver."""
import json, math, statistics as st, sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from data2g_level import tone_ref

args = sys.argv[1:]
lo = hi = None
if "--from" in args:
    i = args.index("--from"); lo = datetime.fromisoformat(args[i + 1]).timestamp(); del args[i:i + 2]
if "--to" in args:
    i = args.index("--to"); hi = datetime.fromisoformat(args[i + 1]).timestamp(); del args[i:i + 2]
listen, txlog = args[0], args[1]
ref = tone_ref(args[2]) if len(args) > 2 else {2: -22.8, 1: -23.4}
series = {int(k): v for k, v in json.load(open(listen))["series"].items()}
bursts = [json.loads(l) for l in open(txlog) if l.strip()]
t0 = max(min(p[0][0] for p in series.values()), lo or 0)
t1 = min(max(p[-1][0] for p in series.values()), hi or 9e12)
bursts = [b for b in bursts if t0 <= b["t0"] and b["t1"] <= t1]
spans = sorted((b["t0"], b["t1"]) for b in bursts)


def busy(t):
    return any(a - 0.3 <= t <= b + 0.5 for a, b in spans)


for sender in (2, 1):
    mic = 3 - sender
    pts = [(t, p) for t, p in series[mic] if t0 <= t <= t1]
    quiet = [p for t, p in pts if not busy(t)]
    if len(quiet) < 20:
        print(f"station {sender} -> {mic}: too little quiet time for a noise estimate"); continue
    noise = st.median(quiet)
    groups = {"data (>= 2 s)": [], "replies (< 2 s)": []}
    digital = {"data (>= 2 s)": [], "replies (< 2 s)": []}
    for b in bursts:
        if b["st"] != sender:
            continue
        v = [p for t, p in pts if b["t0"] + 0.2 <= t <= b["t1"] - 0.2]
        if len(v) < 5 or st.mean(v) <= noise:
            continue
        k = "data (>= 2 s)" if b["s"] >= 2 else "replies (< 2 s)"
        groups[k].append(10 * math.log10(st.mean(v) - noise))
        digital[k].append(b["mean_dbfs"])
    for k, lv in groups.items():
        if not lv:
            continue
        m = st.median(lv)
        print(f"station {sender} -> {mic} {k:<16} n={len(lv):>3}  received {m:6.1f} dBFS "
              f"(middle half {sorted(lv)[len(lv)//4]:.1f}..{sorted(lv)[3*len(lv)//4]:.1f}), digital mean "
              f"{st.median(digital[k]):6.1f} dBFS; tone reference {ref[sender]:.1f} -> {m - ref[sender]:+.1f} dB vs reference")
