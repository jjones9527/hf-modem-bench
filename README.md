# hf-modem-bench

`hf-modem-bench` is a toolchain for bench-testing software HF modems used with Winlink Express, such as VARA HF, ARDOP and Data2G.

A fixed workload goes through two Winlink Express instances and the IONOS HF channel simulator. Between runs only two things change: the modem and the channel settings. The tools do three jobs:

- Generate the run sheet from a test matrix.
- Timestamp each run so that nothing is typed by hand.
- Join Winlink session logs to those runs and produce comparable results.

See [docs/test-protocol.md](docs/test-protocol.md) for the test design.

## Status

| Part | Status |
| --- | --- |
| Matrix → run sheet, run stamping, manifest, payload tools | ✅ |
| Winlink session log + ARDOP session-stats parser (`hfbench parse`) | ✅ |
| Bench runner (`hfbench run`): IONOS serial control, log-based stamping, abort rule | ✅ |
| Winlink Express automation (`--automate`): message import from build-once templates, Start/Abort | ✅ (pilot pending) |
| Tone check and true-S:N measurement (`hfbench audio check / listen`) | ✅ |
| Session ↔ run join, both-ends pairing, audio calibration, ARDOP debug timeline | ⏳ next |
| Analysis and reports (CSV, Markdown/HTML, throughput-vs-SNR plots) | ⏳ Phase 2 |

## Install

Requires Python 3.11 or later. The core tools use only the standard library. matplotlib is needed only for plots, and pyserial for IONOS control.

The Windows bench machine has Python 3.12 (all users, on PATH) with `pyserial`, `sounddevice` and `numpy`. To update `hfbench` there, build a wheel (`pip wheel . -w dist --no-deps`), copy it over, and run `pip install --force-reinstall --no-deps` on it.

```sh
python -m venv .venv
.venv/bin/pip install -e '.[dev]'      # add ,plots for matplotlib
.venv/bin/pytest
```

## Quick start

```sh
hfbench payload make payloads/payload-20k.bin --bytes 20000 --seed 1   # prints the sha256
cp runs/example-matrix.toml runs/coarse01.toml                         # edit modems, versions, hash
hfbench sheet runs/coarse01.toml                                       # creates runs/coarse01/runsheet.csv

export HFBENCH_CAMPAIGN=runs/coarse01
hfbench next                       # shows the settings for the next run
hfbench start coarse01-0001        # stamps the start time
hfbench mark "WGN:5"               # optional: timestamp a mid-run event
hfbench end completed              # or dnc / invalid, optionally with --notes "..."
hfbench status
hfbench manifest                   # creates runs/coarse01/manifest.csv
```

Winlink and ARDOP log in UTC, and the stamps are UTC too. Any machine on NTP can run the stamps, as long as its clock is within about a second of the Windows bench machine.

To parse logs: `hfbench parse "RMS Express 20261110.log" --ardop ARDOP_WinTNC_ARQSession_20261110.log -o out/` writes `sessions.csv` and `transfers.csv`. See [docs/log-formats.md](docs/log-formats.md).

## Layout

| Path | Contents |
| --- | --- |
| `src/hfbench/` | `matrix` (TOML to run sheet), `manifest` (event log to manifest), `logparse`, `payload`, `cli` |
| `runs/` | Matrix files. Campaign directories (run sheet, events, manifest) are git-ignored. |
| `reports/` | Generated reports (git-ignored) |
| `docs/` | Test protocol |
| `tests/` | Unit tests. Log fixtures must be redacted. |

## Privacy

Winlink logs contain callsigns, grid squares and message subjects. Real logs, campaign data and reports are excluded by `.gitignore`. Redact anything you add to `tests/fixtures/`.
