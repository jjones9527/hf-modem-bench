# Results log — Stage 4: ARDOP 1.0.3.3 development build

Part of the [results log](../results-log.md). All times UTC.

## Stage 4: ARDOP 1.0.3.3 development build, bring-up (19 Nov 2026)

`scripts/windows/hfbench_ardop_swap.ps1 -Build dev` (11:02 UTC) put the 1.0.3.3 build (sha256
8517bb90…cc9c0) into both Winlink installs; 1.0.2.9 is kept beside it as `ARDOP_Win.exe.1.0.2.9`
(`-Build release` puts it back). `ARDOP_Win TNC.ini` unchanged (DriveLevel 90 / 75), so the
settings are 1.0.2.9's. Station 2 now runs as VA3ZTF (its second Winlink callsign, set up for
VARA), so ARDOP calls VA3ZTF -> VA3ZTF; 1.0.2.9 ran VE3XZQ -> VA3ZTF. Recorders: listen-20261119-1103
(16 × 150 min) and txcrest-20261119-1103.jsonl (40 h).

**Two bench faults before the first good run (not modem results; folders kept on the bench):**
- `smoke-ardop133-setupfail`: both Winlinks were still in "Vara HF P2P" from the VARA tests and
  the chain didn't recover first, so ARDOP never started; station 2's Winlink then hung in VARA
  reconnects (11-s timeouts to the relay with no VARA behind it) and recovery couldn't read its
  windows. Both Winlinks force-closed, recovered into Ardop P2P. **Fixed:** `bench_chain.sh`
  recovers before its first campaign.
- `smoke-ardop133-noremote`: station 2's Ardop P2P window opened with an empty callsign box.
  Winlink keeps the callsign to call per session type and own callsign ("Ardop P2P Remote
  Callsign", "Vara P2P Remote Callsign" in that callsign's ini section), and VA3ZTF had never run
  ARDOP on station 2. **Fixed:** recovery sets it (`bench.set_remote_callsign`), with the session type.

**smoke-ardop133** (WGN 40, 3 × 50 KB, 12:08-12:25 UTC): **3/3 delivered, identical**, 1,282-1,293
bit/s per message, **1,063 bit/s net**, connect 4 s (1.0.2.9: 6-7 s; 1,259 net at its 21.9 dB ceiling).
- **A new waveform.** Station 1's debug log: data frames OFDM.2000.R35 (24), OFDM16.2000.R34.S (9),
  OFDM.2000.R12 (6), OFDM.2000.R12.G6.S (7), OFDM.500.R12.G6.S (2), plus new LAB-RELIABLE /
  LAB-OFDM-ACK / LAB-OFFER frames; data bursts about 11 s (68 bursts, 777 s). 1.0.2.9 used
  4PSK/8PSK/16QAM.2000 single-carrier frames of 1-4 s. Its audio code is new too ("split-audio-20261013"
  build, discontinuity recovery lines).
- **Level and crest at the same drive:** data average −15.2 dBFS digital (1.0.2.9 at WGN 40: −16.0),
  PAPR 9.1 dB at 0.01 % (1.0.2.9 16QAM: 10.5), so its peaks are no higher (−6.1 against −5.5 dBFS).
  Left at 1.0.2.9's drive; the 0.8 dB is on the measured S:N axis.

Full set started 12:27 UTC: sweep-ardop133-50k (WGN 40/22/17 × 3), sweep-ardop133-5k (17, 12, 7, 2,
0, −2, −5 × 3: 1.0.2.9's sweep, knee and low points in one; −10 left out), crest-ardop133.

### sweep-ardop133-50k results (19 Nov 2026, 12:27-20:22 UTC)

Blocked-random order, 10 × 50 KB per run, 2 -> 1. **84/86 delivered, all 84 attachments
identical, no corrupted message.** Net throughput by simulator setting (measured S:N not yet
computed; the S:N recorder's fourth block, 18:33-20:33, was lost in the power cut below, so runs
7-9 will take their setting's S:N from runs 1-6):

| WGN | Runs (net bit/s, delivered) | 1.0.2.9 (sweep-ardop-50k) |
|---|---|---|
| 40 | 1,110 (10/10), 1,110 (10/10), **1,009 (9/10, dnc)** | 1,251, 1,275, 1,251 (all 10/10) |
| 22 | 1,107 (10/10), 1,096 (10/10), **993 (5 delivered, dnc)** | 1,078, 958 (dnc), 834 (dnc); 2 corrupted |
| 17 | 1,041, 1,033, 1,048 (all 10/10) | 551 × 3, all time-boxed at 6/10 |

Per message (receiver) 1,117-1,199 bit/s median; connect 4-5 s (8 and 12 s once each).
About 12 % below 1.0.2.9 at WGN 40, level with its best run at WGN 22 and without its 16QAM
corruptions, and nearly twice its speed at WGN 17. Data frames at full speed are OFDM.2000.R35.E
of **26.4-26.7 s** (406 of them on the sender's log that day; the smoke run's 11-s average was
over all frame types).

**Both dnc runs: the sender's ARQ inactivity timeout during a repeated 26-s frame.** Run 0003
(WGN 40): station 1's capture logged `[Audio discontinuity] flags=0x1` at 15:05:04.925 and
`partial receive frame cleared` (`conservative reset missingFrames=0`) just as station 2 began a
26.7-s data frame; station 2 repeated it (15:05:36.9-15:06:03.6), station 1 decoded it (Quality
90) and acked at 15:06:03.998, but station 2 had declared `[SESSION FAILURE] ARQ inactivity
timeout` at 15:06:04.422, 60.8 s after its last ack; the ack arrived at 15:06:04.512. Run 0009
(WGN 22): the same, partial frame cleared 20:19:14.5, repeat done 20:20:13.3, timeout
20:20:14.2. With 26-s frames, one lost frame plus its repeat uses the whole 60-s allowance.
Station 1's discontinuities are periodic: 145 between 11:53 and 16:40 UTC, 123 of the intervals
109 s and 15 of 218 s, in sessions and out; 30 cleared a partial frame. Station 2 logged no
discontinuities but 405 `[Receive backlog] state=high` (about 500 ms). Not seen before because
1.0.2.9 doesn't log WASAPI flags. Reported to Phil privately with both stations' logs.

**Bench power cut, 20:33:55 UTC.** The PC (a Mac mini under Windows) lost power mid-way through
sweep-ardop133-5k-0001 (WGN 0): every log stops in the same second; Kernel-Power 41 and
EventLog 6008 at the 21:01 reboot, no bugcheck. That run is marked invalid. The tone check
afterwards (21:06) matched the earlier one (2 -> 1 −22.8, 1 -> 2 −23.4 dBFS; −0.2 / −0.3 dB vs
the reference at WGN 20). **ARDOP 1.0.3.3 testing stopped here** (operator, 19 Nov): Phil has
newer work, which will be tested instead; the 5 KB sweep and crest runs were not done. The dev
build is still installed in both Winlinks (`hfbench_ardop_swap.ps1 -Build release` restores 1.0.2.9).
