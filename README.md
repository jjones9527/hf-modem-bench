# hf-modem-bench

`hf-modem-bench` is a toolchain for bench-testing software HF modems used with Winlink Express: ARDOP, VARA HF, Mercury, Data2G and others that speak the ARDOP or VARA host protocol.

A fixed workload goes through two Winlink Express instances and the IONOS HF channel simulator. Between runs only two things change: the modem and the channel settings. The tools:

- generate the run sheet from a test matrix;
- drive the bench unattended: set the IONOS, queue each run's messages in both Winlink Express instances, start and end the session, and recover the bench after a failure;
- measure the true S:N of each run from the received audio;
- join both stations' Winlink logs to the runs, check every delivered attachment against the payload, and chart goodput, net throughput and delivery against measured S:N.

Documents:

| Document | Contents |
| --- | --- |
| [docs/wgn-report.md](docs/wgn-report.md) | **White-noise results, full report**: five modems, charts, comparisons and test details |
| [docs/interim-report-wgn.md](docs/interim-report-wgn.md) | White-noise results, short summary |
| [docs/test-plan.md](docs/test-plan.md) | Current plan: questions, metrics, stages, decisions |
| [docs/results-log.md](docs/results-log.md) | Every campaign's results and bench incidents, in order |
| [docs/test-protocol.md](docs/test-protocol.md) | Test design and run procedure |
| [docs/bench-setup.md](docs/bench-setup.md) | Wiring, level matching and the current calibration |
| [docs/test-environment.md](docs/test-environment.md) | Hardware, software and settings of the bench |
| [docs/log-formats.md](docs/log-formats.md) | Winlink, ARDOP, VARA-protocol and Mercury log formats |
| [scripts/windows/README.md](scripts/windows/README.md) | Helper scripts on the Windows bench machine |
| [docs/charts/](docs/charts/) | Published charts: `interim-wgn/` for all five modems in white noise (net throughput, per-message rate, connect time, equal-peak view; `points.csv`) |
| [docs/bug-reports/](docs/bug-reports/) | Reports sent upstream: ARDOP 1.0.2.9 carrier check, Mercury 1.9.23 receiver freeze (#579), Winlink P2P timer (Mercury #392) |

## Status (20 Nov 2026)

| Part | Status |
| --- | --- |
| Bench software: run sheets, IONOS control, unattended runner with recovery, Winlink log parsing, attachment check, measured S:N, crest factors, charts | ✅ |
| Bench relay for VARA-protocol modems (`scripts/vara_relay.py`): logs the host interface and holds Winlink's 5-min P2P timer | ✅ |
| White noise (WGN): ARDOP 1.0.2.9, Mercury 1.9.23, Data2G 0.5.1, VARA HF 4.9.1, Aether HF 0.2.0-beta.159 | ✅ done 13–20 Nov ([report](docs/wgn-report.md)) |
| ARDOP 1.0.3.3 development build | 50 KB sweep only; newer build to come |
| ULTRA 0.6.2 | paused (secup/ProjectUltra#38) |
| Modem73, Quicksilver | not tested (no Winlink ARQ interface; not ready) |
| Fading channels (CCIR), then other multipath | next ([test-plan.md](docs/test-plan.md)) |
| Mercury re-test | on its next release |

## Install

Requires Python 3.11 or later. The core tools use only the standard library. matplotlib is needed for charts, pyserial for IONOS control, and sounddevice and numpy for the audio checks.

The Windows bench machine has Python 3.12 (all users, on PATH) with `pyserial`, `sounddevice` and `numpy`. To update `hfbench` there, build a wheel (`pip wheel . -w dist --no-deps`), copy it over, and run `pip install --force-reinstall --no-deps` on it. Don't reinstall while a recording or campaign is running from `hfbench.exe`.

```sh
python -m venv .venv
.venv/bin/pip install -e '.[dev]'      # add ,plots for matplotlib
.venv/bin/pytest
```

## Quick start

A campaign on the bench (details in [docs/test-protocol.md](docs/test-protocol.md) §7 and [scripts/windows/README.md](scripts/windows/README.md)):

```sh
hfbench sheet runs/sweep-ardop-5k.toml                     # creates runs/sweep-ardop-5k/runsheet.csv
# on the bench machine:
hfbench messages build -d runs\sweep-ardop-5k --payloads payloads\Text_5KB --s1-call VA3ZTF --s2-call VE3XZQ --s1-messages 0 --s2-messages 10
hfbench_start_listen.ps1 -Minutes 150 -Setting 0 -Repeat 6        # S:N recording
hfbench_start_campaign.ps1 -Campaign sweep-ardop-5k -MaxRuns 12 -AutoContinue -Recover [-Relay]
# afterwards:
hfbench results -d runs\sweep-ardop-5k --verify payloads\Text_5KB
hfbench audio listen-report listen-*.json --runs runs/sweep-ardop-5k
hfbench report runs/sweep-ardop-50k runs/sweep-ardop-5k -o reports/ardop-wgn --ceiling 22
```

`-Relay` is for VARA-protocol modems (VARA HF, Mercury, Data2G). Winlink and ARDOP log in UTC, and the stamps are UTC too (Mercury's own log is in local time).

To parse logs on their own: `hfbench parse "RMS Express 20261110.log" --ardop ARDOP_WinTNC_ARQSession_20261110.log -o out/` writes `sessions.csv` and `transfers.csv`. See [docs/log-formats.md](docs/log-formats.md).

## Layout

| Path | Contents |
| --- | --- |
| `src/hfbench/` | `matrix` (TOML to run sheet), `manifest`, `bench` (runner, recovery, modem profiles), `winlink_ui` (Winlink Express automation), `ionos`, `audio` and `qamtest` (level, path and S:N checks), `logparse`, `results`, `report`, `messages`, `payload`, `cli` |
| `runs/` | Matrix files, one per campaign. Campaign directories (run sheet, events, manifest, results) are git-ignored. |
| `payloads/` | The fixed payload sets `Text_50KB` and `Text_5KB` |
| `scripts/` | Bench helpers: partial-file check, ARDOP CRC simulation, VARA-protocol relay, Mercury level and S:N scripts (`mercury_level.py`, `mercury_snr.py`), sweep watcher, archive script, Windows scripts |
| `logs/`, `reports/` | Archived bench data and generated reports (git-ignored) |
| `docs/` | Plan, protocol, results log and bench records |
| `tests/` | Unit tests. Log fixtures must be redacted. |

## Privacy

Winlink logs contain callsigns, grid squares, positions and message subjects. Real logs, campaign data, partial files and reports are excluded by `.gitignore`. Redact anything you add to `tests/fixtures/` (the grid square becomes AA00AA); the bench machine's name and address never go in the repo. The callsigns VA3ZTF and VE3XZQ may appear.
