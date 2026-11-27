# Results log — Stage 2b: Data2G 0.5.1, white noise

Part of the [results log](../results-log.md). All times UTC.

## Stage 2b: Data2G 0.5.1 bring-up (17 Nov 2026)

**Version.** Both installs were 0.4.2 (3 Nov). The operator chose to update to **0.5.1**
(14 Nov; installer sha256 7aa03e27…ae6c over `C:\Program Files\Data2G`, portable zip
8c6ce0ba…47bf unpacked over `Data2G 2`; identical binaries, `data2g-host.exe` fd8d7edc…0d5c;
0.4.2 kept in `hfbench\data2g-0.4.2-*-backup`). Two reasons: 0.5.0 gives each copy its own
settings file (`--config`; in 0.4.2 every copy on the machine shares one registry store),
and adds low-S:N changes (coherent FSK detection, "nods").

**Setup.** `data2g-host` (headless) runs per station from `hfbench_start_data2g.ps1`, with
`--config hfbench\data2g\station<N>.conf`, logging stderr to `station<N>_host.log` (local
time; Data2G logs only to stderr). Station 1 VA3ZTF, ports 8300/8301, KISS 8100, C-Media;
station 2 VE3XZQ, 8310/8311, KISS 8110, "3- USB Audio Device"; 48 kHz; rig control off
(no PTT needed on the bench); CW ID off. Winlink unchanged ("Vara HF P2P", station 2 on the
relay, 8320 -> 8310). The runner's Data2G profile now has no TNC path, so recovery leaves
the host running (as for Mercury). Handshake: Winlink's `PUBLIC ON`, `CWID ON` and
`COMPRESSION ON` are accepted but not implemented; `BW2750`, `MYCALL`, `LISTEN ON` taken;
Data2G answers `REGISTERED`. **Data2G has no switch for its busy detector**; it holds new
calls while BUSY is lit. The tone check's tones were heard as a CW ID ("CW ID heard:
holding"), harmless.

**Drive level (D5).** Tone check 17 Nov 01:12 UTC: -0.2 / -0.3 dB vs the reference at
WGN 20, as before. `cal-data2g` (WGN 40, 3 × 50 KB 2 -> 1, `output_volume` 0,
listen-20261117-0114, `scripts/data2g_level.py` keyed by Data2G's own `TX` lines): station 2's
data bursts (w48-256l-r5/8, 12 s) arrived at -21.7 dBFS against the tone's -22.8, **+1.1 dB**;
its acks (ack-1f, 1 s) 2.3 dB hotter again (less crest). Station 1 sends almost only acks
one way (-20.3 dBFS; tone -23.4): with the same ack-data gap its data sits about **+0.8 dB**.
Both set to **`output_volume = -1.0`** (peak 1 dB below full scale). Equal average power is
set on the data bursts; acks run about 2 dB above the reference.

| Run | Setting | Result | Per message (receiver log) | Net | Notes |
|---|---|---|---|---|---|
| cal-data2g-0001 | WGN 40, vol 0 | completed 3/3, identical | 8,650-8,880 bit/s | 5,138 bit/s | Data2G's own S:N 23-26 dB, all data in w48-256l-r5/8, 0 % resends |
| smoke-data2g-0001 | WGN 18, vol -1 | **completed 10/10, identical** | 6,138-6,620 (median 6,486) | **4,291 bit/s** | one 13-min session, 0 % resends, 0 control lost |

For scale, Mercury 1.9.23 at WGN 18: 9/10 in 60 min, 947 bit/s per message, 839 net.

**The per-message goodput overstates Data2G.** Winlink's "Receiving" line (the window's
start) comes when the first data reaches it, i.e. at the end of Data2G's first 12-s burst;
ARDOP and Mercury bursts are 1-4 s, so their windows lose much less. In smoke-data2g messages
start every ~75 s and each takes 52 s by the window: 42 KB in 75 s is about 4,500 bit/s, which
matches Data2G's own stats lines (4,050-5,700 bit/s acked) and the net figure. In cal-data2g,
from the receiver's `FS Y` (it accepts the message) to "received" is 56 s for a 38-s window,
about 6,000 bit/s instead of 8,880. **Until the metric is settled, compare Data2G on net
throughput**, or on a window that starts at the receiver's `FS` line (open question for the
operator; recomputable for every past run from the Winlink logs).

Next: the plan's WGN sweep, `sweep-data2g-50k` (WGN 40/22/17 × 3) then `sweep-data2g-5k`
(17 … -10 × 3), started 02:02 UTC 17 Nov with listen-20261117-0202 (5 × 150 min).

### Data2G 0.5.1 WGN sweep results (17 Nov 2026, 02:02-10:20 UTC)

`sweep-data2g-50k` (9 runs) then `sweep-data2g-5k` (21 runs), unattended, relay holding,
`output_volume -1.0` (D5). **300 of 300 messages delivered, 300/300 attachments
byte-identical; no corruption, no stall, no failed session, no hang, no restart.**

Measured data S:N: `scripts/data2g_snr.py`, keyed by the sender's own `TX ... data` lines.
Noise is taken in the 2-min quiet gap after each run (the IONOS still at the run's
setting, nobody transmitting), because Data2G's traffic is too dense for the in-run
estimate at most settings. Where both exist they agree within 0.1 dB, except at WGN −10
(in-run 0.6 dB noisier: faint bursts the energy detector misses). A campaign's last run
uses the in-run noise, or the campaign's other runs at the same setting.

| measured data S:N | setting | payload | delivered | net throughput (3 runs) | main data modes |
|---|---|---|---|---|---|
| 29.4 dB (ceiling) | WGN 40 | 50 KB | 30/30 | **5,180-5,270 bit/s** | w48-256l-r5/8 |
| 21.3 dB | WGN 22 | 50 KB | 30/30 | 4,940-5,010 bit/s | w48-256l-r5/8 (95 %), w48-64l-r2/3 |
| 17.4 dB | WGN 17 | 50 KB | 30/30 | 3,855-3,895 bit/s | w48-64l-r7/12 (98 %) |
| 17.5 dB | WGN 17 | 5 KB | 30/30 | 2,440-2,470 bit/s | w48-64l-r7/12, r1/2 |
| 14.1 dB | WGN 12 | 5 KB | 30/30 | 1,860-2,020 bit/s | w48-16qam-r2/3, r1/2 |
| 9.2 dB | WGN 7 | 5 KB | 30/30 | 1,600-1,620 bit/s | w48-16qam-r1/2, r1/3 |
| 5.3 dB | WGN 2 | 5 KB | 30/30 | 986-989 bit/s | w48-qpsk-r1/2 |
| 1.3 dB | WGN −2 | 5 KB | 30/30 | 660-690 bit/s | w48-qpsk-r1/3 |
| −2.7 dB | WGN −5 | 5 KB | 30/30 | 324-326 bit/s | qpsk-r1/3 (narrow) |
| −3.5 dB | WGN −10 | 5 KB | 30/30 | 111 bit/s | fsk32r62-r1/2 |

- Runs repeat closely: net throughput within 2 % between replicates at most settings,
  S:N within 0.3 dB.
- **Against ARDOP 1.0.2.9 at equal measured S:N** (its summary above): at the ceiling
  5,200 vs 1,259 bit/s net; around 15-17 dB 3,870 (50 KB) vs 999 (at 15.4); about 9 dB
  1,610 vs 499 (at 10.8) and 206 (at 6.7); about 3 dB, ARDOP 143 bit/s (3.1 dB) while
  Data2G gives 986 at 5.3 and 675 at 1.3; at about −3 dB, ARDOP 69 bit/s (−2.9, time-boxed,
  21/21) vs Data2G 111-326 bit/s (−3.5 / −2.7, 10/10 every run).
- **Low S:N edge not reached.** WGN −10 is the bench's lowest setting, and Data2G
  delivered everything there. ARDOP failed by −6.0 dB. A cliff search lowering
  Data2G's own level at WGN −10 is running (`knee-data2g-v*`, operator, 17 Nov).
- **Measured S:N depends on Data2G's waveform, as for ARDOP.** WGN −5 and −10 measured
  only 0.8 dB apart: part is the IONOS's compression at the bottom of its range, part
  is the mode change to constant-envelope FSK at WGN −10, which carries more average
  power for the same peak (`output_volume` sets the peak). The acks (ack-1f) arrived
  2.3 dB above the OFDM data at the same setting (cal-data2g).
- **Per-message goodput is not usable for Data2G** (bring-up section): besides the late
  window start, at 5 KB Data2G often carries two messages in one burst, so the second
  is logged as received in the second it started (0-s window, no figure). Net throughput
  is the comparison until the metric is changed.
- At the same setting, Data2G's measured S:N is higher than Mercury's and ARDOP's
  (e.g. WGN 7: Data2G 9.2, ARDOP 3.1, Mercury 7.7; WGN 2: 5.3, −1.8, 1.0). ARDOP's PSK
  peak limits explain its part (above). The Data2G-Mercury gap at the low end (up to
  4 dB at WGN −10: −3.5 vs −9.9) is not explained yet; Mercury's figures are keyed by
  its PTT log, whose windows may hold silence. To check before the comparison charts.

### Bench faults found 17 Nov 2026: Windows system sounds, and WGN −10 out of spec

**Windows sounds reached the IONOS.** Windows' default playback device was station 2's
bench card ("Speakers (3- USB Audio Device)") with the system sound scheme on, so any
Windows or Winlink alert sound went into the IONOS on top of the modem. The operator saw
the Lvl meter spike over 1,300 mV p-p during knee-data2g-v4 (marked `invalid`). Fixed
17 Nov 12:35 UTC: default playback is now the Mac mini's own output (Speakers (Apple
Audio Device)) and the scheme is No Sounds (old settings in `hfbench\appevents-backup.reg`).
**Every run before then, every modem, could have had an alert sound mixed in.** Nothing in
the data points to one (every delivered attachment byte-identical, burst S:N tightly
grouped), so no result is withdrawn.

**WGN −10 puts the IONOS output at its limit, with any signal.** With nothing playing, the
microphone peaks rise with the setting (WGN 40, 17, 7, 2, 0, −2, −5, −10: station 1 −30.1,
−25.4, −19.9, −16.4, −15.9, −14.6, −13.2, −11.3 dBFS). Against the operator's meter
readings, red starts at about −11 dBFS at station 1's microphone: WGN −10's noise alone
sits just under it, and any signal on top goes into the red. The Lvl meter shows the
IONOS output (signal plus noise), not only the input. **WGN −10 is out of spec for every
modem** (ARDOP's no-connect, Mercury's 3/10, Data2G's 30/30 there): those points stay in
the tables, marked, and are left off the charts. WGN −5 has headroom (about −11.4 dBFS
with a signal at the reference). The Data2G cliff search therefore ran at WGN −5.

### Data2G 0.5.1 cliff search at WGN −5 (17-18 Nov 2026)

WGN −10 was out of spec and Data2G delivered 30/30 there, so its own level was lowered
instead (`--output-volume` on both stations, flags for the run only; the `.conf` files keep
the D5 level), IONOS fixed at WGN −5, 10 × 5 KB, two runs per step, relay holding, 60-min
time box. Measured S:N: `data2g_snr.py` (sender's TX lines; noise from the quiet gap after
each run). Transmitted PAPR: `tx_crest_log.py` (next section).

| Level | Measured data S:N | Data mode | PAPR | Delivered | Net | Batch rate |
|---|---|---|---|---|---|---|
| −1 dB (sweep, WGN −5) | −2.7 dB | qpsk-r1/3 (narrow) | 5.7 dB | 30/30 | 325 bit/s | 348 |
| −4 dB | −5.6 dB | qpsk-r1/5 | 5.6 | 20/20 | 201 | 212 |
| −7 dB | −4.5 dB | fsk32r62-r1/2 | 3.1 | 20/20 | 110 | 115 |
| −10 dB | −7.4 dB | fsk32r62-r1/2 | 3.1 | 18/20 (time box) | 88 | 100 |
| −13 dB | −11.5 dB | fsk8r50-r1/2 | 3.1 | 8/20 (time box) | 39 | 49 |
| −16 dB | −13.9 dB (−13.3, −14.5) | fsk16r25-r1/2 | 3.1 | 3/20 (time box) | 15 | 22 |

- Every delivered attachment in the cliff steps byte-identical (69/69); no corruption, no failed session, no hang.
  Data2G never stopped working: it got slower until a 5 KB message took about an hour.
  **Practical limit about −11 to −12 dB measured** (4 messages an hour); at the −16 dB step
  one message an hour.
- **Measured S:N depends on the mode** (as for ARDOP, results log 15 Nov): −7 dB measured
  higher than −4 dB because Data2G switched to constant-envelope FSK, which carries more
  average power for the same peak (`--output-volume` sets the peak).
- ARDOP 1.0.2.9 for comparison: 21/21 at −2.9 dB (69 bit/s), nothing at −6.0 dB.

### Transmitted crest factor (PAPR) for all three modems (17-18 Nov 2026)

Measured digitally at each station's sound-card output (WASAPI loopback, before the
Windows volume and the IONOS: no noise, no level change), `scripts/tx_crest_log.py`; needs
the `soundcard` package, installed on the bench with the operator's approval (17 Nov).
One `crest-<modem>` campaign per modem: one 3 × 5 KB run at each sweep setting, WGN 40
down to −5, at the modem's sweep level. PAPR = peak level exceeded by 0.01 % of a burst's
samples minus its mean power; a sine is 3.0 dB. Data frames (the sender):

| Setting | ARDOP 1.0.2.9 | Mercury 1.9.24 | Data2G 0.5.1 |
|---|---|---|---|
| WGN 40 | 10.5 dB (16QAM.2000) | 11.2 dB | 9.3 dB (w48 OFDM 256) |
| WGN 22 | 10.0 | 7.7 | 9.3 |
| WGN 17 | 10.3 (4PSK.2000) | 7.1 | 7.7 (w48 64) |
| WGN 12 | 8.6 | 7.1 | 7.1 (w48 16QAM) |
| WGN 7 | 6.8 (4PSK.500) | 7.1 | 6.9 |
| WGN 2 | 6.8 | 6.4 | 5.6 (narrow QPSK) |
| WGN −2 | 4.2 (4FSK) | 6.4 | 5.6 |
| WGN −5 | 4.3 | 3.1 | 5.7; its cliff-search FSK modes 3.1 |

Replies (station 1): ARDOP 4.9-6.6, Mercury 6.2, Data2G 5.5 dB. VARA's 2018 specification
gives 9 dB for its data and 6 dB for its acks, for comparison when it's measured.
- The operator's meter impression (ARDOP about 600 mV p-p, Mercury about 900, Data2G about
  1,100-1,300) came mostly from the modems' different **average** drive, not their crest:
  ARDOP's digital average was about 4 dB below Data2G's (−16.0 against −11.7 dBFS at WGN
  40), which is also why ARDOP measures a lower S:N at the same setting.
- The sweeps ran before the logger existed: each sweep run takes its modem's PAPR at the same
  setting from its crest campaign (`scripts/crest_by_setting.py`; a modem's modes depend on
  the channel), knee-ardop-5k's WGN 0 from WGN −2 (4FSK at both). Cliff runs: measured directly.
- Data2G's peak check at WGN 40 (`peak-data2g`, `scripts/peak_log.py` at the microphones,
  operator watching the meter) at the D5 level: data peaks about 950-1,100 mV p-p, no red.
  The sweeps at that level were not clipped.

### Reporting changes (D7, operator, 17 Nov 2026) and the comparison so far

- **Headline: net throughput** (connect to disconnect). Beside it the **transfer rate per
  proposal batch** (receiver's `FS` line to the batch's last message: Winlink proposes up
  to a few messages at once and Data2G carries a batch in the same bursts, so per-message
  windows meant nothing for it), and the **time to connect** (Data2G 4-5 s, ARDOP 6-7 s,
  Mercury 8 s; 20 s and more where a call was repeated). The older receiver window
  (`goodput_bps`) stays in messages.csv for comparison only.
- **Two views**: equal average power (as tested, D5) and **equal peak power**: x = measured
  S:N − (PAPR − 3 dB), where a peak-limited transmitter would put each modem.
- All campaigns recomputed on the bench with `--verify` (18 Nov): **1,076 of 1,076 delivered
  attachments byte-identical** across every campaign.
- Report fixes: one line per workload (50 KB solid, 5 KB dashed), a log-scale net chart,
  S:N readings keyed by a modem's own transmit log accepted from 10 bursts, runs whose
  session never closed (Mercury freezes) out of the throughput sums, WGN −10 off the charts.

Net throughput, equal average power (measured data S:N):

| | ARDOP 1.0.2.9 | Mercury 1.9.23 | Data2G 0.5.1 |
|---|---|---|---|
| Ceiling (50 KB) | 1,259 (21.9 dB) | 1,621 (25.5 dB) | 5,233 (29.4 dB) |
| 15-18 dB (50 KB) | 999 (15.4) | 834-949 (17.5-17.8) | 3,869 (17.5) |
| about 11-14 dB (5 KB) | 499 (10.8) | 611 (12.6) | 1,916 (14.1) |
| about 7-9 dB | 206 (6.7) | 606 (7.7) | 1,611 (9.2) |
| about 1-5 dB | 143 (3.1) | 186 (1.0) | 987 (5.3), 675 (1.3) |
| about −3 dB | 69 (−2.9, 21/21) | 40 (−2.9, 4/10) | 325 (−2.7) |
| lowest delivering | −2.9 dB (nothing at −6.0) | −2.9 dB in spec | −11.5 dB (4/h), −16 dB step 1/h |

In the equal-peak view Data2G's lead at the top narrows by about 1 dB against ARDOP and
widens against Mercury; at the bottom ARDOP's 4FSK and Mercury's −5 mode (3.1 dB) gain
1.4-2.6 dB on Data2G's QPSK points, while Data2G's own FSK cliff modes are sine-like too.
Data2G stays ahead everywhere. Mercury against ARDOP is mixed (Mercury faster at the
ceiling and 1-13 dB, ARDOP at 15-18 dB and −3 dB; Mercury's receiver froze in 8 of 16 long
sessions). All white-noise results.

### Phil's ARDOP 1.0.3.3 development build (18 Nov 2026)

ARSFI/ARDOP `main` at 48f2ae5 (Rev 1.0.3.3, 5 Nov; a private repository, Phil's code
only: the binary and source are not published, results name the commit). Built on the
bench into `hfbench\ardop-dev` after the in-box .NET Framework MSBuild couldn't (no 4.8
targeting pack, no SDK tools): Microsoft's Build Tools for Visual Studio 2022 installed
(18 Nov, operator-approved; .NET desktop build tools, 4.8 SDK and targeting pack;
installer signed by Microsoft). `ARDOP_Win.exe` 1.0.3.3, sha256 8517bb90…cc9c0, 0 warnings,
0 errors. To be tested after VARA HF and the interim report, before Aether HF and Modem73.
