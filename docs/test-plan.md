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
| **One-way workload**: 10 messages per run over one fixed path; from 13 Nov, station 2 (Sabrent playback) → station 1 (Syba capture) | Two-way runs mixed two unequal hardware paths. One failure ended the session for both directions. |
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

- **Measured ceiling:** data S:N about 22 dB with the current adapters (WGN 40 on the
  2 → 1 path, 14 Nov; first estimated at 18–20 dB from WGN 28). The bench
  floor is 32 dB below the reference, and the 16QAM MER on Sabrent paths is 13–19 dB
  and varies. That's enough for ARDOP's top mode. It probably caps VARA HF below
  its fastest levels, which would understate exactly the "good conditions" answer.
- **D1 (decided 13 Nov): keep the current adapters.** No second adapter is available.
  The ceiling is a stated bench limit: every chart marks the highest data S:N the
  bench reached, and the report says the fastest modes may be capped by it. The
  data direction is station 2 (Sabrent playback) → station 1 (Syba capture) from 13 Nov,
  when the Sabrent's capture was degrading. The
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
3. **Done 13 Nov:** `audio listen-report --runs CAMPAIGN` measures each run's S:N
   over its own window and setting. Transmissions are found from the audio energy
   by default (any modem), with ARDOP's PTT log as a cross-check.
   - **Validation:** on oneway28r, energy keying gave 18.3 dB against 18.4 dB from
     ARDOP's PTT, with burst starts within 0.06 s. In one run, gaps in ARDOP's PTT
     record around midnight made PTT keying read −10.7 dB.
   - **Limit:** synthetic tests hold within 1 dB down to **0 dB**. On the bench,
     energy keying still matched ARDOP's PTT at **−1.8 dB** (sweep-ardop-5k, WGN 2).
     Below about −2 dB, ARDOP uses its PTT log. Other modems use their received
     signal level from the higher-S:N points of the same campaign, minus the
     noise floor measured at the setting (idle periods, always measurable).
   - **The IONOS setting is not linear in noise (found 14 Nov).** The received signal
     level is constant within 1.6 dB across settings, but each 5 dB step down in the
     setting adds only 3.6–4.3 dB of noise, and less below WGN 2 (noise floor at WGN
     2 / −5 / −10: −28.3 / −24.4 / −22.4 dBFS). The offset (setting − measured)
     is therefore not constant (6.6 dB at WGN 22, 3.8 dB at WGN 2), and it can't be
     carried from one setting to another. The bench's lowest data S:N is about −7 dB.
4. **Done 13 Nov:** recovery and session start are modem-aware. `MODEM_PROFILES` in
   `bench.py` gives each modem's Winlink session type and each station's TNC program.
   The runner picks the profile from the run sheet's `modem`, and
   `--modem/--session-type/--tnc1/--tnc2` override it. **ARDOP is verified; the VARA
   HF, Data2G and Mercury entries are best guesses** (session type 'Vara HF P2P';
   TNCs `C:\VARA\VARA.exe`, `…\Data2G\data2g-host.exe`, `…\MercuryHF\mercury.exe`
   and their second installs). They are printed as UNVERIFIED until confirmed at
   bring-up. Bring-up check for each modem: select the session type once by hand
   at both stations, then try `hfbench_ui_do.ps1 … -Do open-session -Arg "<type>"`
   and a full `hfbench recover`.
5. Time-boxed runs (D3).
6. **Done 13 Nov:** `hfbench report CAMPAIGN... -o DIR [--ceiling dB]` writes three
   charts per profile (goodput per message with its range, net throughput, and
   messages delivered, each against measured data S:N) as PNG and SVG, plus
   `points.csv` as the table view.
   - **Inputs:** `hfbench results` (runs.csv, messages.csv) and
     `audio listen-report --runs` (snr.csv).
   - **Encoding:** each modem keeps a fixed colour slot from a palette validated for
     colour-blind separation. Filled markers are Text_50KB, open markers
     Text_5KB. Lines carry direct labels, the bench ceiling is marked, and the legend
     sits below the plot.

**Stage 1: ARDOP 1.0.2.9 (the release from winlink.org), WGN sweep** (unattended, about 18 h)
- One-way, recovery on, time-boxed. IONOS settings chosen to give data S:N of
  about 20, 15, 10, 5, 0 and −5 dB (exact settings from the listen check), or until
  nothing is delivered. **Run 13–14 Nov:** WGN 40, 22, 17 (Text_50KB) and 17, 12, 7, 2
  (Text_5KB) gave 21.9, 15.4, 10.8, 6.7, 3.1 and −1.8 dB. ARDOP still delivered 100% at
  −1.8 dB, so `sweep-ardop-5k-low` adds WGN −5 and −10 (about −5 and −7 dB, the
  bench's floor). **Result (14 Nov):** 0/6 at −6.0 dB (connects, then drops), no
  connection at WGN −10. Reliability cliff between −1.8 and −6 dB. The knee by the
  definition above is 3.1 dB; it is still 100% reliable at −1.8 dB. Summary in
  results-log.md, "Stage 1 summary". 3 replicates, then 5 at the two points around the knee.
  **Knee runs (15 Nov):** WGN 0 (−0.8 dB) 24/24 and WGN −2 (−2.9 dB) 21/21, both
  4FSK.500; cliff between −2.9 and −6.0 dB. Measured data S:N depends on the frame
  type ARDOP chooses (PSK frames 2.7–6.2 dB weaker than 4FSK at the same drive), so
  each point's frame mix is reported with it.
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

**Stage 3b: Modem73** (added 14 Nov at the operator's request; not downloaded yet)
- The operator downloads it when this stage comes up. Nothing about it is assumed
  until then: version, licence, how it attaches to Winlink Express (session type,
  TNC program and ports), and whether two instances can run on one PC.
- Bring-up as for Stage 2: a profile in `MODEM_PROFILES` (unverified until tried),
  its own TNC ports for each station, a UI survey, the drive level set to the
  reference (D5), busy detection off if it has any, and a smoke test at about 18 dB.
- Then the same WGN sweep as ARDOP. Its chart colour is fixed slot 6 (`#008300`).

**Stage 3c: Aether HF** (added 14 Nov at the operator's request; not downloaded yet)
- github.com/KK4ODA/aether-hf, MIT or Apache-2.0. On 14 Nov the latest release was
  0.2.0-beta.159, with a Windows installer (`x64-setup.exe`, not Authenticode-signed)
  and a headless `aetherd` zip. OFDM plus a 16-FSK floor, 2300 Hz or 500 Hz wide,
  36 bit/s to about 5.5 kbit/s (author's figures, not measured here).
- Its README says it attaches to Winlink Express as a VARA HF session with automatic
  launch off (host ports 8300/8301). Not verified here, and not yet known whether two
  instances run on one PC with separate ports.
- Releases come several times a day and both ends must run the same link protocol:
  pin one release for the whole stage and record it in every result.
- Bring-up and the WGN sweep as for Stage 3b. Chart colour fixed slot 7 (`#6250d6`).

**Stage 3d: ULTRA (ProjectUltra)** (added 14 Nov at the operator's request; not downloaded yet)
- github.com/secup/ProjectUltra, MIT. On 14 Nov the latest release was
  v0.6.2-pre-alpha, with `projectultra-windows.zip`. OFDM/OTFS and multi-carrier
  DPSK, 2.8 kHz, 2.4 kHz or 500 Hz wide (author's figures, not measured here).
- It offers TCP ports 8300/8301, but its README doesn't name VARA, ARDOP or Winlink
  Express, so whether Winlink Express can drive it is the first thing to establish.
- Pre-alpha: the on-air protocol can change between versions. Pin one release and
  label every result with it. Tested after the more mature modems.
- Bring-up and the WGN sweep as for Stage 3b. Chart colour fixed slot 8 (`#e34948`).

**Quick Silver**: requested 14 Nov, not found (no modem by that name turned up).
Waiting for a link or author from the operator.

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

That's about 65 h per modem, about 455 h for seven (ARDOP 1.0.2.9, Data2G, Mercury, VARA HF, Modem73, Aether HF, ULTRA), plus Phil's ARDOP build on ARDOP's points. Fading is the largest part. With
recovery working it can run overnight and across days. A second Windows machine
or IONOS isn't needed. If time is short, use 2 replicates on the fading coarse
pass and add replicates only where results are close.

## Decisions (13 Nov 2026)

| # | Decision | Outcome |
|---|---|---|
| D1 | Replace the Sabrent | **No:** no second adapter. Keep the current adapters, report the ceiling, data direction 2 → 1 from 13 Nov. |
| D2 | VARA HF registration at both ends | **At the VARA stage:** first test one key on both instances; else ask the author. No VARA results published until both ends are confirmed registered. |
| D3 | Low-S:N run length | **60-min time box on every run**, plus **Text_5KB below 10 dB**, with an overlap point. Documented in test-protocol §4. |
| D4 | ARDOP versions | **1.0.2.9 (release) now; Phil's updated build (1.0.3.x, development) last**, labelled as such. |
| D5 | Level policy | **Equal average power** at the IONOS reference; Lvl never red; record the crest factor. |
