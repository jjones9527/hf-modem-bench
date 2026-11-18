# Bench data for audit

Everything behind the results in [docs/results-log.md](../docs/results-log.md), exported
by [scripts/export_audit_data.py](../scripts/export_audit_data.py). The private values
below are replaced in every file; nothing else is changed.

| Replaced | With |
|---|---|
| the stations' grid square | `AA00AA` |
| the bench computer's name | `BENCH-PC` |
| its network address | `BENCH-IP` |
| the Windows user folder | `<user>` |

Callsigns (VA3ZTF, VE3XZQ) are kept. All times are UTC unless a file says otherwise
(Mercury's own engine log is in US Eastern time, UTC−5).

## In this folder

`campaigns/<name>/`, one folder per campaign (the matrix that made it is `runs/<name>.toml`):

| File | Contents |
|---|---|
| `runsheet.csv` | Every planned run: modem, IONOS settings, payload, replicate, time box |
| `events.jsonl` | Append-only log of every start, end, mark, invalidation and recovery, as written during the run |
| `manifest.csv` | One row per attempt (from the events): start/end, outcome, notes, Message-IDs. `final_attempt` marks the one that counts; `invalid` attempts are bench faults and excluded |
| `runs.csv`, `messages.csv` | Per-run and per-message results from both stations' Winlink logs (`hfbench results --verify`): delivered / corrupted / stall / cut, goodput (receiver side), net throughput, attachment check against the payload |
| `snr.csv` | Measured data S:N per run (`hfbench audio listen-report`; `scripts/mercury_snr.py` for Mercury, keyed by its PTT log; `scripts/data2g_snr.py` for Data2G, keyed by its TX lines, noise from the quiet gap after each run) |
| `crest.csv` | The sender's transmitted peak-to-average ratio (PAPR) per run: measured (`scripts/tx_crest_log.py` + `crest_report.py`, crest and cliff campaigns), or for the sweeps taken from the modem's crest campaign at the same setting (`crest_by_setting.py`, `source` column) |
| `console-*.txt` | The runner's console output |
| `levels-tonecheck.json`, `qam-precheck.json` | The tone check and 16QAM path check made before the campaign |
| `relay.txt` | VARA-protocol campaigns: the bench relay's state at start |

`partials/*.txt`: for every message that failed with data on disk, the byte-by-byte
comparison of Winlink's partial file with the compressed stream that was sent
(`scripts/check_partial.py`). The raw `.bin` files aren't published, because their
message headers carry the station's position inside the compressed data.
`mercury-relay-RQ7PT1JKEBHM` is from a test with three Mercury copies on one sound card
and is not counted as a result (results log, 15 Nov).

## The raw logs (GitHub release)

The raw files are too big for git (about 1.2 GB before compression). They are in
`bench-data-<date>.tar.gz`, attached to the repository's
[data releases](https://github.com/jjones9527/hf-modem-bench/releases), redacted the same way:

| Folder | Contents |
|---|---|
| `winlink/station1`, `winlink/station2` | Winlink Express session logs (`RMS Express YYYYMMDD.log`) and ARDOP TNC logs (`ARDOP_WinTNC_ARQSession_*`, `ARDOP_WinTNC_Debug_*`, which include every frame decode) |
| `mercury/` | Mercury engine logs, both stations |
| `data2g/` | Data2G host logs (`station<N>_host.log`, local time) and its start/stop log |
| `peaks/` | `txcrest-*.jsonl`: every transmitted burst's mean power and peak levels, both stations (WASAPI loopback); `peaks-*.json`: microphone block peaks (IONOS Lvl checks) |
| `relay/` and `<campaign>/*.log` | Bench-relay logs (every host↔modem control line, data-port sizes) and per-campaign Mercury logs |
| `listen/` | S:N recordings: per-block band power of both microphones (about 21 ms blocks) and ARDOP PTT times; re-analyse with `hfbench audio listen-report` |
| `qam/`, `levels/` | 16QAM path tests and tone checks |
| `reports/` | Charts and `points.csv` as generated |

## Reproducing a result

```sh
pip install -e '.[plots]'
hfbench audio listen-report bench-data/listen/listen-<stamp>.json --runs data/campaigns/<campaign>
hfbench report data/campaigns/sweep-ardop-50k data/campaigns/sweep-ardop-5k ... -o out/ --ceiling 22
```

`hfbench results` needs the raw Winlink logs laid out as on the bench; `runs.csv` and
`messages.csv` here are its output.
