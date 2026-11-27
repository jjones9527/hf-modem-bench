# Results log — Stage 1: ARDOP 1.0.2.9, white noise

Part of the [results log](../results-log.md). All times UTC.

## Stage 1: ARDOP 1.0.2.9 WGN sweep (started 13 Nov 2026, 16:26)

Campaigns `sweep-ardop-50k` (Text_50KB; WGN 40, 22, 17; 9 runs) and `sweep-ardop-5k`
(Text_5KB; WGN 17, 12, 7, 2; 12 runs). Both are one-way, 10 messages per run,
recovery on, 60-min time box, 3 replicates in seeded random order (seed 13). Listen
`listen-20261113-1626-1…4` (4 × 150 min).

**Direction changed to station 2 → 1** (Sabrent playback → Syba capture). The pre-check
at 16:25 found the Sabrent's *capture* degrading:

| 16QAM path check, full level | 12 Nov 20:40 | 12 Nov 22:35 | 13 Nov 16:25 |
|---|---|---|---|
| Syba → Syba | 22.0 dB | 21.0 dB | 21.6 dB (tilt 0.1) |
| Syba → Sabrent (old data path) | 18.7 | 15.7 | **14.7** (high carriers 12.3) |
| Sabrent → Syba (new data path) | 18.3 | 17.4 | **17.0** (tilt 8.3) |
| Sabrent → Sabrent | 17.5 | 13.2 | 12.7 |

Tone check 16:20: transmit −0.3 / −0.4 dB against the reference, mismatch +0.1, receive
mismatch +0.7, mic noise 33 dB below the reference. Unchanged.

---

### Sweep incident: ARDOP's busy detector blocked every call at WGN 40 (13 Nov)

`sweep-ardop-50k-0002` (17:22) and `-0003` (18:57), both at WGN 40, ended *dnc (no
connection)* after 90 minutes. Start was pressed, station 2 never called, and Winlink
logged "Connection cancelled" about 2 min later. Runs at WGN 22 and 17 in between
connected normally.

**Cause, confirmed at 21:41** during `-0005` (WGN 40): both Ardop session windows
showed **"Channel Busy"**, with no traffic on the bench. ARDOP 1.0.2.9's busy detector
(`BusyDetector.vb`, BusyDet = 5) reports busy when the strongest ~94 Hz of the
spectrum stands about 9 dB above the background, or the widest 66% about 12 dB above
it. It only runs while ARDOP is idle. At WGN 40 the IONOS adds almost no noise, so the
background is the bench's own noise, which is not flat (Sabrent tilt, small spurs).
That trips the detector. At WGN 22 and 17 the IONOS's flat noise dominates.

**Fix (operator's decision, 21:50):** BusyDet = 0 (detector off) in both
`ARDOP_Win TNC.ini` files. There is no other station to protect on the bench. The
detector acts only while idle, so data transfer is unaffected. ARDOP rewrites its ini
when it closes, so the change was made with both Winlink/ARDOP instances closed
(`scripts/windows/busydet_off.ps1`, backups `*.busydet5.bak`). After the restart, both
windows showed "Channel Free" at WGN 40.
- `-0002` and `-0003` were marked **invalid** (bench fault) and are repeated.
- `-0005`'s interrupted first attempt recorded nothing and is also repeated.
- A repeat needs fresh Message-IDs, because Winlink skips IDs it already holds. The
  runner now does this automatically.

**Also seen:** `-0004` (WGN 17, about 10 dB) was the first time-boxed run: 6/10
delivered at 683–701 bit/s in 60 min, cut cleanly, followed by a normal recovery.

### sweep-ardop-50k results (13–14 Nov 2026, ended 04:02 UTC)

All 9 runs ran unattended after the busy-detector fix. There were 4 automatic
recoveries (after 3 time boxes and 2 failures), and none needed the operator.
Goodput is the receiver's figure. S:N is the measured data-frame S:N
(`listen-report --runs`, energy keying). Runs 0008 and 0009 started after the
recording ended, so their points use the two recorded replicates.

| IONOS setting | measured data S:N | runs | delivered / attempted | goodput median (range) | net throughput | outcomes |
|---|---|---|---|---|---|---|
| WGN 40 | **21.9 dB** (21.9–22.0) | 0002, 0003, 0005 | 30/30 | 1,548 bit/s (1,380–1,563) | 1,259 bit/s | 3 completed |
| WGN 22 | **15.4 dB** (15.4, 15.4) | 0001, 0007, 0009 | 20/22 | 1,259 bit/s (1,161–1,295) | 999 bit/s | 1 completed, 2 dnc |
| WGN 17 | **10.8 dB** (10.8, 10.8) | 0004, 0006, 0008 | 18/18 | 684 bit/s (665–723) | 552 bit/s | 3 time-boxed at 6/10 |

- **Data integrity:** all 68 delivered attachments are byte-identical to the payload
  (`results --verify`).
- **The bench ceiling is about 22 dB, not 19.** WGN 40 gives 21.9 dB
  measured data S:N on the 2 → 1 path. The earlier 18–19 dB came from WGN 28. The
  charts mark 22 dB.
- **Zero failures at 22 dB (30/30, 16QAM).** At about 18 dB (WGN 28, cal7) 16QAM lost
  about 9%. This fits the CRC analysis: fewer symbol errors give the weak CRC fewer
  chances to miss one.
- **Two failures at 15.4 dB (8PSK), both corruption that Winlink caught:**
  - `0007` KI7L6KOQNGPV: "Checksum error. Failed to assemble correct binary image."
    `check_partial.py` finds 7 corrupted bytes within 78 bytes (stream offsets
    27185–27263), with XOR patterns of 1–3 adjacent bits. That is the one-carrier,
    few-symbol signature seen at 16QAM, so the CRC weakness also affects 8PSK.
  - `0009` ERZXWBFBHD5G: "Received data stream not correct format.
    ByteIndex=104679". Winlink's B2F block parser rejected the stream 2.5 min into
    the message and disconnected. The partial is clean up to its last byte, so the
    bad bytes landed in the block framing rather than the compressed data.
    **`hfbench results` first classed this as a stall.** "not correct format" is now
    a corruption marker (test fixture `tests/fixtures/sweep0009`). It also appears 5
    times in the 10 Nov two-way logs, which predate `results`.
- **About 10 dB is a clean slow regime:** 18/18 delivered and no errors. 60 min
  holds 6 messages, so every run was time-boxed.
- **Net vs goodput:** net is 80–81% of goodput where nothing failed (handover
  and session set-up) and 79% at 15.4 dB, where two failed sessions cost time.

Charts: `hfbench report logs/archive/sweep-ardop-50k --ceiling 22` (goodput, net,
delivered; WGN).

**Pre-check for sweep-ardop-5k (14 Nov 04:05 UTC):**
- **Tone check:** transmit −0.2 / −0.3 dB against the reference (from WGN 20),
  mismatch +0.1, receive mismatch +0.7. Unchanged.
- **16QAM path check:** the Sabrent's capture has recovered since 13 Nov.

| 16QAM path check, full level | 13 Nov 16:25 | 14 Nov 04:05 |
|---|---|---|
| Syba → Syba | 21.6 dB | 21.9 dB |
| Syba → Sabrent | 14.7 | 15.2 |
| Sabrent → Syba (data path) | 17.0 | **22.6** (tilt 8.2) |
| Sabrent → Sabrent | 12.7 | 19.1 |

sweep-ardop-5k started 04:13 UTC with listen `listen-20261114-0413-1…5`.

### sweep-ardop-5k results (14 Nov 2026, 04:13–12:10 UTC)

12 runs, Text_5KB, one-way 2 → 1. Three automatic recoveries (all after time boxes),
no operator action, and **no failed message**.

| IONOS setting | measured data S:N | delivered / attempted | goodput median (range) | net throughput | outcomes |
|---|---|---|---|---|---|
| WGN 17 | **10.8 dB** | 30/30 | 752 bit/s (530–860) | 499 bit/s | 3 completed |
| WGN 12 | **6.7 dB** (6.6, 6.7) | 30/30 | 247 bit/s (195–331) | 206 bit/s | 3 completed |
| WGN 7 | **3.1 dB** | 30/30 | 160 bit/s (130–182) | 143 bit/s | 3 completed |
| WGN 2 | **−1.8 dB** | 21/21 | 84 bit/s (76–87) | 69 bit/s | 3 time-boxed at 7/10 |

- **Data integrity:** all 111 delivered attachments are byte-identical to the payload.
- **S:N:** energy keying and ARDOP's PTT agree to 0.1 dB at every point, including
  −1.8 dB. Run 0012 started 3 min before the recorder's third segment ended (5 bursts
  recorded), so its reading is ignored. `hfbench report` now needs at least 30 data
  bursts for a run's S:N (`MIN_SNR_BURSTS`), and the 12 dB point uses 0005 and 0009.
- **The overlap point joins the two payload sets.** At 10.8 dB, Text_5KB goodput is
  752 bit/s against 684 bit/s for Text_50KB, but net throughput is 499 against 552 bit/s.
  The fixed per-message handover (about 20 s) costs more on a 4.3 KB transfer than on
  a 42 KB one. Net throughput is therefore only comparable within a payload set; the
  curves are compared between modems at equal payload.
- **The steepest drop is 10.8 → 6.7 dB** (752 → 247 bit/s). Data frames decoded at
  station 1 (ARDOP debug log, "Frame Type OK"; the archived log ends at 07:12, so
  WGN 12 is from run 0005's first minutes only):

  | point | frames decoded |
  |---|---|
  | 10.8 dB (0003) | 4PSK.2000.100 94, 4PSK.1000/500 4 |
  | 6.7 dB (0005, partial) | 4PSK.1000.100 23, 4PSK.2000.100 13 |
  | 3.1 dB (0001) | 4PSK.500.100 380, 4FSK.500 1 |
  | −1.8 dB (0004) | 4PSK.500.100 546, 4FSK.500.100 41 |

  ARDOP moves from 2000 Hz 4PSK to 1000 Hz around 7 dB, to 500 Hz 4PSK by 3 dB, and
  begins to fall back to 4FSK at −1.8 dB.
- **No knee yet.** ARDOP still delivers every message at −1.8 dB, at 84 bit/s.

**IONOS noise is not linear in the setting.** Per-run noise floor and received signal
level on station 1's microphone (2 → 1 path):

| WGN setting | noise floor dBFS (3 kHz) | received signal dBFS | measured data S:N | setting − measured |
|---|---|---|---|---|
| 40 | −52.3 | −30.3 | 21.9 | (bench ceiling) |
| 22 | −44.5 | −29.1 | 15.4 | 6.6 |
| 17 | −40.3 | −29.4 | 10.8 | 6.2 |
| 12 | −36.0 | −29.3 | 6.7 | 5.3 |
| 7 | −31.9 | −28.7 | 3.1 | 3.9 |
| 2 | −28.3 | −30.1 | −1.8 | 3.8 |
| −5 | −24.4 (idle check) | | about −5 (expected) | |
| −10 | −22.4 (idle check) | | about −7 (expected) | |

The signal stays within 1.6 dB while each 5 dB step adds only 3.6–4.3 dB of noise, and
less below WGN 2. This is why the chart axis is the measured S:N. It also means
the setting-to-S:N offset can't be carried between settings (test-plan.md updated).
The IONOS accepted WGN −5 and −10 (and the Lvl meter, which reads the input, is
unaffected).

Charts (both payload sets): `hfbench report logs/archive/sweep-ardop-50k
logs/archive/sweep-ardop-5k --ceiling 22`.

**Next: `sweep-ardop-5k-low`** (WGN −5 and −10, Text_5KB, 3 replicates, seed 14), started
14 Nov 12:20 UTC after a fresh pre-check. Tone check: transmit −0.0 / −0.3 dB,
mismatches unchanged. 16QAM data path 2 → 1: 20.7–22.0 dB MER. Listen
`listen-20261114-1220-1…3`.

### sweep-ardop-5k-low incident: failed calls were not retried (14 Nov)

The operator saw a failed connection attempt during run 0003. The logs showed:

- **0001 (WGN −10) and 0003 (WGN −10):** station 2 called once ("Calling VA3ZTF"), and
  Winlink gave up 35–36 s later ("Failure connecting to VA3ZTF"). The runner then
  waited out the 90-minute abort time with the bench idle. The protocol (§4) allows
  `abort_retries` = 3 failed connects per run, but the runner never re-called. The
  station 1 log it watches shows nothing for a failed call.
- **0002 (WGN −5): a real result.** It connected at 13:57 after a 4-min call. The
  B2F handshake took until 14:05, and the first 4.5 KB message was still incomplete
  when the link dropped at 14:16 (19.4-min session, 0/10 delivered).

**Fix:** while no session is detected, the runner reads the caller's session window
every 30 s. Two readings in a row of "listening" (Start enabled, Abort disabled, not
connected) mean the call failed. It presses Start again, and after `abort_retries`
failed calls it ends the run as **`dnc` "no connection after N calls"**, within minutes.
Tests: `test_failed_calls_are_retried_then_dnc`, `test_call_that_connects_on_retry_runs_normally`.

0001 was marked **invalid** (runner fault: one call instead of three) and is re-run.
0003 had recorded no start and is simply re-run. 0002 stands. Campaign restarted
15:25 UTC with the fixed runner.

### sweep-ardop-5k-low results (14 Nov 2026, re-run from 15:25 UTC)

With the re-call fix, all 6 runs ended without the operator. Every one is `dnc`.

| IONOS setting | measured data S:N | runs | result |
|---|---|---|---|
| WGN −5 | **−6.0 dB** (−5.9 / −6.0 / −6.1; ARDOP PTT −5.7) | 0002, 0004, 0006 | connected each time, **0 of 10 delivered**; session dropped 8–19 min in |
| WGN −10 | no data frames to measure (ARDOP's connect bursts read −10.3 to −10.7 dB) | 0001, 0003, 0005 | **no connection after 3 calls**, 3 times |

How the −6 dB sessions fail: the connect (4FSK) succeeds within seconds, but the
B2F handshake crawls. In 0004, station 2 logged its proposals at 15:49:04, and station
1 logged them at 15:56:19, about 7 min for a few hundred bytes. The first message
starts, and the link drops 1–8 min later. The sender's ARQ stats (0002, 0004): ARDOP's own leader
S:N −10.2 / −9.8 dB, 49 and 40 of about 250 frame-type decodes failed, 4FSK quality
44–61 (97 at good S:N). Only 1,839 bytes were sent per session, and 66 received.

At WGN −10, energy keying found no data bursts (expected, below about −2 dB). ARDOP's
PTT log keys the connect requests at −10.3 to −10.7 dB. That is lower than the −7 dB
expected from the idle noise floor (−22.4 dBFS at WGN −10), so this point is reported
only as "below −6 dB: no connection" and isn't plotted.

### knee-ardop-5k results (14–15 Nov 2026, 18:14–00:52 UTC)

WGN 0 and −2, 3 replicates each, Text_5KB, 60-min time box. Pre-checks: tone check
−0.2 / −0.4 dB from the reference, 16QAM 20.2–21.9 dB MER on path 2→1. Every run
connected on the first call and ran to the time box.

| IONOS setting | measured data S:N | control S:N | runs | delivered | goodput median | net | main data frames |
|---|---|---|---|---|---|---|---|
| WGN 0 | **−0.8 dB** (−0.8 / −0.8 / −0.8) | −0.9 dB | 0002, 0005, 0006 | 24/24 (6 cut) | 95 bit/s | 79 bit/s | 4FSK.500 |
| WGN −2 | **−2.9 dB** (−3.0 / −2.9 / −2.8) | −3.0 dB | 0001, 0003, 0004 | 21/21 (5 cut) | 91 bit/s | 69 bit/s | 4FSK.500 and 4FSK.500.100S |

- 45 of 45 attachments byte-identical. No corruption, no stall.
- At WGN −2, ARDOP spent more and more time in 4FSK.500.100S (short frames): 238 of
  801 data frames in 0001, 638 of 944 in 0003, 1,020 of 1,065 in 0004. Run 0004 was
  the slowest (72 bit/s median, 6 delivered). That is the first sign of the cliff.
- **The cliff now lies between −2.9 dB (WGN −2, 100%) and −6.0 dB (WGN −5, 0%).**

**Measured data S:N depends on ARDOP's frame type.** WGN 0 measured −0.8 dB, above
WGN 2's −1.8 dB, although WGN 0 adds more noise. The noise is the same at a given
setting, but ARDOP's bursts are not equally strong: at the same drive, its 4FSK
frames arrive stronger than its PSK frames, and the wider the PSK frame, the weaker
(peak-limited multi-carrier). The gap between control frames (always 4FSK) and data
frames, averaged per setting:

| setting | main data frames | data S:N | control S:N | gap |
|---|---|---|---|---|
| WGN 40 | 16QAM.2000 | 21.9 | 28.1 | 6.2 dB |
| WGN 22 | 8PSK.2000 | 15.4 | 20.1 | 4.6 dB |
| WGN 17 | 4PSK.2000 | 10.8 | 15.5 | 4.7 dB |
| WGN 12 | 4PSK.1000/2000 | 6.7 | 10.7 | 4.0 dB |
| WGN 7 | 4PSK.500 | 3.1 | 5.8 | 2.7 dB |
| WGN 2 | 4PSK.500, some 4FSK | −1.8 | 0.9 | 2.7 dB |
| WGN 0 | 4FSK.500 | −0.8 | −0.9 | 0 |
| WGN −2 | 4FSK.500 | −2.9 | −3.0 | 0 |
| WGN −5 | 4FSK | −6.0 | −6.0 | 0 |

Control S:N falls steadily with the setting (+0.9, −0.9, −3.0, −6.0 dB at WGN 2, 0,
−2, −5), so the bench is consistent. The charts keep data S:N, the S:N the receiver
actually saw for each modem's own waveform (D5: equal average drive). Read the −1.8
and −0.8 dB points as "ARDOP chose PSK and was weaker on the air" versus "ARDOP chose
FSK", not as an S:N measurement error. This matters for every modem that changes
waveform: each point's frame mix is reported with it.

### Stage 1 summary: ARDOP 1.0.2.9 on WGN (13–14 Nov 2026)

| measured data S:N | payload | delivered | goodput median | net throughput | main data frames |
|---|---|---|---|---|---|
| 21.9 dB (ceiling) | 50 KB | 30/30 | 1,548 bit/s | 1,259 bit/s | 16QAM.2000 |
| 15.4 dB | 50 KB | 20/22 (2 corrupt, caught) | 1,259 bit/s | 999 bit/s | 8PSK.2000 |
| 10.8 dB | 50 KB | 18/18 (time-boxed) | 684 bit/s | 552 bit/s | 4PSK.2000 |
| 10.8 dB | 5 KB | 30/30 | 752 bit/s | 499 bit/s | 4PSK.2000 |
| 6.7 dB | 5 KB | 30/30 | 247 bit/s | 206 bit/s | 4PSK.1000/2000 |
| 3.1 dB | 5 KB | 30/30 | 160 bit/s | 143 bit/s | 4PSK.500 |
| −1.8 dB | 5 KB | 21/21 (time-boxed) | 84 bit/s | 69 bit/s | 4PSK.500, some 4FSK |
| −0.8 dB | 5 KB | 24/24 (time-boxed) | 95 bit/s | 79 bit/s | 4FSK.500 |
| −2.9 dB | 5 KB | 21/21 (time-boxed) | 91 bit/s | 69 bit/s | 4FSK.500 (+ short frames) |
| −6.0 dB | 5 KB | 0/6 started (3 sessions) | | 0 | |
| below −6 dB | 5 KB | no connection | | | |

- **Speed in good conditions:** 1,548 bit/s per message, and 1,259 bit/s net, at the
  bench ceiling (22 dB).
- **Robustness:** every message delivered from 22 dB down to −1.8 dB, except 2 at
  15.4 dB, which were corrupted frames that Winlink caught. Nothing delivered at −6 dB,
  and no connection below. **The reliability cliff lies between −2.9 and −6 dB**
  (knee-ardop-5k, 15 Nov).
- **Knee by the plan's definition** (success ≥ 90% and net ≥ 10% of the best, i.e.
  ≥ 126 bit/s): **3.1 dB** (143 bit/s). At −1.8 dB it is still 100% reliable but nets
  69 bit/s (5.5%). The net criterion mixes payload sets, so both numbers are reported.
- **Data integrity:** 224 of 224 delivered attachments are byte-identical. The weak
  ARDOP 1.0.2.9 CRC shows as caught corruption (4 at 18 dB in cal7wgn28, 2 at 15.4
  dB here), never as bad data delivered.

Charts: `hfbench report logs/archive/sweep-ardop-50k logs/archive/sweep-ardop-5k
logs/archive/sweep-ardop-5k-low --ceiling 22`.
Frame types from station 1's ARDOP debug log ("Frame Type OK") in runs 0001 (15.4 dB:
8PSK.2000 309 of 313), 0003 (21.9 dB: 16QAM.2000 788 of 796) and 0004 (10.8 dB, 50 KB:
4PSK.2000 536).
