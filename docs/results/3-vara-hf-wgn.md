# Results log — Stage 3: VARA HF 4.9.1, white noise

Part of the [results log](../results-log.md). All times UTC.

## Stage 3: VARA HF 4.9.1, registered at both ends (18-19 Nov 2026)

VARA HF 4.9.1 on both stations, 2750 Hz, P2P through the bench relay (D6), session type
"Vara HF P2P". **Registered at both ends** (D2 resolved, test-plan.md): station 2's Winlink
(`C:\RMS Express 2`) has VA3ZTF as a second callsign and runs with it active, so station
2's VARA answers `REGISTERED VA3ZTF`; every result below is full speed, no inference.
VARA keeps no log of its own the bench can read, so its data bursts come from the
transmit-side loopback log (`tx_crest_log.py`): measured S:N by `scripts/txlog_snr.py`
(station 2's bursts of 2 s or more, noise from the quiet gap after each run), PAPR by
`scripts/crest_report.py`, both per run.

**Bring-up.**
- vara-reg-check (WGN 40): no connect in 3 calls. Station 1's Winlink session had been
  opened before VARA started, so it wasn't listening (operator: Listen indicator yellow, 2300 Hz
  showing). Fixed by recovery (restart of Winlink's session); `recover()` now sets the
  session type in the ini first (`bench.set_session_type`).
- vara-reg-check2 (WGN 40, 3 × 50 KB): connected at 2750 Hz, speed levels 14-16, 3/3
  identical.
- **Level (D5 exception).** vara-level at ALC drive −5: data 5.4 dB under the tone reference
  (`burst_level.py`). At drive 0 the IONOS Lvl meter went over 1,200 mV p-p, into the red
  (operator, sweep-vara-50k-0001's first attempt, marked `invalid` and repeated). VARA's
  fast-mode data has the highest crest factor measured (11.7 dB at 0.01 %). **Never red
  comes first: drive −3 on both stations** (peaks about 900 mV p-p, no red, operator), fast-mode
  average about 3.4 dB under the reference. peak-vara (WGN 40, 3 × 50 KB) at −3: 3/3.
- **smoke-vara (WGN 18): one byte lost inside VARA.** 2 of 10 delivered (2,230 and 2,780
  bit/s), then the receiving Winlink rejected the third ("Received data stream not
  correct format") and the session ended. The kept partial matches the sent message for
  its first 40,928 compressed bytes, then everything is shifted by one: **exactly one byte
  missing.** The relay passed on all 42,519 bytes Winlink gave it for that message, and
  station 1 has no relay, so the byte was lost between station 2's VARA data port and
  station 1's. Winlink caught it (nothing bad stored); the cost was the session. It did not
  happen again in the 311 later messages. Not reported to VARA's author (operator).

**sweep-vara-50k / sweep-vara-5k** (18-19 Nov, 12:54-00:21 UTC): the sweep matrix as for
the other modems, 3 runs per setting, randomised order, 10 messages each, relay holding.

| IONOS | Measured data S:N | Data PAPR | Workload | Delivered | Net | Batch rate | Connect |
|---|---|---|---|---|---|---|---|
| WGN 40 | 25.8 dB | 11.7 dB | 50 KB | 30/30 | 3,341 bit/s | 3,831 | 8-9 s |
| WGN 22 | 17.9 | 11.7 | 50 KB | 30/30 | 2,803 | 3,225 | 8 |
| WGN 17 | 13.4 | 11.6 | 50 KB | 30/30 | 1,898 | 2,032 | 8 |
| WGN 17 | 13.4 | 11.6 | 5 KB | 30/30 | 1,274 | 1,603 | 8-9 |
| WGN 12 | 9.1 | 11.2-11.3 | 5 KB | 30/30 | 961 | 1,218 | 8-9 |
| WGN 7 | 5.4 (3.7, 5.4, 5.4) | 10.7-10.8 | 5 KB | 30/30 | 582 | 661 | 8-9 |
| WGN 2 | 1.8 | 7.4 | 5 KB | 30/30 | 262 | 280 | 8 |
| WGN −2 | −0.5 | 3.0 | 5 KB | 30/30 | 139 | 144 | 8-9 |
| WGN −5 | −3.5 | 3.0 | 5 KB | 30/30 | 135 | 141 | 9 |

- **270/270 delivered, every attachment byte-identical** (`--verify`); no hang, no failed
  call, no corruption. crest-vara (one 3 × 5 KB run per setting): 24/24 identical.
- **VARA keeps its peak, not its average, fixed.** At the same drive its data average was
  −15.0 dBFS (digital) in the fast modes, −14.1 at WGN 12-7, −12.7 at WGN 2 and −9.4 in the
  FSK modes at WGN −2 and −5, which have a pure constant envelope (PAPR 3.0 dB, a sine).
  So at the low settings VARA put about 5.5 dB more average power into the channel than
  in its fast modes, about 2 dB over the reference. The measured S:N axis includes this
  (it is measured, not set), so the comparison on it stays fair; comparisons by IONOS
  setting would not be. (Data2G's FSK cliff modes do the same.)
- WGN 7's run sweep-vara-5k-0014 measured 3.7 dB against 5.4 for the other two, and was
  slower (527 against 608-621 bit/s net), with the same noise and the same transmitted
  level (−13.9 against −14.1 dBFS). Not explained; VARA's mode choice isn't logged where the
  bench can read it.
- Replies (station 1): PAPR 6.3-6.4 dB in the fast modes, 3.1 in FSK. VARA's 2018
  specification gives 9 dB for data and 6 for acks; we measure 11.7 at 0.01 % and 10.3 at
  0.1 % for data.

**Cliff search at WGN −5** (`scripts/vara_cliff.sh`, 19 Nov 01:33-08:00 UTC): as Data2G's,
VARA's ALC drive lowered on both stations (`hfbench_vara_drive.ps1`), 10 × 5 KB, two runs
per step, 60-min time box, relay holding; stop after the first step that delivers nothing.

| ALC drive | Measured data S:N | PAPR | Delivered | Net | Batch rate |
|---|---|---|---|---|---|
| −3 (sweep, WGN −5) | −3.5 dB | 3.0 dB | 30/30 | 135 bit/s | 141 |
| −6 | −6.5 dB (−6.6, −6.5) | 3.0 | 10/20 (time box) | 50 | 61 |
| −9 | −9.4 dB | 3.0 | 4/20 (time box) | 20 | 24 |
| −12 | −12.4 dB (−12.3, −12.5) | 3.0 | **0/20** | 0 | − |

- Every delivered attachment byte-identical (14/14). At −12.4 dB VARA still connected
  (10-11 s) and started the first message in both runs (a partial kept each time), but
  delivered nothing in two hours. **VARA's last delivering point: −9.4 dB, 2 messages an
  hour.** cliff-vara-d15 has a run sheet only: never run (the driver misread the 0 and was
  stopped by hand; `vara_cliff.sh` fixed).
- Data2G 0.5.1 for comparison at the same bench: 8/20 at −11.5 dB, 3/20 at −13.9 dB.

**VARA HF overall:** 319 messages delivered, every one byte-identical; one corrupted
(the smoke test's lost byte, caught by Winlink). Time to connect 8-9 s (10-11 s at the
cliff), the slowest of the four modems tested so far.

### The comparison with VARA HF (19 Nov 2026)

Net throughput, equal average power (bit/s at measured data S:N; points.csv in
`docs/charts/interim-wgn/`):

| | ARDOP 1.0.2.9 | Mercury 1.9.23 | Data2G 0.5.1 | VARA HF 4.9.1 |
|---|---|---|---|---|
| Ceiling (50 KB) | 1,259 (21.9 dB) | 1,621 (25.5 dB) | 5,233 (29.4 dB) | 3,341 (25.8 dB) |
| 15-18 dB (50 KB) | 999 (15.4) | 834-949 (17.5-17.8) | 3,869 (17.5) | 2,803 (17.9) |
| about 13-14 dB | 499 (10.8, 5 KB) | 611 (12.6, 5 KB) | 1,916 (14.1, 5 KB) | 1,898 (13.4, 50 KB); 1,274 (5 KB) |
| about 7-9 dB (5 KB) | 206 (6.7) | 606 (7.7) | 1,611 (9.2) | 961 (9.1) |
| about 1-5 dB (5 KB) | 143 (3.1) | 186 (1.0) | 987 (5.3), 675 (1.3) | 582 (5.4), 262 (1.8) |
| about −3 dB (5 KB) | 69 (−2.9, 21/21) | 40 (−2.9, 4/10) | 325 (−2.7) | 135 (−3.5) |
| lowest delivering | −2.9 dB (nothing at −6.0) | −2.9 dB in spec | −13.9 dB (1/h) | −9.4 dB (2/h; nothing at −12.4) |
| failures | 6/328, 16QAM 15-18 dB | froze 8 of 16 long sessions | none | 1 byte lost, 1/320 |
| time to connect | 6-7 s | 8 s | 4-5 s | 8-9 s |

- **Speed: VARA second**, behind Data2G and ahead of ARDOP and Mercury everywhere from
  −3 to 26 dB. Against Data2G at the same S:N: about 64 % at the ceiling, 72 % at 15-18 dB,
  60 % at 9 dB, about 40-60 % at 1-5 dB and 40 % at −3 dB. Against ARDOP: about 2-3 × from
  9 dB to the ceiling, 2 × at −3 dB.
- **Robustness: VARA second** too: it delivers to −9.4 dB, about 6.5 dB further down than
  ARDOP and Mercury and about 2-4.5 dB short of Data2G (−11.5 dB at 4/h, −13.9 at 1/h).
- **Equal peak power.** VARA's fast modes (PAPR 11.7) move 8.7 dB left, its FSK modes
  (3.0) don't move. At the top Data2G's lead over VARA grows by about 2.4 dB; at the bottom
  VARA's FSK gains about 2.7 dB on Data2G's QPSK (5.7) but none on Data2G's own FSK cliff
  modes (3.1). VARA's line zig-zags in this view: at equal peak its PSK point at WGN 7 (−2.4 dB,
  582 bit/s) sits left of its FSK point at WGN −2 (−0.5 dB, 139 bit/s). VARA picks its speed by
  the S:N it sees, which a peak-limited transmitter changes; how it adapts there is not tested.
- All white-noise (WGN) results; fading (CCIR) channels are still to come.
