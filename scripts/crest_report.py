#!/usr/bin/env python3
"""Per-run transmitted crest factor (PAPR) from tx_crest_log.py's bursts.
usage: crest_report.py txcrest.jsonl [more.jsonl ...] -- campaign_dir [campaign_dir ...]
For each run (manifest, final attempts) and each station: the bursts inside the run's
window, their air time, and the air-time-weighted median of PAPR at 0.01 % (p9999 minus
mean power), 0.1 % and the burst maximum; a sine is 3.0 dB at every level. The sender
(station 2, data) is what the equal-peak comparison uses; station 1 sends the replies.
Writes crest.csv in each campaign folder."""
import csv, json, sys
from datetime import datetime

i = sys.argv.index("--")
logs, camps = sys.argv[1:i], sys.argv[i + 1:]
bursts = [json.loads(l) for f in logs for l in open(f) if l.strip()]


def wmedian(pairs):
    pairs = sorted(pairs)
    tot = sum(w for _, w in pairs)
    acc = 0.0
    for v, w in pairs:
        acc += w
        if acc >= tot / 2:
            return v
    return float("nan")


for camp in camps:
    rows = [r for r in csv.DictReader(open(f"{camp}/manifest.csv"))
            if r.get("final_attempt") == "yes" and r.get("outcome") not in ("invalid", "") and r.get("end_utc")]
    out = []
    for r in rows:
        a = datetime.fromisoformat(r["start_utc"]).timestamp() - 60
        b = datetime.fromisoformat(r["end_utc"]).timestamp()
        rec = {"run_id": r["run_id"], "setting_db": r["snr_db"]}
        line = f"{r['run_id']:<24} WGN {r['snr_db']:>3}"
        for st in (2, 1):
            bs = [x for x in bursts if x["st"] == st and a <= x["t0"] and x["t1"] <= b]
            air = sum(x["s"] for x in bs)
            if not bs:
                rec.update({f"st{st}_bursts": 0}); line += f" | st{st}: no bursts"; continue
            p4 = wmedian([(x["p9999_dbfs"] - x["mean_dbfs"], x["s"]) for x in bs])
            p3 = wmedian([(x["p999_dbfs"] - x["mean_dbfs"], x["s"]) for x in bs])
            mx = wmedian([(x["max_dbfs"] - x["mean_dbfs"], x["s"]) for x in bs])
            mean = wmedian([(x["mean_dbfs"], x["s"]) for x in bs])
            rec.update({f"st{st}_bursts": len(bs), f"st{st}_air_s": round(air, 1), f"st{st}_mean_dbfs": round(mean, 2),
                        f"st{st}_papr_0.01pct_db": round(p4, 2), f"st{st}_papr_0.1pct_db": round(p3, 2),
                        f"st{st}_papr_max_db": round(mx, 2)})
            line += (f" | st{st}: {len(bs):>3} bursts {air:6.0f} s, mean {mean:6.1f} dBFS, "
                     f"PAPR 0.01% {p4:4.1f} / 0.1% {p3:4.1f} / max {mx:4.1f} dB")
        print(line)
        out.append(rec)
    if out:
        keys = sorted({k for o in out for k in o}, key=lambda k: (k not in ("run_id", "setting_db"), k))
        with open(f"{camp}/crest.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(out)
        print(f"wrote {camp}/crest.csv")
