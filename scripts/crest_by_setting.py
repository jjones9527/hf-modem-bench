#!/usr/bin/env python3
"""Give sweep runs the transmitted PAPR their modem showed at the same IONOS setting.
usage: crest_by_setting.py [--map SETTING=FROM ...] crest_campaign_dir campaign_dir [campaign_dir ...]
--map 0=-2: runs at WGN 0 take the crest run at WGN -2 (only where the modem used the same
modes at both settings, e.g. ARDOP 4FSK.500 at WGN 0 and -2, knee-ardop-5k).
The sweeps ran before tx_crest_log.py existed (17 Nov 2026). A modem's PAPR depends on
the modes it uses, and its modes on the channel, so the crest-<modem> campaign (one run
per sweep setting, same level, same bench) stands in for it. Writes crest.csv in each
campaign folder, with a `source` column naming the crest run used. Runs at a setting the
crest campaign didn't cover (e.g. WGN -10) get none."""
import csv, sys

args, maps = sys.argv[1:], {}
while args and args[0] == "--map":
    a, b = args[1].split("="); maps[a] = b; args = args[2:]
src, camps = args[0], args[1:]
by_setting = {}
for r in csv.DictReader(open(f"{src}/crest.csv")):
    by_setting[r["setting_db"]] = r
for camp in camps:
    sheet = {r["run_id"]: r for r in csv.DictReader(open(f"{camp}/runsheet.csv"))}
    out = []
    for rid, s in sheet.items():
        c = by_setting.get(maps.get(s["snr_db"], s["snr_db"]))
        if c is None:
            continue
        row = {k: v for k, v in c.items() if k != "run_id"}
        row.update({"run_id": rid, "setting_db": s["snr_db"], "source": c["run_id"]})
        out.append(row)
    if out:
        keys = ["run_id", "setting_db", "source"] + [k for k in out[0] if k not in ("run_id", "setting_db", "source")]
        with open(f"{camp}/crest.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(out)
    print(f"{camp}: {len(out)} of {len(sheet)} runs given a PAPR from {src}")
