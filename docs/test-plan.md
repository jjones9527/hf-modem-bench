# Test plan (revised 13 Nov 2026)

This revises the staging in [test-protocol.md](test-protocol.md) §6 using what the
ARDOP campaigns of 10–13 Nov taught us (see [results-log.md](results-log.md)). Items
marked **Decision** need the operator's choice before the work that depends on them.

## What the comparison has to answer

1. **Speed in good conditions:** the highest sustained goodput each modem reaches
   at the best S:N the bench can provide (WGN, and the mild fading profile MPG).
2. **Robustness in challenging conditions:** how goodput and reliability fall as
   S:N drops and fading gets harsher. Specifically:
   - the S:N where each modem stops delivering reliably (its *knee*);
   - how it behaves on MPM, MPP and MPD;
   - whether it ever passes bad data or stalls instead of failing cleanly.

## What changes, and why

| Change | Reason (from the ARDOP campaigns) |
|---|---|
| **One-way workload**: 10 messages from station 1 to station 2 | Two-way runs mixed two unequal hardware paths. One failure ended the session for both directions. |
| **Automatic recovery on for every campaign** (`--recover`) | Failures are routine near a modem's limit. Without recovery every failure stopped the bench until the operator reset it. Tried and working (oneway28r: 2 unattended recoveries, about 85 s each). |
| **Reliability is measured per message**, not per run | At 9% message failure a 10-message run completes only about 4 times in 10. *Completed runs* hides how much got through. |
| **Goodput from the receiving station's log** | The sender's log adds about 20 s of handover per message, about 10% low. This was found on 13 Nov, after it looked like a 10% difference between directions. |
| **Net throughput** as a headline metric | It includes the cost of failures. ARDOP 16QAM at about 18 dB is 25% faster per message than 8PSK at about 15 dB, but nets about the same. |
| **Delivered-data check** against the original payload | Winlink caught every ARDOP corruption, but that has only been checked through its log. A modem that passes bad data through every check would only show up this way. |
| **The S:N axis is the measured data S:N**, not the IONOS setting | At cal7, data S:N ≈ setting − 7 to −10 dB, and it flattens out near the bench ceiling. |
| **Partials are kept and checked** after every failed message | `scripts/check_partial.py` tells corruption from a stall and locates the bad bytes. |

## Metrics (per run, per message and per test point)

| Metric | Definition |
|---|---|
| **Goodput per message** | Compressed bytes (`FC EM`) × 8 ÷ transfer time from the **receiver's** log ("Receiving" → "received"). Report the median and range per point. |
| **Net throughput** | Compressed bytes delivered × 8 ÷ total session time, failed sessions included, recovery time excluded. Measures speed and robustness together. |
| **Message success rate** | Messages delivered ÷ messages attempted (offered by the sender). Failures are split by type: *corrupted* (checksum or decompress error), *stall* (no progress, ARQ timeout), *link lost*, *timeout* (run time limit). |
| **Knee** | The lowest measured S:N with message success ≥ 90%, and with net throughput still at least 10% of the modem's best. |
| **Data integrity** | SHA-256 of every delivered attachment against the payload file. Any mismatch is reported as a headline finding. |
| **Speed level / mode** | ARDOP: from its debug log. VARA-type modems: from their own logs where available. |
| **Crest factor and IONOS Lvl** | Recorded per modem. The Lvl must never go red. |

Report n, median and range for every point. Use 3 replicates on the coarse pass
and 5 near the knee.

## Run length at low S:N

At 10 × 42 KB per run, a modem running at 300 bit/s needs about 3 hours per run.
Below about 95 bit/s, not even one message fits in a 60-minute run. Two options:

- **A. Time-boxed runs:** every run stops after 10 messages **or 60 minutes**.
  Net throughput and message success still work; at very low S:N a run may deliver
  nothing, which is itself the result.
- **B. A small payload below a set S:N:** a second fixed set of 10 × about 5 KB
  messages, used below (say) 10 dB. Run one overlap point with both sets to show
  how the two connect.

**Decision D3:** recommended A + B: time-box every run, and use the small set
below 10 dB.

## Bench

- **Measured ceiling:** data S:N about 18–20 dB with the current adapters. The bench
  floor is 32 dB below the reference, and the 16QAM MER on Sabrent paths is 13–19 dB
  and varies. That's enough for ARDOP's top mode. It probably caps VARA HF below
  its fastest levels, which would understate exactly the "good conditions" answer.
- **Decision D1:** replace the Sabrent with a second adapter of the Syba's model
  (C-Media, flat, about 22 dB MER) before any VARA testing. Acceptance: all four
  16QAM paths within about 1 dB MER and flat, and the tone check within 1 dB. If
  that isn't possible, report the ceiling in every chart.
- Turn off USB selective suspend (still on).
- **Level policy, Decision D5:** set each modem so its **average** power at the IONOS
  matches the reference, which is what the IONOS S:N setting assumes, while keeping
  the Lvl meter out of the red. Record the crest factor. Modems with high peaks then
  get no S:N advantage from a hotter average, and the real-transmitter caveat about
  peak power stays in the report.

## Stages and order

**Stage 0: tooling (before the next campaign)**

1. Per-message results from **both** stations' logs: receiver-side goodput,
   failure type, and net throughput per run.
2. Delivered-attachment SHA-256 check at the receiving station after each run.
3. `audio listen` keyed from the audio itself (energy detection) instead of
   ARDOP's log, so it measures any modem's S:N.
4. Recovery and session start made modem-aware: session type (Ardop P2P / VARA HF
   P2P), TNC executable, and ports from the run sheet.
5. Time-boxed runs (D3).
6. A first report generator: goodput, net throughput and message success against
   measured S:N, per modem and profile.

**Stage 1: ARDOP 1.0.2.9, WGN sweep** (unattended, about 18 h)
- One-way, recovery on, time-boxed. IONOS settings chosen to give data S:N of
  about 20, 15, 10, 5, 0 and −5 dB (exact settings from the listen check), or until
  nothing is delivered. 3 replicates, then 5 at the two points around the knee.
- WGN 22 and 28 are already done at cal7: 77 messages. They are re-run one-way
  only if Stage 0 changes the metrics.

**Stage 2: next modem: Data2G 0.4.2 or Mercury 1.9.23** (needs neither a licence
nor a new adapter)
- Bring-up for each: both installs configured with their own TNC ports (8300/8301
  for station 1, 8400/8401 for station 2; the ARDOP TNCs closed); a UI survey of the
  session window; the drive level set to the reference (D5); a smoke test at about
  18 dB.
- Then the same WGN sweep as ARDOP.

**Stage 3: VARA HF 4.09**
- **Decision D2:** registration at both ends (a key for VE3XZQ, or a bench licence
  from the author). Unregistered VARA is speed-limited, so its results can't be
  published until this is settled.
- Ideally after D1, so its top speed isn't capped by the bench.

**Stage 4: fading profiles** (all modems)
- MPG, MPM, MPP, MPD at three S:N points per modem: near its best, mid-range, and
  about 5 dB above its WGN knee. 3 replicates each, because the IONOS has no seed
  control.

**Stage 5: impairments (WGN only)**
- Frequency offset ±50 Hz, slow drift, flat fading, and an S:N step mid-run
  (adaptation speed).

**Optional: ARDOP 1.0.3.x.** **Decision D4:** the current ARSFI development build
verifies RS parity as well as the CRC, which should remove the 16QAM corruption.
Repeating the WGN 28 point and the sweep with it would show what that is worth. It
should only be published if that build is a release.

## Time budget (unattended running)

A 10-message run takes about 45–60 min at good S:N, and the 60-min time box limits
low-S:N runs.

| Stage | Runs per modem | Hours per modem |
|---|---|---|
| WGN sweep | about 22 | about 20 |
| Fading (4 profiles × 3 S:N × 3) | 36 | about 35 |
| Impairments | about 10 | about 9 |

That's about 65 h per modem, about 260 h for four. Fading is the largest part. With
recovery working it can run overnight and across days. A second Windows machine
or IONOS isn't needed. If time is short, use 2 replicates on the fading coarse
pass and add replicates only where results are close.

## Decisions needed

| # | Decision | Recommendation |
|---|---|---|
| D1 | Replace the Sabrent with a second Syba-model adapter | Yes, before VARA |
| D2 | VARA HF registration at both ends | Ask the VARA author about a key for the second callsign or a bench licence |
| D3 | Low-S:N run length | Time-box at 60 min, plus a small payload set below 10 dB |
| D4 | Include ARDOP 1.0.3.x | Yes, if it's a release (or labelled as a development build) |
| D5 | Level policy | Equal average power at the IONOS reference; Lvl never red; record the crest factor |
