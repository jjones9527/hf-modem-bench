# Results log — Stage 2: Mercury 1.9.23 / 1.9.24

Part of the [results log](../results-log.md). All times UTC.

## Stage 2: Mercury 1.9.23 bring-up (15 Nov 2026)

**Setup.** Two installs, `C:\Program Files\MercuryHF` (station 1) and `MercuryHF 2`
(station 2), both 1.9.23 (git 09f258f8), GUI `mercury-ui.exe` started by hand (desktop
icons "Mercury HF Modem" and "Mercury HF 2"). Each GUI reads `mercury.ini` from its own
folder and writes its settings back to it. Station 2's ini: `arq_tcp_base_port = 8310`,
`broadcast_tcp_port = 8110`, `ui_port = 10010`, `[store] enabled = false` (original
kept as `mercury.ini.orig`). Winlink Express: session type "Vara HF P2P", VARA TNC
port 8300 (station 1) / 8310 (station 2), auto launch off, "Log Vara commands" on.
Sound cards as for ARDOP (station 1 C-Media, station 2 USB Audio Device); Windows
levels unchanged from cal7 (speakers: C-Media 17% left only, USB Audio 50% right only;
microphones 35% / 75%, mono). Mercury writes the same signal to both output channels,
so the Windows balance routes it as for ARDOP; its capture-channel setting has no
effect on a mono microphone. `busy_detect = false` (default). Winlink's `CWID ON` is
rejected by Mercury (no Morse ID), harmless.

**Drive level (D5).** At `tx_gain_db = 0`, Mercury's bursts arrived 3.1 dB (2 -> 1) and
3.4 dB (1 -> 2) below the tone reference (listen-20261115-0248, WGN 40, ~28 bursts each,
matched to Mercury's own PTT log). Set to +3.0 (station 2) and +3.5 (station 1), the GUI's
0.5 dB steps: then -0.4 and 0.0 dB vs the reference (listen-20261115-0311). IONOS Lvl
about 550 mV p-p at 0 dB, 650-750 mV p-p after: no red. Against the tone (400 mV p-p at
the reference) that puts Mercury's peak-to-average about 6 dB above a sine's.

**Pre-checks (smoke-mercury).** Tone check -0.3 / -0.3 dB vs the reference at WGN 20;
16QAM 2 -> 1 22.8 dB MER at full level.

**smoke-mercury-0001 (WGN 18, Text_50KB, 2 -> 1): dnc, 1/10.** The first message was
delivered intact (6:20, 886 bit/s), but station 2's Winlink logged "P2P session
inactivity timeout" exactly 5:00 after "Sending" and disconnected; Mercury kept sending
until the receiver had it, so the sender never saw the receipt. The runner then
recovered the bench correctly with Mercury left running. Same failure in the manual
session at 02:53 (WGN 40, before the gain change, 6:27 send). Sends under 5 min
(03:14, 3:02 and 2:32 at the corrected level) completed normally.

**Relay trace (13:57-14:05 UTC).** A logging relay (`scripts/vara_relay.py`, station 2's
Winlink on 8320 -> Mercury 8310) shows Mercury follows the VARA host protocol:
Winlink handed all 42,527 bytes to Mercury in one write at 13:58:29; Mercury reported
`BUFFER 42527`, then `31027` (14:00:39), `19527` (14:02:16), `14927`, `12627` (14:03:14),
plus `PTT ON/OFF` around every transmission (44 lines), `BITRATE`, `SN` and `IAMALIVE`.
Winlink still sent `DISCONNECT` at 14:03:29, 5:00 after its last data-port write.
**Winlink's 5-minute P2P inactivity timer is not reset by BUFFER, PTT, BITRATE or SN
lines from the modem.** Winlink's own VARA command log does not record BUFFER or PTT
lines at all, so it can't show this; the relay can. 

**Same test with VARA HF 4.09.0001 (14:44-15:24 UTC, WGN 2, relay in front of station
2's VARA).** VARA hits the same timer. Winlink again wrote the whole message (42,573
bytes) in one go at 14:47:12, and VARA reported BUFFER every ~5 s (falling ~89 bytes per
frame, about 1,150 bytes/min). Winlink sent `DISCONNECT` at 14:52:12 and every 5 min
after. VARA answered only `OK` and kept the link (no `DISCONNECTED`), so Winlink stayed
in the session and just logged "P2P session inactivity timeout. Disconnecting." each
time. When the last byte was acknowledged (15:23:49, BUFFER 0) the receiver stored the
message intact and answered `FF`, but VARA then carried out the pending disconnect
(`DISCONNECTED` 15:23:51), so the `FF` never reached the sender: **station 2 has no
"Completed send" and the delivered message is still in its Outbox, as with Mercury.**

**Conclusion.** The 5-minute limit is Winlink Express's P2P inactivity timer, counted
from the host's last data-port write; BUFFER/PTT/BITRATE lines don't reset it. Any
VARA-protocol modem (VARA HF, Mercury, presumably Data2G) loses the session and the
sender's receipt on a send longer than 5 minutes, after delivering it. VARA only delays
the end until the current message is through; Mercury reports `DISCONNECTED` at once
(while still sending), which is wrong by its own TNC.md but makes no difference to the
outcome here. ARDOP isn't affected: 50 KB sends of 8-10 min ran in one session
(sweep-ardop-50k at 10.8 dB). No setting for the timer was found in Winlink's ini
files or documentation. How to handle it in the comparison is an open decision.

**Workaround: relay holds the timer's DISCONNECT (17:08-17:23 UTC, Mercury, WGN 18).**
The operator wants long sessions (performance measured over time, as with ARDOP), so
`vara_relay.py --hold-timeout-disconnect` answers a DISCONNECT with `OK` itself and
doesn't pass it on when the host has written nothing to the data port for >= 240 s and
the modem's last BUFFER was above zero; any other DISCONNECT is passed through. Test:
two 50 KB messages 2 -> 1 through the relay on station 2.
- 17:12:35 message 1 handed over; 17:17:35 Winlink's timer fired ("P2P session
  inactivity timeout. Disconnecting.") and the relay held it (Mercury BUFFER 12,632);
  17:19:02 received intact (6:20, 6,704 bytes/min); **17:19:23 station 2 logged
  "Completed send of message AY9TFXG6F1KU"** and message 2 started in the same session.
  Winlink carries on normally once the modem keeps the link.
- Message 2 did not finish, for a different reason: at 17:22:31 station 1's Winlink
  logged "Link Error - Received data stream not correct format. ByteIndex=58923" and
  aborted. The partial (16,250 bytes) matches the original for its first 16,238 bytes;
  the **last 6 bytes Mercury handed to Winlink were wrong**. Unrelated to the relay (on
  the sending station only, data passed through unchanged; message 2's timer would not
  have fired until 17:24:36). **Not counted as a Mercury result:** at 17:40 three
  `MercuryHF 2\mercury-ui.exe` processes were found running on station 2's sound card
  (one left from 14 Nov 21:35, still busy after its window was closed for the VARA
  test, 5.4 h CPU; two started 30 s apart at 12:09). Overlapping instances can garble
  the audio. All three were stopped; from now on the bench check counts Mercury
  processes (exactly one per station) before every run.
- All delivered attachments checked byte-identical against the payload: AY9TFXG6F1KU,
  5Q6A8Q2MUYKM (VARA), 1LXNP3DKWQQB, 4VB3S9EAD6GZ, 7OTX6QPRUVDY.

### smoke-mercury-r: Mercury 1.9.23 through the bench relay (15 Nov 2026, 17:34-18:38 UTC)

Same as smoke-mercury (WGN 18, Text_50KB x 10, one-way 2 -> 1, 60-min time box) with
station 2's Winlink on the relay (8320 -> 8310, holding the 5-min timer's DISCONNECT).
Exactly one Mercury process per station (checked; the start script now refuses
otherwise). Pre-checks: tone -0.2 / -0.3 dB vs the reference; 16QAM 2 -> 1 22.6-23.1 dB.

| item | value |
|---|---|
| outcome | **timeboxed, 9/10 delivered** in one session (the 10th not started at 60 min) |
| failures | 0 corrupted, 0 stalled; **9/9 attachments byte-identical** |
| sender | 9 x "Completed send"; Winlink's timer fired 9 times, all 9 held by the relay |
| goodput per message | median **947 bit/s** (812-1,054) |
| net throughput | **839 bit/s** over the 60-min session |
| measured data S:N | **18.2 dB** (234 bursts, energy-keyed; 18.7 dB from bursts matched to Mercury's PTT log) |
| Mercury level | +0.5 dB (2 -> 1) / -0.4 dB (1 -> 2) vs the tone reference |

For scale, ARDOP 1.0.2.9 with Text_50KB gave 1,259 bit/s at 15.4 dB and 1,548 bit/s at
21.9 dB. Mercury's sweep will give the curve; one point is not a comparison.

The run ended on the time box: the runner pressed Abort, recovery cleared the one
remaining Outbox message, restarted both Winlinks and reopened both sessions with the
Mercury GUIs left running. Mercury is ready for the WGN sweep with the relay in place.

### sweep-mercury-50k: two bench faults (15-16 Nov 2026)

- **0003 (WGN 22, 20:48 UTC): relay rule gap.** Winlink's 5-min timer fired at
  20:59:02.678, 0.6 s after Mercury reported BUFFER 0 (message sent, receipt not yet
  back). The relay then held only while BUFFER > 0, so it passed the DISCONNECT and the
  session ended after 1 delivered message (`dnc`). Fixed: the relay now holds any
  DISCONNECT after >= 240 s of host data-port silence (Abort sends `ABORT`, never held;
  a real end of session comes seconds after the host's FQ). Marked `invalid`, re-run.
  WGN 22 is the setting where a 50 KB message takes almost exactly 5 minutes.
- **0007 (WGN 22, from 23:41 UTC): station 1's Mercury froze.** At 00:10:57 UTC its
  engine log stopped mid-reception and its CPU went idle (0.2 s per 5 s, against
  2.5 s for station 2), with no crash or error; Windows still showed it responding.
  It had been running about 7 h (started 12:09 local). The operator noticed the
  waterfall had stopped. Campaign stopped by hand, run marked `invalid`; station 1's
  Mercury restarted (operator), relay restarted with the fixed rule, bench recovered,
  sweep resumed 00:17 UTC. **A Mercury stability finding, not counted as a
  link result.** From now on a watcher alerts if either Mercury log is quiet for
  more than 3 min during a session.
- **0007 again, twice more (16 Nov): station 1's Mercury froze both times.** 02:02:33 UTC
  (37 min into the session; Mercury up 1.8 h) and 12:24:23 UTC (44 min in; up 0.8 h).
  Same signature each time: the last log lines are a burst of received frames
  (`car_rx`), then nothing; CPU near idle (0.27 s per 5 s against 3.0 s for station
  2). The frozen copy's audio capture kept running: its log later filled with "[WRN]
  [audio-cap] Buffer full in capture buffer!" at about 100 lines/s until it was
  stopped, so the processing side hung, not the audio input. All three freezes were at
  the receiving station (direct connection to Winlink, no relay) and in WGN 22 runs,
  where a 50 KB message takes about 5 min. The repeat of 0003 (WGN 22) completed 10/10
  in between. Each run was marked `invalid`; station 1's Mercury was restarted
  (16 Nov 12:28 UTC by `hfbench_restart_mercury.ps1`, operator-approved for hangs), the
  bench recovered and the sweep resumed.
- **0007, fourth attempt (16 Nov 12:33 UTC): station 1's Mercury froze again**, about
  12:41:48 UTC, 8 min into the session, 1 message delivered (CPU 0.23 s per 5 s; Mercury
  up 0.25 h). By the operator's decision this attempt is recorded as **`dnc`, a Mercury
  failure, and not retried**; WGN 22 is reported from 0003 plus this attempt, with the
  freezes stated. Station 1's Mercury restarted by script (12:46:55), bench recovered,
  0008 and 0009 started 12:48. Freezes so far: 4, all on the receiving station, all in
  run 0007 at WGN 22.
- **0008 (WGN 22, from 12:50 UTC): fifth freeze.** Station 1's Mercury stopped at
  13:30:58 UTC, about 41 min into the session, after 6 messages delivered, with the same
  signature (`car_rx bytes=2300` ×3 in one millisecond, then nothing; CPU 0.33 s per 5 s).
  Recorded `dnc` as a Mercury failure and not retried, as agreed for 0007. Mercury
  restarted by script (13:35:10), bench recovered, 0009 (WGN 40) started 13:36. **At
  WGN 22 Mercury froze in 5 of 7 sessions; none of the 5 other sessions in the sweep
  froze.** Totals so far: 60/63 messages delivered, 60/60 attachments identical.
- **0009 (WGN 40, from 13:38 UTC): sixth freeze, the first away from WGN 22.**
  Station 1's Mercury stopped at 13:54:35 UTC, 16 min into the session, after 4
  messages, again right after a burst of `car_rx bytes=2300` frames (six within 62 ms);
  CPU 0.23 s per 5 s. Recorded `dnc` as a Mercury failure, not retried. Mercury restarted
  by script (13:58:45), bench recovered.
- **sweep-mercury-50k final (16 Nov):** 9 runs, 13 sessions. **Mercury's receiver froze
  in 6 of 13 sessions**: 5 of 7 at WGN 22 (one of the other two was ended early by the
  relay bug), 1 of 3 at WGN 40, 0 of 3 at WGN 17. 64/68 messages delivered; 64/64 attachments
  identical; failures: 1 corrupted (caught by Winlink, WGN 40), 3 lost to freezes.
  `sweep-mercury-5k` started 17:13 UTC.
- **sweep-mercury-5k trimmed (16 Nov, operator decision):** with the receiver freezing
  in about half of long sessions, three replicates mostly re-measure the freeze. One
  run per setting: WGN 12 and 17 (done, 10/10 each), −10 (running), 2, −5, 7, −2. The
  bench's run sheet holds those 7 rows (`runsheet-full.csv` keeps the 21). After the
  sweep: Data2G bring-up; Mercury 1.9.24 later as a short re-test of key points.
- **0005 (WGN 40): 6/10, `dnc`, a real result.** Station 1's Winlink logged "Link
  Error - Received data stream not correct format. ByteIndex=271584" at 22:31:04:
  corrupted data from Mercury, caught by Winlink, at the bench's best S:N.

### sweep-mercury-5k results (16 Nov 2026, 17:13-21:46 UTC, trimmed: one run per setting)

`hfbench results --verify`: **50/50 delivered, 50/50 attachments identical, no
corruption, no freeze** (7 sessions, 245 min). Goodput is the median per message
(receiver side); net includes session overhead. Measured data S:N is from
`scripts/mercury_snr.py` (recordings listen-20261116-1713-1/-2, keyed by station 2's
PTT log; `snr.csv`).

| Run | WGN | Measured S:N | Outcome | Delivered | Goodput | Net |
|---|---|---|---|---|---|---|
| 0002 | 17 | 17.4 dB | completed | 10/10 | 810 bit/s | 557 bit/s |
| 0001 | 12 | 12.6 | completed | 10/10 | 821 | 611 |
| 0012 | 7 | 7.7 | completed | 10/10 | 926 | 606 |
| 0004 | 2 | 1.0 | completed | 10/10 | 216 | 186 |
| 0013 | −2 | −2.9 | timeboxed | 4/10 | 50 | 40 |
| 0007 | −5 | **−2.3** | timeboxed | 3/10 | 40 | 30 |
| 0003 | −10 | −9.9 | timeboxed | 3/10 | 37 | 30 |

**Unexplained: WGN −5 measured −2.3 dB, above WGN −2's −2.9 dB.**
- IONOS acknowledged `WGN:-5`, and both recording blocks give the same figure
  (−2.2 / −2.3 dB), so it isn't the split between recordings.
- The noise was 1.6 dB higher than at WGN −2, as expected. But Mercury's signal was
  2.2 dB stronger, likely a different, higher-power mode. To check against Mercury's
  mode log before WGN −5 is plotted.

- From 7 dB up, 5 KB messages run at 800-930 bit/s, below the 50 KB rate at the same
  setting (961 at WGN 17), because each message is short against the session's fixed
  handshakes.
- **Mercury kept delivering, byte-perfect, down to WGN −10**, at 37-50 bit/s: 3-4
  messages an hour, each taking 15-36 min. On the same IONOS settings ARDOP 1.0.2.9
  delivered nothing at WGN −5 (−6.0 dB measured) and didn't connect below. At WGN −2
  (−2.9 dB measured for both modems), though, ARDOP was faster: 91 bit/s, every message
  in time, against Mercury's 50 bit/s and 4 messages in the hour. The
  comparison on measured S:N waits for the S:N analysis, since Mercury's burst power
  varies with its mode.
- Each of those slow messages had Winlink's timer DISCONNECT every 300 s, up to six
  per message, all held by the relay (next section).

### Winlink's timer DISCONNECT in the relay logs, for Mercury PR #581 (16 Nov 2026)

The developers opened draft PR #581: an opt-in `[tnc] absorb_idle_disconnect_s` that
answers the first timer DISCONNECT of a session with OK, if bytes are still queued
(`BUFFER` > 0) and the host has been idle that long. Across two days of Mercury relay
logs (`relay-20261115-1250`, `-1708`, `relay-20261116-0015`), there were 112
DISCONNECTs:
- **Timer DISCONNECTs (106)** all came 300 s or more after the host's last data write.
- **Real ends (6)** all came at most 4.1 s after it. So idle time alone separates them.
- **Winlink repeats the DISCONNECT every 300 s for as long as a message takes**:
  300, 600, 900, 1201, 1501, 1801 s during one 5 KB message at WGN −10. VARA HF
  (`relay-20261115-1439`) did the same: 300, 600 … 2101 s.
- **The timer restarts with each data write**, so every message over 5 minutes gets
  one. A 50 KB session at WGN 17-22 had up to 9 (one per message).
- **Three came with BUFFER 0** (data sent, the receiver's answer not back yet):
  15 Nov 20:59:02, 16 Nov 01:31:00 and 01:36:53. The first, passed on by the relay's
  first rule, ended that session (sweep-mercury-50k-0003, invalid).
- **What followed the 104 held ones:**
  - 72: the next message;
  - 23: another timer DISCONNECT in the same message;
  - 6: sessions where the receiver had already frozen;
  - 3: time-boxed sessions.

So, as written, the PR would end a session at its second long message, at the second
DISCONNECT of a message over 10 minutes, and at a DISCONNECT with BUFFER 0. Drafted as
a comment on #581, with a suggestion to decide on idle time alone, every time. The
tests are in test-plan.md ("Mercury 1.9.24 and PR #581"). The branch's engine was
built locally from 7dd5c40 (MinGW GCC 16.2, `mercury.exe` sha256 cafa4f89…84f),
because the Windows GUI has the engine built in and CI keeps no Windows build.

### PR #581 tested on the bench (16 Nov 2026, 22:43-23:20 UTC)

Mercury 1.9.24 installed first (results log above; after a PC restart every sound-card
endpoint had a new Windows ID, so both `mercury.ini` were updated; Windows levels
unchanged). Station 2 (sender) ran the branch's standalone engine (7dd5c40, MinGW
build, sha256 cafa4f89…84f) with `[tnc] absorb_idle_disconnect_s = 240`; station 1
the 1.9.24 GUI; relay logging only (`relay-20261116-2236.log`).

| Campaign | Test | Result |
|---|---|---|
| pr581-short | 3 × 5 KB, WGN 40: normal end (Q3) | completed 3/3, identical; DISCONNECT 4 s after the last write passed on, closed 11 s later |
| pr581-50k | 10 × 50 KB, WGN 17: carry on after an absorb (Q1) | **dnc 2/10.** Message 1's timer DISCONNECT absorbed and Winlink sent message 2; message 2's DISCONNECT (the session's second) ended the session after a 103-s drain. Message 2 reached station 1 but stayed in station 2's Outbox |
| pr581-100k | 3 × 100 KB, WGN 17: message over 10 min (Q2) | **dnc 0/3.** Absorbed at 300 s; Winlink's second DISCONNECT at 600 s ended the session; partial file at station 1 |

So the developer's three questions are answered yes, yes, yes, and the once-per-session
absorb still loses multi-message and long sessions, as the code predicted. No freeze on
station 1 (1.9.24) in about 30 min of sessions. Reported on #581.

### retest-mercury-1924: the receiver freeze on Mercury 1.9.24 (16-17 Nov 2026, 23:37-00:55 UTC)

Both stations on the 1.9.24 release GUI (git 1b13fab1, `mercury-ui.exe`, engine built
in), relay holding (D6, `relay-20261116-2333.log`), 10 × Text_50KB one-way 2 → 1,
60-min time box. Run sheet: WGN 40 and 22, three each (6 runs). **Stopping rule
(operator, 16 Nov): stop at 3 receiver freezes. The operator stopped the test after
the second, and the 1.9.24 question is answered.**

| Run | Setting | Result | Delivered | Notes |
|---|---|---|---|---|
| 0001 | WGN 40 | completed | 10/10 | goodput median 2,097 bit/s, net 1,738 bit/s |
| 0002 | WGN 40 | **dnc, freeze 1** | 6/10 | station 1's log stops 00:36:56 UTC, 23 min into the session, Mercury up 2.0 h (`+7301 s`), `rx_total` 287,729 |
| 0003 | WGN 22 | **dnc, freeze 2** | 0/10 | log stops 00:49:32 UTC, 3 min into the session, **6.7 min after the restart** (`+399.6 s`), `rx_total` 19,270 |

- Same signature as all six 1.9.23 freezes: the last lines are three
  `car_rx bytes=2300` frames logged in the same millisecond, then nothing. CPU
  0.16-0.27 s per 5 s against 1.45-2.38 s for station 2. Windows says it is responding.
  Station 2 logged "nothing from the peer in 240 s with data in flight, link lost".
  No ERR or WRN before either freeze. The 2-6 min before each restart
  showed no "Buffer full in capture buffer" lines (1.9.23 logged them later).
- That burst is not a clean trigger: station 1 logged five other three-frame
  2,300-byte bursts on 1.9.24 tonight without freezing.
- All 16 delivered attachments are byte-identical (`results --verify`).
- **S:N not measured for this campaign.** The freeze script stopped every
  `hfbench.exe` process to stop the runner, and the S:N recorder is one too
  (`listen-20261116-2238`, killed 00:42:47 before its first block was written, so the
  PR #581 window is lost too). From sweep-mercury-50k at the same Windows levels: WGN 40 ≈
  25.5 dB, WGN 22 ≈ 17.5 dB. Fixed for later: stop only the `hfbench_pilot` task's runner.
- With 1.9.23 and 1.9.24 together, **the receiver froze in 8 of 16 long Mercury sessions**
  (50 KB at WGN 22 and 40). The PR #581 sessions and the 5 KB sweep (short sessions, or
  station 1 receiving little) had no freeze. Reported on #579.
- Install note for the developers: the Windows installer overwrites `mercury.ini`
  (installer.iss `[Files]` has `ignoreversion` and no `onlyifdoesntexist`), so an
  update resets a station's settings (ports, sound card).
