# CLAUDE.md

Guidance for Claude Code working in this repository. Keep this file short: it is loaded into every session.

## What this is

`hf-modem-bench` bench-tests software HF modems used with Winlink Express (ARDOP, VARA HF, Mercury, Data2G, Aether HF, ULTRA, and later VARA FM and Loki FM) through the IONOS HF channel simulator, between two Winlink Express instances on a Windows bench machine. The Python package `hfbench` (in `src/hfbench/`) builds run sheets, drives the bench unattended, measures true S:N, parses logs and charts results.

The operator (Jeremy, VA3ZTF) is the second station's hands: he turns the IONOS knob, runs tone checks and approves anything unusual.

## Where the current state lives

Read these instead of the whole history:

| Need | File |
| --- | --- |
| Current stage, order and every decision (D1-D7, dated) | `docs/test-plan.md`, **bottom of the "Decisions" table** |
| Latest results | `docs/results-log.md`, **last section only** (the file is 2,000+ lines; grep for the campaign name or ask the `scout` agent) |
| How a run is done | `docs/test-protocol.md` section 7 |
| Wiring and calibration | `docs/bench-setup.md` |
| Bench-machine scripts | `scripts/windows/README.md` |
| Published results | `docs/wgn-report.md` (white noise) |

As of 27 Nov 2026: white-noise stage complete for five modems; fading (MPG/MPM/MPP, N5TW sweep) done for VARA HF, Data2G MPG done, then Data2G MPM and MPP, Mercury dev build, ARDOP, Aether HF. Update this line when the stage changes.

## Rules that are easy to get wrong

- **The IONOS channel type is knob-only** (firmware 2.03): over USB it changes the display and S:N but not the channel processing. Group runs by channel and stop for the operator at each change; a tone check comes before each group.
- **Times are UTC** in Winlink and ARDOP logs and in all our stamps. Mercury's own log is local time.
- **Measured S:N is the x-axis**, never the IONOS setting.
- **VARA-protocol modems** (VARA HF, Mercury, Data2G, ULTRA) run with the bench relay (`-Relay`), which holds Winlink Express's 5-minute P2P timer DISCONNECT. Label every such result.
- **Don't reinstall `hfbench`** on the bench machine while a recording or campaign is running from `hfbench.exe`.
- **Bench scripts run in the desktop session.** Over SSH there are no audio devices or Winlink windows; use the `hfbench_*.ps1` wrappers, which register interactive scheduled tasks.
- **Never change levels, drive, or modem settings mid-stage** without recording it in `docs/test-plan.md` (Decisions) and `docs/results-log.md`.

## Privacy

Winlink logs contain callsigns, grid squares, positions and message subjects. Real logs, campaign data, partial files and reports stay git-ignored. Redact anything added to `tests/fixtures/` (grid square becomes `AA00AA`). The bench machine's name and address never go in the repo. Callsigns VA3ZTF and VE3XZQ may appear. Campaigns listed in `export-exclude.local` stay private until their owner agrees.

## Build and test

```sh
python -m venv .venv && .venv/bin/pip install -e '.[dev]'   # add ,plots for matplotlib
.venv/bin/pytest
```

Python 3.11+; core tools use only the standard library. matplotlib for charts, pyserial for IONOS control, sounddevice and numpy for audio checks.

## After each campaign

1. `hfbench results -d runs/<campaign> --verify payloads/<set>`; measured S:N with `scripts/txlog_snr.py` or `hfbench audio listen-report`.
2. Append the campaign to `docs/results-log.md` (setup, table of measured S:N and net bit/s, delivered/identical counts, incidents).
3. Update the Decisions table in `docs/test-plan.md` and the status table in `README.md` if the stage moved.
4. Commit with a one-line summary that names the modem, profile and result (existing history shows the style).

Steps 1-4 are mechanical: hand them to the `mechanical` agent.

## Model routing and session handoff

- The main session defaults to the model in `.claude/settings.json`. Change it any time with `/model`.
- Delegate by kind of work, using the agents in `.claude/agents/`:
  - `mechanical` (Sonnet): steps already known - docs, changelogs, logs, config, applying a decided plan, running builds and tests.
  - `deep` (Opus): diagnosis and design - bugs that resisted one attempt, DSP/protocol/concurrency, architecture, review or licensing judgment.
  - `scout` (Haiku, read-only): lookups in large files; returns only the answer.
- End a session with `/handoff`; start the next with `/pickup`. The handoff file (`.claude/handoff/NEXT.md`) is not committed.
