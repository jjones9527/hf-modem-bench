#!/usr/bin/env python3
"""Per-run data S:N for a one-way Mercury campaign, keyed by the SENDER's own PTT log.
usage: mercury_snr.py campaign_dir sender_engine.log listen1.json [listen2.json ...]
Noise: median mic-1 block power outside every burst (energy-detected, either station)
and outside the sender's PTT, with a 0.3 s guard, within the run's window."""
import csv, json, math, re, statistics as st, sys
from datetime import datetime, timedelta, timezone
sys.path.insert(0, "src")
from hfbench import audio

EST = timezone(timedelta(hours=-5))
camp, englog, *listens = sys.argv[1:]

ptt, on = [], None
for l in open(englog, encoding="utf-8", errors="replace"):
    m = re.match(r"(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+)", l)
    if not m:
        continue
    if "PTT ON" in l or "PTT OFF" in l:
        t = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=EST).timestamp()
        if "PTT ON" in l:
            on = t
        elif on:
            ptt.append((on, t)); on = None

mic1 = []
for f in listens:
    mic1 += json.load(open(f))["series"]["1"]
mic1.sort()

rows = [r for r in csv.DictReader(open(f"{camp}/manifest.csv"))
        if r.get("final_attempt") == "yes" and r.get("outcome") not in ("invalid", "") and r.get("end_utc")]
out = []
for r in rows:
    a = datetime.fromisoformat(r["start_utc"]).timestamp(); b = datetime.fromisoformat(r["end_utc"]).timestamp()
    pts = [(t, p) for t, p in mic1 if a <= t <= b]
    if len(pts) < 100:
        print(r["run_id"], "not recorded"); continue
    tx = [(x, y) for x, y in ptt if a <= x and y <= b]
    busy = sorted(tx + audio.bursts_from_energy(pts))
    def isbusy(t):
        return any(x - 0.3 <= t <= y + 0.3 for x, y in busy)
    noise = st.median(p for t, p in pts if not isbusy(t))
    snr = []
    for x, y in tx:
        v = [p for t, p in pts if x + 0.15 <= t <= y - 0.08]
        if len(v) >= 5 and st.mean(v) > noise:
            snr.append(10 * math.log10((st.mean(v) - noise) / noise))
    snr.sort()
    med = snr[len(snr) // 2] if snr else float("nan")
    print(f"{r['run_id']:<24} WGN {r['snr_db']:>3}  data S:N {med:5.1f} dB  (n={len(snr)}, middle half "
          f"{snr[len(snr)//4]:.1f}..{snr[3*len(snr)//4]:.1f})  noise {10*math.log10(noise):.1f} dBFS")
    out.append({"run_id": r["run_id"], "setting_db": r["snr_db"], "data_snr_db": round(med, 2), "data_n": len(snr),
                "control_snr_db": "", "keyed_by": "Mercury PTT (sender)", "ardop_ptt_data": ""})
if len(sys.argv) and out:
    with open(f"{camp}/snr.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
    print(f"wrote {camp}/snr.csv")
