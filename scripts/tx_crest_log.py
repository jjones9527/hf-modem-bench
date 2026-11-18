#!/usr/bin/env python3
"""Transmit-side crest factor: record both stations' speaker outputs digitally (WASAPI
loopback, before the Windows volume and the IONOS, so no noise and no level change) and
write one JSON line per burst: station, start/end (unix), mean power, max peak and the
peak levels exceeded by 1 %, 0.1 % and 0.01 % of the burst's samples (dBFS). Crest
factor (PAPR) = a peak level minus the mean power; a sine is 3.0 dB. Needs the
`soundcard` package (bench, operator-approved 17 Nov 2026). Desktop session only.
usage: tx_crest_log.py HOURS OUT.jsonl
A burst is a run of 21-ms blocks above -60 dBFS mean power, ended by 0.2 s below it."""
import json, math, sys, threading, time
import numpy as np

# soundcard 0.4.3 reads WASAPI buffers with numpy.fromstring, which numpy 2 removed:
# the same bytes through frombuffer (copied, as fromstring did)
np.fromstring = lambda b, dtype=float, **kw: np.frombuffer(b, dtype=dtype).copy()
import soundcard as sc  # noqa: E402

SPEAKERS = {1: "Speakers (C-Media USB Audio Device   )", 2: "Speakers (3- USB Audio Device)"}
FS, BLOCK, ON_DB, GAP_S = 48000, 1024, -60.0, 0.2
hours, out = float(sys.argv[1]), sys.argv[2]
lock = threading.Lock()
fh = open(out, "a", buffering=1)


def db(x):
    return 10 * math.log10(max(x, 1e-20))


def run(st, name, t_end):
    mic = [m for m in sc.all_microphones(include_loopback=True) if m.isloopback and m.name == name][0]
    cur, quiet = None, 0.0
    with mic.recorder(samplerate=FS, blocksize=BLOCK) as rec:
        while time.time() < t_end:
            x = rec.record(numframes=BLOCK)
            t = time.time()
            # the channel that carries the signal: VARA writes only its configured channel
            # (station 2: Channel=2, the right), the others write both
            if x.ndim > 1:
                x = x[:, int(np.argmax(np.mean(x * x, axis=0)))]
            p = float(np.mean(x * x))
            if db(p) > ON_DB:
                if cur is None:
                    cur = {"t0": t - BLOCK / FS, "chunks": []}
                cur["chunks"].append(np.abs(x).astype(np.float32))
                cur["t1"] = t
                quiet = 0.0
            elif cur is not None:
                quiet += BLOCK / FS
                if quiet >= GAP_S:
                    a = np.concatenate(cur["chunks"])
                    pw = float(np.mean(a.astype(np.float64) ** 2))
                    q = np.quantile(a, [0.99, 0.999, 0.9999])
                    rec_ = {"st": st, "t0": round(cur["t0"], 3), "t1": round(cur["t1"], 3),
                            "s": round(cur["t1"] - cur["t0"], 3), "mean_dbfs": round(db(pw), 2),
                            "max_dbfs": round(20 * math.log10(max(float(a.max()), 1e-10)), 2),
                            "p99_dbfs": round(20 * math.log10(max(float(q[0]), 1e-10)), 2),
                            "p999_dbfs": round(20 * math.log10(max(float(q[1]), 1e-10)), 2),
                            "p9999_dbfs": round(20 * math.log10(max(float(q[2]), 1e-10)), 2)}
                    with lock:
                        fh.write(json.dumps(rec_) + "\n")
                    cur, quiet = None, 0.0


t_end = time.time() + hours * 3600
th = [threading.Thread(target=run, args=(st, n, t_end), daemon=True) for st, n in SPEAKERS.items()]
for t in th:
    t.start()
for t in th:
    t.join()
