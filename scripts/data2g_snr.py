#!/usr/bin/env python3
"""Per-run data S:N for a one-way Data2G campaign, keyed by the SENDER's own burst log.
usage: data2g_snr.py campaign_dir sender_host.log listen1.json [listen2.json ...]
Sender = station 2 (data 2 -> 1), heard on station 1's microphone. Bursts are the sender's
'TX b<n> data <mode> x<frames> <seconds>s' lines (data2g_level.bursts: queued time, audio
within 0.2 s); each burst's S:N uses its blocks from 0.35 s after the line to 0.1 s before
its end. Noise: median mic-1 block power in the quiet gap after the run (end + 10 s to
end + 100 s: the runner waits 120 s before the next run sets the IONOS, and nobody
transmits), so dense traffic inside the run doesn't matter. For comparison it also prints
the in-run estimate (blocks outside energy-detected bursts and the sender's bursts) where
at least 10 such blocks exist, and uses it for the campaign's last run, whose gap may hold
the next campaign's setting (with no idle blocks there, the campaign's other runs at the
same setting). Also
prints the run's data-mode mix (share of data air time per mode) and writes snr.csv."""
import csv, json, math, statistics as st, sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "src")
sys.path.insert(0, str(Path(__file__).parent))
from hfbench import audio
from data2g_level import bursts

camp, sendlog, *listens = sys.argv[1:]
allsend = bursts(sendlog)
tx = [b for b in allsend if b[2] == "data"]
mic1 = []
for f in listens:
    mic1 += json.load(open(f))["series"]["1"]
mic1.sort()
t_lo, t_hi = (mic1[0][0], mic1[-1][0]) if mic1 else (0, 0)

rows = [r for r in csv.DictReader(open(f"{camp}/manifest.csv"))
        if r.get("final_attempt") == "yes" and r.get("outcome") not in ("invalid", "") and r.get("end_utc")]
out, noise_by_setting = [], []
last_id = max(rows, key=lambda r: r["start_utc"])["run_id"] if rows else ""
for r in sorted(rows, key=lambda r: r["run_id"] == last_id):
    a = datetime.fromisoformat(r["start_utc"]).timestamp(); b = datetime.fromisoformat(r["end_utc"]).timestamp()
    mine = [x for x in tx if a <= x[0] and x[1] <= b]
    mix = Counter()
    for x0, x1, _, mode in mine:
        mix[mode] += x1 - x0
    tot = sum(mix.values()) or 1
    mixs = ", ".join(f"{m} {100 * s / tot:.0f}%" for m, s in mix.most_common(3))
    pts = [(t, p) for t, p in mic1 if a <= t <= b]
    if len(pts) < 100 or a < t_lo or b > t_hi:
        print(f"{r['run_id']:<24} WGN {r['snr_db']:>3}  not recorded  | modes: {mixs}")
        continue
    gap = [p for t, p in mic1 if b + 10 <= t <= b + 100]
    energy = audio.bursts_from_energy(pts)

    def inside(t, spans):
        return any(x - 0.3 <= t <= y + 0.5 for x, y in spans)

    sends = [(x0, x1) for x0, x1, _, _ in mine]
    idle = [p for t, p in pts if not inside(t, energy) and not inside(t, sends)]
    inrun = st.median(idle) if len(idle) >= 10 else None
    if r["run_id"] == last_id or len(gap) < 100:
        if inrun is None:
            same = [n for sd, n in noise_by_setting if sd == r["snr_db"]]
            if not same:
                print(f"{r['run_id']:<24} WGN {r['snr_db']:>3}  no noise estimate (last run, no idle blocks) | modes: {mixs}")
                continue
            noise, note = st.median(same), f"  (noise: the campaign's other runs at this setting, n={len(same)})"
        else:
            noise, note = inrun, "  (noise: in-run, last run of the campaign)"
    else:
        noise = st.median(gap)
        note = f"  (in-run noise {10*math.log10(inrun):.1f} dBFS)" if inrun else "  (in-run noise: too few idle blocks)"
    noise_by_setting.append((r["snr_db"], noise))
    snr = []
    for x0, x1, _, _ in mine:
        v = [p for t, p in pts if x0 + 0.35 <= t <= x1 - 0.1]
        if len(v) >= 5 and st.mean(v) > noise:
            snr.append(10 * math.log10((st.mean(v) - noise) / noise))
    snr.sort()
    if not snr:
        print(f"{r['run_id']:<24} WGN {r['snr_db']:>3}  no data bursts measured | modes: {mixs}")
        continue
    med = snr[len(snr) // 2]
    print(f"{r['run_id']:<24} WGN {r['snr_db']:>3}  data S:N {med:5.1f} dB  (n={len(snr)}, middle half "
          f"{snr[len(snr)//4]:.1f}..{snr[3*len(snr)//4]:.1f})  noise {10*math.log10(noise):.1f} dBFS | modes: {mixs}{note}")
    out.append({"run_id": r["run_id"], "setting_db": r["snr_db"], "data_snr_db": round(med, 2), "data_n": len(snr),
                "control_snr_db": "", "keyed_by": "Data2G TX log (sender)", "ardop_ptt_data": "", "data_modes": mixs})
if out:
    with open(f"{camp}/snr.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
    print(f"wrote {camp}/snr.csv")
