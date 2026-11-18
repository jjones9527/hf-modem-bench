#!/usr/bin/env python3
"""Per-run data S:N for a one-way campaign of ANY modem, keyed by the transmit log
(tx_crest_log.py: the sender's bursts, start and end, taken digitally): station 2's
bursts of 2 s and longer are its data. Otherwise as data2g_snr.py (below), whose
Data2G-specific burst source this replaces; the data-mode column is left empty.
usage: txlog_snr.py campaign_dir txcrest.jsonl[,more.jsonl] listen1.json [listen2.json ...]

From data2g_snr.py:
Sender = station 2 (data 2 -> 1), heard on station 1's microphone. Bursts are the sender's
'TX b<n> data <mode> x<frames> <seconds>s' lines (data2g_level.bursts: queued time, audio
within 0.2 s); each burst's S:N uses its blocks from 0.35 s after the line to 0.1 s before
its end. Noise: median mic-1 block power in the quiet gap after the run (end + 10 s to
end + 100 s: the runner waits 120 s before the next run sets the IONOS, and nobody
transmits), so dense traffic inside the run doesn't matter. For comparison it also prints
the in-run estimate (blocks outside energy-detected bursts and the sender's bursts) where
at least 10 such blocks exist. A campaign's last run, whose gap may hold the next
campaign's setting, uses its own gap if it agrees within 1 dB with the other runs' gaps
at the same setting, else their noise, else (flagged) the in-run estimate, which reads
low at low S:N (the receiver's replies and faint bursts get into it). Also
prints the run's data-mode mix (share of data air time per mode) and writes snr.csv."""
import csv, json, math, statistics as st, sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "src")
sys.path.insert(0, str(Path(__file__).parent))
from hfbench import audio

camp, txlogs, *listens = sys.argv[1:]
tx = []
for f in txlogs.split(","):
    for l in open(f):
        if l.strip():
            b = json.loads(l)
            if b["st"] == 2 and b["s"] >= 2:
                tx.append((b["t0"], b["t1"], "data", ""))
tx.sort()
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
    own_gap = st.median(gap) if len(gap) >= 100 else None
    if r["run_id"] != last_id and own_gap is not None:
        noise = own_gap
        note = f"  (in-run noise {10*math.log10(inrun):.1f} dBFS)" if inrun else "  (in-run noise: too few idle blocks)"
    else:
        # the last run's gap may hold the next campaign's setting: use it only if it agrees
        # (1 dB) with the other runs' gaps at this setting; else their noise; else in-run
        same = [n for sd, n in noise_by_setting if sd == r["snr_db"]]
        ref = st.median(same) if same else None
        check = ref if ref is not None else inrun   # with no other run, the in-run estimate (a looser check)
        tol = 1.0 if ref is not None else 1.5
        if own_gap is not None and (check is None or abs(10 * math.log10(own_gap / check)) <= tol):
            noise, note = own_gap, "  (noise: own gap" + (", agrees with the other runs)" if ref else
                                                          ", agrees with the in-run estimate)" if inrun else ")")
        elif ref is None and inrun is not None:
            noise, note = inrun, "  (noise: in-run; the gap after the run disagrees, likely the next campaign's setting)"
        elif ref is not None:
            noise, note = ref, f"  (noise: the campaign's other runs at this setting, n={len(same)})"
        elif inrun is not None:
            noise, note = inrun, "  (noise: in-run only; low S:N reads low)"
        else:
            print(f"{r['run_id']:<24} WGN {r['snr_db']:>3}  no noise estimate | modes: {mixs}")
            continue
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
                "control_snr_db": "", "keyed_by": "tx log (sender, digital)", "ardop_ptt_data": "", "data_modes": mixs})
if out:
    with open(f"{camp}/snr.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
    print(f"wrote {camp}/snr.csv")
