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
| Winlink log parser | ⏳ waiting on sample logs |
| Analysis and reports (CSV, Markdown/HTML, throughput-vs-SNR plots) | ⏳ Phase 2 |

## Install

Requires Python 3.11 or later. The core tools use only the standard library. matplotlib is needed only for plots.

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
hfbench end completed              # or dnc / invalid, optionally with --notes "..."
hfbench status
hfbench manifest                   # creates runs/coarse01/manifest.csv
```

Run the `start` and `end` stamps on the machine that writes the Winlink logs, so that both use the same clock.

## Layout

| Path | Contents |
| --- | --- |
| `src/hfbench/` | `matrix` (TOML to run sheet), `manifest` (event log to manifest), `payload`, `cli` |
| `runs/` | Matrix files. Campaign directories (run sheet, events, manifest) are git-ignored. |
| `reports/` | Generated reports (git-ignored) |
| `docs/` | Test protocol |
| `tests/` | Unit tests. Log fixtures must be redacted. |

## Privacy

Winlink logs contain callsigns, grid squares and message subjects. Real logs, campaign data and reports are excluded by `.gitignore`. Redact anything you add to `tests/fixtures/`.
