# FM modem test plan (draft, 27 Nov 2026)

**Status:** draft for the operator's review. Nothing here is decided until it's recorded in the Decisions table of [test-plan.md](test-plan.md).

**Scope:** VARA FM and Loki FM, after the Data2G fading campaigns. Same bench, same method as the HF stages: two stations through the IONOS, a fixed workload, **measured S:N on the x-axis**, delivered/identical counts and net throughput as the headline (D7).

## 1. What changes from the HF bench

| Item | HF stages | FM stages | Why |
| --- | --- | --- | --- |
| IONOS bandwidth | 3000 Hz | **3000 Hz for narrow, 6000 Hz for wide** (`[ionos] bandwidth_hz`, already accepted by `matrix.py`) | Wide FM profiles use audio up to about 5.7 kHz (Loki wide 300–5700 Hz); the 3 kHz filter would cut them off |
| S:N reference | 3 kHz | **The IONOS bandwidth in use** (3 kHz or 6 kHz), recorded on every run | Same rule as test-protocol §3; a 6 kHz reading is 3 dB lower than a 3 kHz one for the same noise density |
| Channel profiles | WGN, then MPG/MPM/MPP fading | **WGN only** | The MP* presets model HF skywave; they don't represent an FM link, so FM fading results would mean little |
| Extra sweep | — | **Drive (deviation) sweep** at one S:N | FM modems are very sensitive to drive: too low loses S:N, too high clips in the radio's deviation limiter |
| Session driver | Winlink Express P2P (`hfbench run --automate`) | VARA FM: same. **Loki FM: its own test runner** (see §4) | Loki has no Winlink Express interface yet (its command set for Express is on hold pending the Winlink Development Team) |

### What an audio-only bench can and can't show

The IONOS adds white noise to audio. That is a fair stand-in for an FM link **above the FM threshold**, where the receiver's output S:N is what the modem sees. It does not reproduce:

- the FM threshold itself (clicks and capture as the RF signal fades);
- de-emphasis shaping of noise on the narrow path (roughly flat after de-emphasis, so white noise is close) and the rising ("triangular") discriminator noise on the wide 9600 port (white noise understates high-frequency noise there);
- radio key-up time (Loki narrow needs about 150 ms or less) and the radios' own audio filters.

So the FM stages answer "how does each modem perform against audio S:N", which is how Loki states its targets (top speed at 30 dB audio S:N or less, graceful down to 20–25 dB). An RF spot check (two radios into dummy loads through step attenuators) is optional, at the end (§6).

## 2. Modems and versions

| Modem | Version | Interface | Licence | Notes |
| --- | --- | --- | --- | --- |
| VARA FM | latest release, pinned for the stage | VARA TCP, session type "Vara FM P2P" | Registration at **both** ends, as decided for VARA HF (D2) | Narrow and Wide modes are separate campaigns |
| Loki FM | the `v0.1.0-testNN` release current at bring-up, pinned | Loki host interface, TCP 8600/8601 (`MYCALL`, `PROFILE NARROW/WIDE`, `CONNECT`, ...) | GPL-3, free | Profile is a user setting; both stations must match |

## 3. Matrix (per modem, per profile)

| Campaign | IONOS | S:N settings (dB) | Payload | Runs |
| --- | --- | --- | --- | --- |
| Level check (`cal-<modem>-<profile>`) | WGN 30 | 30 | tone check + 2 smoke runs | 1 |
| Drive sweep | WGN 30 | 30, at 4–5 drive settings 3 dB apart around the level check's | Text_5KB, 10 messages | 2 per setting |
| Sweep, 50 KB | WGN | 40, 35, 30, 25, 20 | Text_50KB, 10 messages | 3 |
| Sweep, 5 KB | WGN | 15, 10, 5, 0 | Text_5KB, 10 messages | 3 |
| Cliff search | WGN | from the lowest delivering point down in 1-2 dB steps | Text_5KB | 2 |

- One-way station 2 → station 1, 60-minute time box, recovery on, as the HF stages.
- Profiles: **Narrow** at `bandwidth_hz = 3000`, **Wide** at `bandwidth_hz = 6000`.
- Drive is fixed for the whole sweep at the best setting from the drive sweep, and recorded in the Decisions table.
- Time: about 4 campaigns × 2 profiles × 2 modems; roughly 40–50 hours unattended, plus bring-up.

Starter matrices for VARA FM are in `runs/fm-varafm-*.toml` (S:N points above, draft; check before use).

## 4. Tooling needed

1. **VARA FM modem profile** in `bench.py` `MODEM_PROFILES`: added as `"VARA FM": ModemProfile("Vara FM P2P", "", "", verified=False)`. Verify the session-type name and window titles at bring-up, as for VARA HF, then set `verified=True`.
2. **Relay:** check whether Winlink Express's 5-minute P2P DISCONNECT also hits VARA FM sessions (D6). If so, run with `-Relay` and label results, as for VARA HF.
3. **Loki FM runner.** Loki's own test mode (`--repeat N --pause S`, a series file, automatic test answering at the answering station) can carry the workload. Needed:
   - a `hfbench` step that sets the IONOS per run from the run sheet and waits while Loki runs its series;
   - a parser for Loki's series/session report into `sessions.csv` / `transfers.csv` (format from `jrtrint/open-fm-modem` `results/`: S:N dB, net bit/s per transfer), with a payload check equal to Winlink's;
   - the same S:N measurement (`txlog_snr.py` / `audio listen-report`) keyed to Loki's transmit log.
   Until Loki has a Winlink interface, Loki results are **modem-to-modem**, not through Winlink. Label them so, since VARA FM's include Winlink Express's overhead.
4. **6 kHz S:N reference** in the report and charts: axis label shows the bandwidth; never mix 3 kHz and 6 kHz points on one axis without converting.

## 5. Bring-up checklist (per modem)

1. Install both copies; one config per station; record versions and sha256.
2. Tone check at WGN 20/40 with `bandwidth_hz` set for the profile (wide: confirm the 4.5 kHz harmonic test still makes sense above the 6 kHz filter, or use the QAM path test).
3. Level check, then the drive sweep; pick the drive; record it (Decisions).
4. Smoke 3/3 at WGN 30.
5. Sweeps, then cliff.

## 6. Optional: RF spot check (after the sweeps)

Two radios (for example IC-9700 and IC-7100, both with 9600 data ports) into dummy loads, coupled through step attenuators, a few points per profile for each modem. This shows the FM threshold and key-up effects the audio bench can't. Run only after the audio-bench results are in, and only on frequencies and powers that keep everything into dummy loads.

## 7. Open questions for the operator

1. Which VARA FM version, and is a second licence available for station 2?
2. Loki FM: test through its own runner now (modem-to-modem), or wait for a Winlink interface?
3. Confirm from the IONOS manual (rev 2.03, §3) that 6000 Hz behaves like 3000 Hz apart from the filter (same S:N definition, same noise source).
4. Is the RF spot check wanted?
