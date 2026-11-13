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

## Run length at low S:N (D3, decided 13 Nov 2026)

At 10 × 42 KB per run, a modem running at 300 bit/s needs about 3 hours per run.
Below about 95 bit/s not even one message fits in an hour. Two rules handle this.
The full wording is in [test-protocol.md](test-protocol.md) §4.

1. **Every run is time-boxed at 60 minutes** (`time_box_minutes = 60`; the 90-minute
   abort rule stays as a safety net). At the box the runner ends the session and
   records outcome **`timeboxed`** with the messages delivered. This is not a failure.
2. **Below 10 dB measured data S:N the small payload set `Text_5KB` is used**
   (10 × 5,120 bytes, the first 5,120 bytes of each Text_50KB file). At each modem's
   10 dB point the run is made with **both** sets, so the curves can be joined.

## Bench

- **Measured ceiling:** data S:N about 18–20 dB with the current adapters. The bench
  floor is 32 dB below the reference, and the 16QAM MER on Sabrent paths is 13–19 dB
  and varies. That's enough for ARDOP's top mode. It probably caps VARA HF below
  its fastest levels, which would understate exactly the "good conditions" answer.
- **D1 (decided 13 Nov): keep the current adapters.** No second adapter is available.
  The ceiling is a stated bench limit: every chart marks the highest data S:N the
  bench reached, and the report says the fastest modes may be capped by it. The
  data direction stays station 1 (Syba playback) → station 2 (Sabrent capture). The
  16QAM path check before each campaign records the Sabrent's state that day.
- Turn off USB selective suspend (still on).
- **Level policy (D5, decided 13 Nov):** set each modem so its **average** power at the IONOS
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

**Stage 1: ARDOP 1.0.2.9 (the release from winlink.org), WGN sweep** (unattended, about 18 h)
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
- **D2 (decided 13 Nov): settle registration at the start of the VARA stage.** First
  check whether one callsign's key registered on both instances gives full speed
  (the operator may test this beforehand). If not, ask the VARA author about a key
  for the second callsign or a bench licence. Unregistered VARA is speed-limited,
  so no VARA result is published until both ends are confirmed registered.

**Stage 4: fading profiles** (all modems)
- MPG, MPM, MPP, MPD at three S:N points per modem: near its best, mid-range, and
  about 5 dB above its WGN knee. 3 replicates each, because the IONOS has no seed
  control.

**Stage 5: impairments (WGN only)**
- Frequency offset ±50 Hz, slow drift, flat fading, and an S:N step mid-run
  (adaptation speed).

**Stage 6 (last): Phil Sherrod's updated ARDOP (1.0.3.x development build).** D4,
decided 13 Nov. ARDOP 1.0.2.9 as shipped by winlink.org is the release under test.
The updated build verifies RS parity as well as the CRC, which should remove the
16QAM corruption. It is tested at the end, on the same points as 1.0.2.9, and
labelled as a development build in every chart and table.

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

## Decisions (13 Nov 2026)

| # | Decision | Outcome |
|---|---|---|
| D1 | Replace the Sabrent | **No:** no second adapter. Keep the current adapters, report the ceiling, keep the direction 1 → 2. |
| D2 | VARA HF registration at both ends | **At the VARA stage:** first test one key on both instances; else ask the author. No VARA results published until both ends are confirmed registered. |
| D3 | Low-S:N run length | **60-min time box on every run**, plus **Text_5KB below 10 dB**, with an overlap point. Documented in test-protocol §4. |
| D4 | ARDOP versions | **1.0.2.9 (release) now; Phil's updated build (1.0.3.x, development) last**, labelled as such. |
| D5 | Level policy | **Equal average power** at the IONOS reference; Lvl never red; record the crest factor. |
