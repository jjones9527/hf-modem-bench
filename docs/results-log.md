# Results log

A running record of every campaign: what was run, what happened, and what we
learned from it. Each entry is written when the run's logs have been checked.
This file is the lab notebook. The numbers in the final report are computed
again from the raw files.

**Raw data.** `scripts/archive-bench.sh` copies everything from the bench
machine into `logs/archive/` (gitignored). That covers each campaign's run sheet,
events, manifest and console output, the S:N recordings (`listen-*.json`), the
tone checks, and both stations' Winlink and ARDOP logs. Run it after every
campaign. All times are UTC.

**Stations.** Station 1 is VA3ZTF (`C:\RMS Express`) and station 2 is VE3XZQ
(`C:\RMS Express 2`). Station 2 always places the call. Adapters: until 11 Nov
station 1 used the Sabrent and station 2 the Syba; **from wgn25a (12 Nov) on they are
swapped** (station 1 Syba/C-Media, station 2 Sabrent), for every modem since.

**Workload.** Until 12 Nov: the Text_50KB set (sha256 `3ec10a0b…279f9`), 5 messages
from each station, each with one 51,200-byte attachment (about 42,100 bytes on the
wire). **From 13 Nov (oneway28 on): one way, 10 messages from station 2 to station 1,**
Text_50KB at 10 dB and above and Text_5KB (`85741279…384d4`) below, with a 60-min time
box per run.

**Goodput.** Compressed (FC EM) bytes × 8 divided by the message's transfer time.
Until 13 Nov from the sender's Winlink log; **from 13 Nov from the receiver's**, which
excludes the ~20 s handover and reads about 10% higher (test-plan.md).

**VARA-protocol modems** (Mercury from 15 Nov) run with station 2's Winlink behind the
bench relay, which holds Winlink Express's 5-min P2P inactivity DISCONNECT (D6).

---

## Bench calibration (10–11 Nov 2026)

See [bench-setup.md](bench-setup.md). Tone check at WGN 20: transmit mismatch
−1.1 dB, receive mismatch −0.7 dB, and the transmit level is +1.6 / +2.7 dB
against the IONOS reference. ARDOP DriveLevel is 90 on both stations.

**True S:N at WGN 20** (`hfbench audio listen` during the runs):

| recording | covers | 1→2 data | 2→1 data | 1→2 control | 2→1 control |
|---|---|---|---|---|---|
| listen-20261111-0203 | pilot01-0001 | 14.1 dB (435 frames) | 14.2 dB (284) | 19.1 dB | 18.4 dB |
| listen-20261111-1135 | pilot01-0002 | 14.1 dB (177) | 14.2 dB (117) | 19.2 dB | 18.1 dB |
| listen-20261111-2134 | pilot01-0003 | 14.1 dB (178) | 14.2 dB (110) | 19.4 dB | 18.3 dB |

(The 2134 recording was cut short at 22:15, after 0003 had ended, when the next
recording's start replaced its scheduled task. The raw data had already been
saved, and the table row was computed from it with `hfbench audio listen-report`.)

The S:N of ARDOP's 2000 Hz data frames is about 6 dB below the IONOS setting,
and the two directions differ by only 0.2 dB.

---

## pilot01: ARDOP 1.0.2.9, WGN 20, no impairment, 3 replicates

Purpose: prove the automated pipeline and see the run-to-run spread.

| run | start | outcome | delivered | 2→1 goodput (8PSK) | 1→2 goodput (16QAM) | ended by |
|---|---|---|---|---|---|---|
| 0001 | 02:09:19 | completed | 10/10, 70.0 min | 1,191–1,271 bit/s | 645–688 bit/s | normal end |
| 0002 | 11:37:47 | dnc | 3/10, 29.5 min | 1,126, 1,213 bit/s | 656 bit/s | station 2: *Link Error – Unable to decompress received binary compressed message* (12:06:13), receiving station 1's file **2/5** |
| 0003 | 21:38:55 | dnc | 3/10, 28.7 min | 1,243, 1,282 bit/s | 662 bit/s | station 2: *Link Error – Checksum error. Failed to assemble correct binary image* (22:06:37), receiving station 1's file **2/5** |

ARDOP behaviour, from the TNC debug logs:

| run | sender | modes reached | data ACK / NAK received | receiver's avg quality |
|---|---|---|---|---|
| 0001 | station 1 | 16QAM.2000 (up at 02:15:45 after 6 ACKs; one shift down and back up at 02:46–02:47) | 233 / 201 | about 38 at 16QAM, about 74 at 8PSK before the shift |
| 0001 | station 2 | 8PSK.2000 (never shifted up) | 271 / 5 | about 71 |
| 0002 | station 1 | 16QAM.2000 | 94 / 79 | |
| 0002 | station 2 | 8PSK.2000 | 113 / 2 | |
| 0003 | station 1 | 16QAM.2000 (one shift down and back up) | 94 / 76 | |
| 0003 | station 2 | 8PSK.2000 | 111 / 0 | |

Message order in each direction (station 1's file numbers, sent at 16QAM): in
0001 the order was 4, 2, 3, 1, 5 and all were delivered. In 0002 file 4 was
delivered and file 2 failed. In 0003 file 4 was delivered and file 2 failed.

**Findings:**
1. The automation worked end to end in all three runs, with no operator action
   during a run.
2. ARDOP's mode choice is the same every time and doesn't depend on S:N.
   Station 1 → 2 shifts up to 16QAM and about 45% of its frames are rejected;
   station 2 → 1 stays at 8PSK and almost none are. The true S:N is the same in
   both directions. The receiver's quality score for 8PSK sits right at the
   threshold for shifting up (about 74 vs about 71).
3. There was **data corruption at 16QAM**. Twice, every ARDOP frame of a message
   passed and was acknowledged, but the reassembled B2F message was corrupt,
   Winlink dropped the link, and the run did not complete. Both failures were
   the same payload file (station 1's 2/5), which was delivered in 0001. With
   only two events this may be a coincidence (about 1 in 5).
   An earlier session on 11 Nov (00:31, before pilot01) also shifted station
   1 → 2 up to 16QAM and ended with *Received data stream not correct format,
   ByteIndex=19420*.
4. The 8PSK direction delivered 13 of 13 messages without error.

Operational notes: after a link error, delete any leftover Outbox messages and
restart both Winlink instances. `--auto-continue` takes a number of seconds. Without
it the runner waits for Enter between runs, which stopped 0003 the first time.

---

## swap01: as pilot01, Y cables swapped between the USB adapters

Started 11 Nov 2026 at 22:15. The two Y cables were swapped at the USB adapters,
and each station kept the same IONOS channel (the left or right side). The tone
check after the swap read the same as before: transmit −1.1 dB, receive −0.7 dB,
and +1.6 / +2.7 dB against the reference.

Question: does the station 1 → 2 16QAM shift, and the corruption, follow the
cables?

| run | start | outcome | delivered | 2→1 goodput | 1→2 goodput | ended by |
|---|---|---|---|---|---|---|
| 0001 | 22:17:56 | dnc | 7/10, 56.8 min | 1,136–1,273 bit/s (4 msgs) | 655–677 bit/s (3 msgs) | station 2: *Link Error – Checksum error. Failed to assemble correct binary image* (23:13:40), receiving station 1's file **1/5** |
| 0002 | not run | | | | | the runner refused to start because station 1's Outbox still held 2 messages from 0001 |

Before 0001, the runner found and quarantined one stale `Partials\*.bin` left
over from the pilot01-0003 failure.

Station 1 shifted up from 8PSK to 16QAM at 22:23:56 and again at 22:40:50, after a
shift down. Station 2 stayed at 8PSK. Station 1's files were sent in the order
4, 2, 3, 1. Files 4, 2 and 3 were delivered, including the file 2/5 that failed in
pilot01-0002 and -0003, and file 1 failed.

**Findings:**
1. The cables don't decide the direction. With the cables swapped, station
   1 → 2 still shifted up to 16QAM and station 2 → 1 still stayed at 8PSK. What
   remains is the USB adapter or the IONOS channel (left or right).
2. The corruption doesn't depend on the file. A third file-level corruption
   happened at 16QAM, on a different file (1/5). File 2/5 was delivered this time.

**Running totals at WGN 20, 11 Nov** (pilot01 + swap01):

| mode (direction) | messages attempted | delivered | corrupted (link error) |
|---|---|---|---|
| 16QAM.2000 (1→2) | 13 | 10 | 3 |
| 8PSK.2000 (2→1) | 13 | 13 | 0 |

Each corrupted message arrived in full and every ARDOP frame passed before
Winlink rejected it. A 16-bit frame CRC failing to catch errors would explain
far fewer than 3 events in 13 messages, even with about 45% of frames
rejected. That points to ARDOP's ARQ or frame reassembly, for example a
repeated or reused frame being accepted, rather than to channel errors that get
past the CRC. This is only a hypothesis; the debug logs around each event are in
the archive.

---

## swap02: IONOS channels swapped

Started 11 Nov 2026 at 23:40. The cables are as in swap01. In Windows, each
USB device now outputs on the other side:

| | station 1 (Sabrent, "USB Audio Device") | station 2 (Syba, "C-Media USB Audio Device") |
|---|---|---|
| Windows playback balance | L 0 / R 100 | L 90 / R 0 |
| IONOS channel | CH1 | CH2 |
| IONOS CH IN | 50 | 2 |

The first tone check after the swap, with the gains simply exchanged
(CH1 IN 20, CH2 IN 1), had both stations about 6 dB low: transmit −4.9 / −3.1 dB
against the reference, and a receive level of −28 dBFS. Raising each gain one
step (20 → 50, 1 → 2) restored them:

| tone check at WGN 20 | station 1 vs reference | station 2 vs reference | transmit mismatch | receive mismatch | receive level |
|---|---|---|---|---|---|
| pilot01 / swap01 | +1.6 dB | +2.7 dB | −1.1 dB | −0.7 dB | about −21 dBFS |
| swap02 | +2.8 dB | +2.6 dB | +0.3 dB | −0.7 dB | about −21 dBFS |

The saved tone check is `runs/swap02/levels-tonecheck.json` in the archive.

Swapping the channels needed one more gain step on both channels, so the
IONOS's left and right inputs aren't interchangeable at the same gain setting.
Record this as part of the bench setup.

Question: does the 16QAM direction follow the IONOS channel (it would become
station 2 → 1) or the USB adapter (it would stay station 1 → 2)?

| run | start | outcome | delivered | 2→1 goodput | 1→2 goodput | ended by |
|---|---|---|---|---|---|---|
| 0001 | 23:42:42 | dnc | 1/10, 14.5 min | 1,111 bit/s (1 msg) | none | station 2: *Link Error – Checksum error. Failed to assemble correct binary image* (23:56:10), on station 1's **first** message (G2W86PLFK7LA), sent at 16QAM |
| 0002 | not run | | | | | the runner refused to start because station 1's Outbox still held 5 messages from 0001 |

Before 0001, the runner quarantined one stale `Partials\*.bin` from swap01.

ARDOP: station 1 shifted 4PSK.500 → … → 8PSK.2000 → 16QAM.2000 as before. The
receiver's average quality at 8PSK was 72–73 before the shift, and 38 at 16QAM.
It got 50 data ACKs and 27 NAKs. Station 2 reached 8PSK.2000 and stayed there
(average quality 68–69, 60 ACKs and 2 NAKs).

**Findings:**
1. The IONOS channel doesn't decide the direction. With the channels swapped,
   station 1 → 2 still shifted up to 16QAM. Together with swap01, the cables and
   the IONOS channels are ruled out. The ARDOP settings are identical on both
   stations: a sorted diff of the two `ARDOP_Win TNC.ini` files shows only the
   callsign, the sound devices, the TCP port and the window position. What's
   left is the audio hardware path, the Sabrent DAC → (IONOS) → Syba ADC versus
   the reverse.
2. That path is the *cleaner* one: the receiver reports about 72–74 quality at
   8PSK, against 68–71 in the other direction. That's what pushes ARDOP over its
   threshold for shifting up to 16QAM. The hardware only decides which
   direction crosses the threshold. The slowdown and the corruption come from
   ARDOP's behaviour at 16QAM near 14 dB true S:N.
3. A fourth corruption, this time on the first 16QAM message.

**Running totals at WGN 20, 11 Nov** (pilot01 + swap01 + swap02):

| mode | messages attempted | delivered | corrupted (link error) |
|---|---|---|---|
| 16QAM.2000 | 14 | 10 | 4 |
| 8PSK.2000 | 14 | 14 | 0 |

---

## wgn25a: WGN 25, USB adapters swapped between the ARDOP instances

Started 12 Nov 2026 at 11:11. `scripts/windows/swap_ardop_devices.ps1` swapped
the `CaptureDevice` and `PlaybackDevice` lines in the two `ARDOP_Win TNC.ini`
files and nothing else (verified by diffing against the `.bak` copies). Station 1
(VA3ZTF) now uses the **Syba** (C-Media) and station 2 (VE3XZQ) uses the
**Sabrent**. The cabling, the Windows balance and the IONOS gains are as in
swap02; they go with the devices.

Tone check at WGN 20 after the swap: station 1 +2.6 dB, station 2 +2.9 dB
against the reference, transmit mismatch −0.3 dB, receive mismatch +0.7 dB. This
is the mirror image of swap02, as expected.

Two changes at once, the device swap and S:N 25, are deliberate: the first
question is whether 16QAM is clean at about 19 dB true S:N. If it is, WGN 20 is
run next with the devices still swapped, to see which way the 16QAM direction
goes.

| run | start | outcome | delivered | 2→1 goodput | 1→2 goodput | modes | ended by |
|---|---|---|---|---|---|---|---|
| 0001 | 11:14:36 | completed | 10/10, 43.3 min | 1,477–1,534 bit/s | 1,302–1,407 bit/s | both 16QAM.2000 from the first message | normal end |
| 0002 | 12:02:32 | dnc | 6/10, 30.6 min | 1,409–1,519 bit/s (3 msgs) | 1,225–1,399 bit/s (3 msgs) | both 16QAM.2000 | station 1: *Link Error – Checksum error. Failed to assemble correct binary image* (12:33:07), receiving station 2's 4th message (DBUE4FWNCUQH) |

The failed message: station 2's TNC sent 42 data frames and each was ACKed on the
first try (0 NAKs, no repeats). Station 1's TNC decoded all 42 as PASS, at a
quality of 22–25. The reassembled B2F message still failed Winlink's checksum.
Across the whole of 0002, station 2 as sender got 183 ACKs and **0 NAKs**, and
station 1 as sender got 140 ACKs and 1 NAK.

**16QAM receive quality by hardware path** (median of PASS frames from the
receiver's debug log, with the 10th–90th percentile range):

| run | S:N setting | path | receiver | 16QAM quality | frame FAILs |
|---|---|---|---|---|---|
| pilot01-0001 | WGN 20 | Sabrent → Syba | station 2 | 31 (29–33), 209 frames | many (201 NAKs) |
| wgn25a-0001 | WGN 25 | Sabrent → Syba | station 1 | **24 (22–27)**, 217 frames | 0 |
| wgn25a-0001 | WGN 25 | Syba → Sabrent | station 2 | **53 (47–56)**, 216 frames | 0 |
| wgn25a-0002 | WGN 25 | Sabrent → Syba | station 1 | 24 (21–27), 171 frames | 0 |
| wgn25a-0002 | WGN 25 | Syba → Sabrent | station 2 | 53 (45–56), 126 frames | 0 |

The Windows device formats are identical: both adapters render in stereo and
capture in mono, at 48 kHz, 16-bit.

**Findings:**
1. **All five corrupted messages so far went through the Sabrent → Syba path.**
   That was station 1 → 2 until the device swap, and station 2 → 1 after it. The
   problem follows the audio hardware, not the station, its settings, the cables
   or the IONOS channel.
2. **16QAM quality on that path doesn't depend on the noise.** It reads about 24
   at WGN 25 and about 31 at WGN 20, against about 53 for the reverse path at
   WGN 25. Something other than the IONOS noise degrades 16QAM on this path:
   amplitude or phase distortion, or timing, in the Sabrent's output or the
   Syba's input. 8PSK has a constant amplitude, which is consistent with it not
   being affected.
3. **Corruption also happens without any rejected frames.** The failed message
   in 0002 had 42 of 42 frames pass on the first try, so retransmission handling
   can't be the only cause. The hypothesis now: on this path, ARDOP's 16QAM
   decoder sometimes outputs wrong data that still passes its frame check.
   That's more likely when the decoded quality is this low.
4. At WGN 25 the Syba → Sabrent path ran 16QAM cleanly: 8 of 8 messages, quality
   about 53, 0 FAILs.

**Running totals of 16QAM.2000 by hardware path** (all campaigns so far):

| path | S:N setting | attempted | delivered | corrupted |
|---|---|---|---|---|
| Sabrent → Syba | WGN 20 | 14 | 10 | 4 |
| Sabrent → Syba | WGN 25 | 9 | 8 | 1 |
| Syba → Sabrent | WGN 25 | 8 | 8 | 0 |

8PSK.2000 (Syba → Sabrent, WGN 20): 14 attempted, 14 delivered.

---

## qam01: 16QAM path test without ARDOP (12 Nov 2026)

`hfbench audio qam` (module `hfbench.qamtest`) plays a known ARDOP-like signal
from each station and records it on both microphones, which covers all four
paths. The signal has 10 carriers from 600 to 2400 Hz, 200 Hz apart, at 100
baud with random 16QAM symbols, and a chirp at each end for timing. Each run
was 800 symbols (8 s) at two drive levels: −1 dBFS peak, and 6 dB lower. The
bench was as in wgn25a, with devices swapped: station 1 = Syba, station 2 =
Sabrent. The raw recordings are in the archive under `qam/`
(`qam-raw.npz`, `qam-rep.npz`).

Per path it reports:
- **MER**: the error left after fitting each carrier's gain and phase drift, so
  higher is better. The IONOS noise alone would allow about 35 dB here
  (in-band S:N measured at WGN 40).
- **Timing jitter**: the rms change in timing error from one symbol to the next,
  taken from the slope of phase across the carriers.
- **Timing wander**: the peak-to-peak range of the timing error after smoothing
  over 0.2 s.
- **Tilt**: the spread in gain across the carriers.

Three repeats at WGN 40 (`qam-rep`), with the range across the 3 × 2 levels:

| path (plays → records) | MER dB | jitter µs | wander µs p-p | tilt dB |
|---|---|---|---|---|
| Syba → Syba | 22.4–22.7 | 2.9–4.3 | 24–29 | 2.6 |
| Syba → Sabrent | 14.7–19.3 | 3.4–4.6 | 57–83 | 2.5 |
| **Sabrent → Syba** | 16.4–21.1 | **8.8–10.6** | 27–107 | **9.7** |
| Sabrent → Sabrent | 17.7–22.3 | 4.6–7.4 | 36–92 | 10.0 |

The paths recorded by the Syba run about +90 ppm against the paths recorded by
the Sabrent, whichever adapter plays. The IONOS re-clocks the audio, so the
recording adapter's clock is the one that counts.

**Findings (revised after qam02, see there):**
1. Syba → Syba was the cleanest path. On every path the Sabrent played, gain
   rippled or tilted across the carriers and MER fell toward the high carriers.
   On every path the Sabrent recorded, MER also fell toward the high carriers.
2. *Correction:* the "jitter" column (symbol-to-symbol timing change) is mostly
   measurement noise. It rises as MER falls, and in qam02 it reads about 10 µs on
   every path, Syba → Syba included. Don't use it as evidence. The sign of a
   timing problem is **MER that falls with carrier frequency**, because phase
   error from a timing error grows with frequency.
3. Even the best path topped out at about 22.5 dB MER, so the bench has a floor
   of its own below the IONOS noise. Record this as a bench limit for 16QAM-class
   modes.

---

## qam02: after moving the Sabrent to another USB port (12 Nov 2026)

The Sabrent was moved to a USB port on the Mac mini itself, not through a hub.
Windows re-enumerated it as **"3- USB Audio Device"**, a new endpoint with
default settings. Station 2's ARDOP was pointed at the new name. The endpoint was
set up again: playback 100 with balance L 0 / R 100, microphone 75, AGC off, and
48 kHz 16-bit. The first tone checks showed station 2 dead in both directions:
**the Sabrent's 3.5 mm plugs weren't fully seated.** Once reseated:

| tone check at WGN 20 | station 1 vs reference | station 2 vs reference | transmit mismatch | receive mismatch | H2 |
|---|---|---|---|---|---|
| before (wgn25a) | +2.6 dB | +2.9 dB | −0.3 dB | +0.7 dB | −40 dBc |
| after reseating | **+8.7 dB** | **+8.9 dB** | −0.2 dB | +0.7 dB | −45 dBc |

Both stations now reach the IONOS about 6 dB hotter, still matched to within
0.2 dB. The IONOS gains are unchanged (CH1 IN 50, CH2 IN 2). The splitter cables
join both adapters' outputs, so a badly seated plug changes the loading on
*both*. It's quite possible a plug was partly seated during earlier campaigns
too.

`hfbench audio qam --snr 40 40 40` (`qam-port2`), first repeat:

| path (plays → records) | MER dB | MER 600–1000 / 2000–2400 Hz | tilt dB |
|---|---|---|---|
| Syba → Syba | 19.5–20.1 | 19.3 / 19.0 (flat) | 0.1 |
| Syba → Sabrent | 14.8–16.8 | 17.5 / 12.8 (**falls**) | 0.1 |
| Sabrent → Syba | 16.5–19.0 | 19.0 / 18.4 (flat) | 8.4 (low-pass: +5.5 dB at 600 Hz, −2.9 dB at 2400 Hz) |
| Sabrent → Sabrent | 14.0–17.7 | 18.5 / 15.7 (**falls**) | 8.4 |

**Findings:**
1. **The loose plug accounted for the earlier problems with the Sabrent's
   playback.** Before reseating, the Syba's paths rippled ±1.5 dB across the
   carriers and the Sabrent's playback paths lost MER toward the high carriers.
   Both are gone now. Sabrent playback is flat in MER, apart from a smooth
   8.4 dB low-pass tilt that leaves its top carriers about 3 dB down in S:N.
2. **The Sabrent's input still has a timing fault.** Everything it records loses
   3–5 dB of MER toward the high carriers and shows more timing wander (44–134 µs
   against 24–35 µs). It did the same before the move and before reseating.
3. Now that the Syba → Syba ripple is gone, its MER reads about 19.5–20 dB at
   the hotter level, against 22.5 dB before. So the bench floor is about 20 dB.
4. Acceptance (all four paths within about 1 dB MER) **still fails**, by 3–5 dB,
   on the paths the Sabrent records.

---

## cal: bench recalibration (12 Nov 2026, afternoon)

The Sabrent stays in the bench: there's no second adapter, and the Mac mini has
no audio input. What happened during recalibration, in order:

1. **Level trim to the IONOS reference.** The Windows levels and IONOS
   **CH2 IN 2 → 1** were changed to bring both stations to about 0 dB against the
   reference. The 16QAM test then got much worse on every path. At WGN 40 a
   tone's S:N was only about 31 dB, against about 40 before.
2. **Windows enhancements.** The re-enumerated Sabrent endpoint had
   "Microsoft Audio Home Theater Effects" enabled (registry `DisableSysFx` = 0),
   and the Syba had no saved setting. Both are now **disabled** (`DisableSysFx` = 1,
   checked with registry query `scripts/windows/hfbench_fx.ps1`). This made
   **no** measurable difference (cal4 and cal5 are identical).
3. **qam analysis bug.** The best demodulation window was at +2.25 ms, outside
   the search range (−3 to +1 ms), so cal3–cal5 were understated. The search now
   covers the whole symbol (−5 to +4.75 ms in 0.25 ms steps). Re-analysing the
   earlier recordings changes them by less than 1 dB, except where noted.
4. **The real fault was a comb inside the IONOS.** With the fixed analysis, cal5
   showed the same gain ripple on all four paths: ±4 dB with peaks about 800 Hz
   apart, meaning a second copy of the signal about 1.25 ms late. It was
   identical at both receivers and for both players, so it was after the input
   mix and before the output split, inside the IONOS. It probably came from a
   front-panel menu change made while adjusting CH2 IN. **Rebooting the IONOS
   cleared it.** `WGN:x` and the reset commands sent over serial did *not*.
   Note that qam01 (`qam-rep`) shows a weaker ripple with the same spacing
   (±1.3 dB), so the IONOS may have been in a slightly wrong state then too.
5. CH2 IN was set back to 2, Syba playback L 90, Sabrent playback R 100.

**Calibration (cal6, after the IONOS reboot):**

| item | value |
|---|---|
| IONOS | firmware 2.03; CH1 IN 50 (Sabrent), CH2 IN 2 (Syba); OUT gains unchanged |
| Windows playback | Syba "C-Media USB Audio Device" L 90 / R 0; Sabrent "3- USB Audio Device" L 0 / R 100; enhancements disabled on both |
| Windows recording | Syba 35, Sabrent 75 (as calibrated 10 Nov); AGC off |
| ARDOP | station 1 (VA3ZTF) = Syba, station 2 (VE3XZQ) = Sabrent; DriveLevel 90 |
| tone check, WGN 20 | transmit +8.7 / +8.8 dB against the reference; mismatch −0.3 dB; receive mismatch +0.7 dB; H2 −45 dBc |
| tone check, WGN 40 | tone S:N 41.3–41.7 dB; bench's own noise 33 dB below the reference |

**16QAM path test (cal6, WGN 40, 2 repeats × 2 levels):**

| path | MER dB | low / high carriers | tilt dB |
|---|---|---|---|
| Syba → Syba | 19.5–19.9 | flat | 0.1 |
| Syba → Sabrent | 15.7–19.2 | sometimes falls (18 / 14) | 0.1 |
| Sabrent → Syba | 17.2–19.0 | mostly flat | 8.4 |
| Sabrent → Sabrent | 16.4–19.5 | sometimes falls | 8.4 |

The Sabrent's intermittent input timing fault and its output tilt remain. They
are known, measured properties of this bench, and the report has to state them.

**Rules adopted for the protocol:**
- Run `hfbench audio qam --snr 40 40` before every campaign, and again after
  any change at the bench. Syba → Syba must be flat (tilt < 0.5 dB) and
  ≥ 19 dB. A periodic ripple across the carriers means the IONOS needs a reboot.
- **Reboot the IONOS after any front-panel menu use.**
- Re-check that every plug is fully seated after anything is moved.
- After any re-enumeration of a USB audio device, check its Windows settings:
  levels, balance, AGC, enhancements and format.

---

## cal6wgn14 (first attempt): stopped, IONOS input clipping

Started 12 Nov 2026 at 16:02 at the cal6 levels. The operator saw the IONOS
**Lvl** meter repeatedly going into the red (more than about 1,100–1,200 mV p-p)
during ARDOP transmissions. At cal6 the tone reaches the IONOS about 6 dB hotter
than in the original calibration, which left about 8 dB of headroom with the tone
at about 400 mV, so ARDOP's peaks now clip at the IONOS input. The run was
stopped at 16:22 after 2 of 10 messages. Both sessions were aborted remotely and
the run was marked `invalid`. The 16QAM test didn't show the problem: its
−1 dBFS-peak signal at Windows level 90/100 evidently peaks lower at the IONOS
than ARDOP at DriveLevel 90 does.

**Rule added:** the IONOS Lvl meter must never go red during an ARDOP session.
Watch it for the first few minutes of each campaign. Lower the levels in Windows,
never from the IONOS front panel.

---

## cal7: levels lowered for IONOS headroom (12 Nov 2026)

Both Windows playback levels were lowered, with **no IONOS front-panel
change**, until the tone sat at the IONOS reference:

| item | value |
|---|---|
| tone check, WGN 20 | transmit **−0.2 / −0.4 dB** against the reference; mismatch **+0.1 dB**; receive mismatch +0.7 dB; receive level about −23.5 dBFS |
| tone check, WGN 40 | tone S:N 32.3–32.5 dB: the bench's own noise floor is 32 dB below the reference |
| ARDOP data S:N (expected) | about the setting − 8 dB (from pilot01: data = setting + transmit offset − 8). So WGN 22 ≈ 14 dB and WGN 28 ≈ 20 dB, with a ceiling around 24 dB set by the bench floor |

16QAM pre-check (cal7, WGN 40, 2 repeats × 2 levels):

| path | MER dB | low / high carriers | tilt dB |
|---|---|---|---|
| Syba → Syba | 19.1–21.8 | 23.0 / 20.5 at full level | 0.1 |
| Syba → Sabrent | 15.5–18.9 | falls (22 / 17) | 0.1 |
| Sabrent → Syba | 17.4–22.1 | varies | 8.3 |
| Sabrent → Sabrent | 14.7–20.8 | falls | 8.4 |

At full level, Syba → Syba improved from about 20 dB (cal6) to about 21.7 dB.
cal6's hot levels were probably already costing some quality. **Pass.**

Campaigns: `cal7wgn22` (started 16:33), then `cal7wgn28`.

---

## cal7wgn22: ARDOP 1.0.2.9, WGN 22 (expected ≈ 14 dB data S:N), cal7 levels

Started 12 Nov 2026 at 16:33. Station 1 (VA3ZTF) uses the Syba and station 2
(VE3XZQ) the Sabrent, as since wgn25a. 2 replicates of Text_50KB (5 + 5 messages).
The operator was asked to watch the IONOS Lvl meter; no red was reported.

| run | start | outcome | delivered | 2→1 goodput (Sabrent → Syba) | 1→2 goodput (Syba → Sabrent) | modes | ended by |
|---|---|---|---|---|---|---|---|
| 0001 | 16:36:00 | completed | 10/10, 50.2 min | 1,234–1,292 bit/s | 1,147–1,189 bit/s | both 8PSK.2000 after the 4PSK ramp | normal end |
| 0002 | 17:30:52 | completed | 10/10, 51.4 min | 1,198–1,263 bit/s | 1,129–1,219 bit/s | both 8PSK.2000 after the 4PSK ramp | normal end |

ARDOP debug logs (data frames, both runs):

| run | sender | 8PSK.2000 frames sent | NAKs received | receiver's 8PSK quality, median (p10–p90) | 16QAM |
|---|---|---|---|---|---|
| 0001 | station 1 (Syba) | 257 | 2 | 72 (72–73) | never |
| 0001 | station 2 (Sabrent) | 258 | 4 | 73 (72–74) | never |
| 0002 | station 1 (Syba) | 257 | 1 | 73 (72–73) | never |
| 0002 | station 2 (Sabrent) | 258 | 10 | 73 (72–74) | never |

No Winlink errors (checksum, decompress or link) in either station's log.

**Findings:**
1. **At cal7 levels the two directions are symmetric.** Both ran 8PSK.2000 for
   the whole session, at the same receive quality (72–73) and within about 7%
   goodput of each other. The earlier quality gap on the Sabrent → Syba path
   (about 24–31 against 53 at 16QAM) doesn't show at 8PSK.
2. **ARDOP never tried 16QAM at this S:N.** The quality sits at 72–74, just
   under the shift-up threshold seen before (about 72–74), so the gearshift
   stays at 8PSK. In pilot01 (WGN 20 at the old, hotter levels, about 14 dB
   data S:N) 16QAM was used. At this S:N, whether ARDOP shifts up is
   borderline and depends on small differences in quality.

**Measured S:N** (`listen-20261112-1633`, trimmed to 16:33–18:22:13 so that the
cal7wgn28 traffic recorded after it is excluded):

| direction | data frames | data S:N median (middle half) | vs setting | control S:N |
|---|---|---|---|---|
| 1 → 2 (Syba → Sabrent) | 551 | **14.9 dB** (14.8–15.0) | −7.1 dB | 19.0 dB |
| 2 → 1 (Sabrent → Syba) | 562 | **15.5 dB** (15.4–15.5) | −6.5 dB | 18.8 dB |

Data-frame mismatch −0.6 dB (symmetric). The data S:N is about 1 dB above the
cal7 estimate (setting − 8 dB), so here data ≈ setting − 7 dB. The untrimmed
file reads 15.2 / 15.8 dB, because its last 40 minutes are WGN 28 traffic.

3. 20 of 20 messages delivered, none corrupted, all at 8PSK.2000 in both
   directions (the Sabrent → Syba path included).

---

## cal7wgn28: ARDOP 1.0.2.9, WGN 28 (measured ≈ 18 dB data S:N), cal7 levels

Started 12 Nov 2026 at 18:23, straight after cal7wgn22, with the same devices and
levels.

| run | start | outcome | delivered | 2→1 goodput (Sabrent → Syba) | 1→2 goodput (Syba → Sabrent) | modes | ended by |
|---|---|---|---|---|---|---|---|
| 0001 | 18:26:08 | completed | 10/10, 43.1 min | 1,409–1,563 bit/s | 1,364–1,431 bit/s | both 16QAM.2000 from the first message | normal end |
| 0002 | 19:13:53 | dnc | 3/10, 18.7 min | 1,276–1,547 bit/s (2 msgs) | 1,381 bit/s (1 msg) | both 16QAM.2000 | ARQ timeout during station 1's 2nd message (AS21E74HAIMR), 19:32:38 |

ARDOP debug logs, 16QAM.2000 frames:

| run | path | receiver | 16QAM quality, median (p10–p90) | frames | NAKs |
|---|---|---|---|---|---|
| 0001 | Sabrent → Syba | station 1 | **38 (37–40)** | 217 | 1 |
| 0001 | Syba → Sabrent | station 2 | **64 (63–64)** | 216 | 1 |
| 0002 | Sabrent → Syba | station 1 | 38 (37–40) | 83 | 1 |
| 0002 | Syba → Sabrent | station 2 | 64 (63–64) | 83 | 0 |

**The 0002 failure:**
- Station 1's TNC sent all of AS21E74HAIMR at 16QAM.2000 (19:27:47–19:31:35).
  Every data frame was ACKed on the first try (0 NAKs), and station 2's TNC
  decoded all of them as PASS at quality 63–64.
- Both ends' ARQ stats agree to the byte: station 1 sent 85,161 bytes over the
  session and station 2 received 85,161.
- Station 1 then sent IDLE to hand over the link. Station 2's TNC answered each
  IDLE with an ACK (22 times) but stayed in IRS, because its Winlink Express never
  sent anything back. After 60 s station 1's ARQ timeout disconnected.
- Station 2's Winlink log shows "Receiving AS21E74HAIMR" at 19:27:57 and nothing
  more until the disconnect. There was no checksum or decompress error.

So all the bytes arrived, but Winlink at station 2 didn't recognise the message as
complete. The likeliest explanation is the same mechanism as the earlier
checksum failures. A 16QAM frame decoded to wrong data that still passed ARDOP's
frame check. Here it probably hit the B2F framing (for example a block length),
so Winlink waited for more data instead of failing the checksum. This is a
hypothesis.

**What station 2 actually received** (checked 12 Nov, 20:50):
- Winlink had left a partial, `Partials\AS21E74HAIMR.bin` (34,500 bytes,
  written 19:30). The next run's set-up quarantined it, and it is archived as
  `logs/archive/partials/cal7wgn28-0002-AS21E74HAIMR.bin`.
- It holds the B2F compressed stream received so far: CRC16, the length (51,411),
  then the LZHUF data. `scripts/check_partial.py` decodes it.
- The header is intact. The attachment matches the original
  `File-A9TS9.txt` **byte for byte for the first 41,838 of 51,200 bytes (82%)**,
  which is exactly where the saved compressed data ends.
- **So the first 82% of the message arrived uncorrupted.** The last 7.6 KB
  (received 19:30–19:31:35) was never written to the partial, so corruption
  there can't be confirmed or ruled out. A Winlink-side stall remains possible.

**Findings:**
1. **At WGN 28 ARDOP runs 16QAM.2000 in both directions from the first message,**
   at 1,364–1,563 bit/s, about 20% above 8PSK at WGN 22.
2. **The 16QAM quality asymmetry is still there at cal7 levels:** 38 on
   Sabrent → Syba against 64 on Syba → Sabrent. That's the same direction as in
   wgn25a (24 against 53). The Syba's recording of the Sabrent's signal is
   still the weak path, consistent with the qam pre-check (Sabrent output tilt
   8.3 dB).
3. **The failure was on the good path, Syba → Sabrent (quality 64).** It's the
   first failure on this path and the first that shows as a hang instead of a
   checksum error. Meanwhile Sabrent → Syba delivered 7 of 7 at quality 38. So
   failures don't simply follow ARDOP's quality figure. Whatever corrupts
   16QAM data without a frame failure can happen on either path.
4. **Measured S:N** (`listen-20261112-1823`, trimmed to the two runs): data
   frames **17.9 dB** (1 → 2) and **18.4 dB** (2 → 1), control frames 23.5 dB,
   mismatch −0.5 dB. That's only 3 dB above WGN 22 for a 6 dB step. The bench's
   own noise (32 dB below the reference, a data-frame ceiling of about 24 dB)
   now adds to the IONOS noise. **On this bench, "good conditions" top out at
   about 18–20 dB data S:N.**
5. The operator was asked to watch the IONOS Lvl meter at the start of 16QAM;
   no red was reported.

**16QAM.2000 at cal7 levels by hardware path:**

| path | S:N setting | attempted | delivered | failed (corrupted or hung) |
|---|---|---|---|---|
| Sabrent → Syba | WGN 28 | 7 | 7 | 0 |
| Syba → Sabrent | WGN 28 | 8 | 7 | 1 (hang, 0002) |

Previous totals (pre-cal7 levels) are in the wgn25a section. Across all campaigns,
16QAM.2000 has now had 6 failures in 46 messages. 8PSK.2000 has had none in the messages counted here (14 at WGN 20, 20 at cal7wgn22).

---

## oneway28: ARDOP 1.0.2.9, WGN 28, one-way (station 1 → station 2)

Decided 12 Nov 2026 with the operator. From now on each run sends **10 messages one
way**, from station 1 (Syba playback) to station 2 (Sabrent capture). Station 2
sends none. The reasons:
- Every modem is compared over the same hardware path, so the bench's two
  unequal paths don't mix into one number.
- The weak direction carries only ACKs and control frames, in robust modes.
- The Syba's output is flat. The Sabrent's 8 dB output tilt would favour
  modems that equalise.
- ARDOP rated this direction better (16QAM quality 64 against 38).

`hfbench messages build --s1-messages 10 --s2-messages 0` builds the templates
(added in this session). The runner then imports nothing at station 2 but still
requires its Outbox to be empty. A failed message is now treated as a result
(reliability) as well as a run outcome.

Pre-check (20:20–20:40, after the operator reset both Winlink instances):

| item | value |
|---|---|
| tone check, WGN 20 | transmit −0.2 / −0.3 dB against the reference, mismatch +0.1, receive mismatch +0.7, unchanged from cal7 |
| tone check, WGN 40 | tone S:N 32.3–32.5 dB |
| 16QAM path check, WGN 40, full level | Syba → Syba **22.0 dB** (tilt 0.1); Syba → Sabrent 18.7 (falls 21.7 / 16.6); Sabrent → Syba 18.3 (tilt 8.3); Sabrent → Sabrent 17.5. **Pass** |

Campaign started 20:44, 3 replicates at WGN 28, with listen `listen-20261112-2044`.

| run | start | outcome | delivered | 1→2 goodput | modes | ended by |
|---|---|---|---|---|---|---|
| 0001 | 20:45:56 | dnc | 1/10, 10 min | 1,363 bit/s | 16QAM.2000 | station 2: *Link Error – Checksum error. Failed to assemble correct binary image* (20:54:54), on the 2nd message S176LKCKL8SF (File-NqdBp.txt) |

The runner then stopped before 0002, as designed, because station 1's Outbox still
held 9 messages. One-way B2F worked as expected: station 2 sent FF, and station 1
offered all ten and sent them one at a time.

**Forensics of the corrupted message.** Station 2's partial `S176LKCKL8SF.bin`
(42,000 bytes, archived as `logs/archive/partials/oneway28-0001-S176LKCKL8SF.bin`)
holds 41,994 of the 42,117 compressed bytes. `scripts/check_partial.py` decodes it.
It also re-compresses the original message with the same LZHUF coder, which
reproduces Winlink's stream exactly (0 differences against the clean
cal7wgn28-0002 partial). So it can list the exact bytes that changed:

| compressed offset | sent | received | bits flipped |
|---|---|---|---|
| 33,402 | 1010 0110 | **1001** 0110 | 2, inside the high nibble |
| 33,465 | 1001 1010 | 1001 **1001** | 2, inside the low nibble |

- **Only two bytes of 42,000 are wrong.** Each error is confined to one 4-bit
  nibble, which is one 16QAM symbol, and both are the same confusion: 1010
  received as 1001. These are **demodulation symbol errors**, not lost or
  duplicated data and not a software fault.
- The two bytes are 63 bytes apart, in the same B2F block. ARDOP 16QAM.2000
  carries 1,024 bytes per frame, so they were almost certainly in one frame.
- Station 2's ARDOP log shows every data frame of this message decoded PASS
  on the first try, at quality 61–66, with no NAKs. **A frame with two symbol
  errors passed ARDOP's frame check** and was delivered to Winlink as good.
- The cal7wgn28-0002 hang partial, re-checked the same way, has 0 wrong bytes
  in the 34,494 received. Its tail was never saved, so that hang is still
  unexplained.

**0002** (restarted 21:05 after the operator's reset): **dnc, 4/10**. The first
four messages were delivered at 1,290–1,435 bit/s. The 5th, RY0VDQU1TRYD
(File-FJYnL.txt), failed at 21:29:09 with the same *Checksum error*. Station 2's
ARDOP log for that message: 42 16QAM frames, all PASS on the first try, quality
62–66, 0 NAKs. Its partial (`oneway28-0002-RY0VDQU1TRYD.bin`, 41,994 compressed
bytes) has **4 wrong bytes, all within 104 bytes** (compressed offsets 21,443–21,546).
Each error again stays inside one nibble:

| compressed offset | sent | received |
|---|---|---|
| 21,443 | 1011 1001 | 1011 **1000** |
| 21,501 | 1001 1011 | 1000 1011 |
| 21,545 | 0101 1100 | 0101 **1011** |
| 21,546 | 1111 0111 | **1000** 0111 |

The runner then stopped before 0003, because 6 messages were left in station 1's
Outbox.

**16QAM.2000 at WGN 28 (≈ 18 dB data S:N), Syba → Sabrent so far:** cal7wgn28
8 attempted, 7 delivered, 1 hang. oneway28: 7 attempted, 5 delivered, 2
corrupted. **Total: 15 messages, 3 failures (20%).** Every failure ends the
session, so at that rate a 10-message run would complete only about 1 time in 9
(0.8¹⁰ ≈ 0.11). For ARDOP at this S:N, the useful measures are therefore **goodput
per delivered message and the failure rate per message**, not completed runs.
Automatic recovery is what makes collecting them practical.

**What this means:** the earlier corruptions (checksum and decompress errors)
fit the same mechanism. On this path ARDOP 1.0.2.9's 16QAM sometimes
mis-decides a symbol, and its frame check doesn't always catch it. This failure
was on the Syba → Sabrent path, so the problem isn't confined to the Sabrent →
Syba direction. For the comparison it counts as an ARDOP 16QAM reliability
result at about 18 dB data S:N on this bench.

---

## ARDOP 1.0.2.9 source: why corrupted 16QAM frames pass (12 Nov 2026)

Source: the ARSFI ARDOP_Win repository (VB.NET), commit `bc11cb3` (20 Jul 2026),
whose AssemblyInfo is version **1.0.2.9**, the TNC Winlink Express runs on the bench.

**How a received data carrier is checked** (`DemodulateDecode12K.vb`,
`CorrectRawDataWithRS`). Each carrier holds a byte count, the data, a 2-byte CRC and
Reed-Solomon parity. A 16QAM carrier is 1 + 128 + 2 + 64 bytes = 390 symbols.
1. If the CRC over count + data matches, the data is accepted. **RS parity is not
   looked at.**
2. Only if the CRC fails does RS correct up to 32 byte errors, and then the CRC is
   checked again.

So symbol errors that RS can fix produce no NAK and no visible sign in the log. A
carrier whose errors happen to satisfy the CRC is accepted without the RS check
that would have caught them.

**The CRC is weaker than its comment says** (`Globals.vb`,
`GenCRC16FrameType`/`CheckCRC16FrameType`). It is commented as CRC-16-CCITT
(x¹⁶ + x¹² + x⁵ + 1). But this left-shifting algorithm uses the constant `&H8810`,
where CCITT needs `&H1021`. `&H8810` is the polynomial x¹⁶ + x¹⁵ + x¹¹ + x⁴, which
has no +1 term and is divisible by x⁴. `scripts/ardop_crc_sim.py` ports the routine
bit for bit and puts random 16QAM symbol (nibble) errors into a 129-byte carrier
(200,000 trials each):

| symbol errors in a carrier | ARDOP 1.0.2.9 CRC misses | true CRC-16-CCITT misses |
|---|---|---|
| 1 | never | never |
| 2 | **1 in 8,300** | never |
| 4 | **1 in 2,700** | 1 in 67,000 |

**This matches what the bench shows:**
- the corrupted messages contain only whole-symbol (nibble) errors, 2 and 4 of
  them in one carrier;
- every frame of those messages passed on the first try with no NAKs (RS was
  quietly fixing the other carriers' errors);
- each 16QAM message is about 42 frames × 8 carriers ≈ 340 carrier checks. If
  most carriers carry a few symbol errors at about 18 dB data S:N on this bench,
  roughly 1 escape per 3,000–8,000 carriers gives a failure every 10–25 messages.
  That's the order of magnitude seen.

8PSK carries 3 bits per symbol and runs at a higher quality here, so it has
fewer errors to slip through (0 failures in 34 messages).

**Upstream has since changed the check.** In the current ARDOP_Win development
code (1.0.3.x), `CorrectRawDataWithRS` carries the note "2026-10-10 LAB
EXPERIMENT: Verify parity as well as CRC for every carrier". It now accepts a
carrier only when the RS parity verifies **and** the CRC matches. The CRC
constant is unchanged. Verifying parity is receiver-side only, so it stays
compatible over the air. Changing the CRC polynomial would not.

**What this means for the comparison:**
- The 16QAM failures are an ARDOP 1.0.2.9 integrity weakness, made more frequent
  by symbol errors from the S:N and the bench's own MER limit (about 17–22 dB).
  They are not a fault of one station or adapter.
- They should be reported as an ARDOP 1.0.2.9 result. A later ARDOP version with
  parity verification is worth testing on the same bench.

---

## oneway28 0003 and oneway28r: both directions one-way at WGN 28 (12–13 Nov 2026)

**oneway28-0003** (21:48, first run with `--recover`): **completed, 10/10**, 1,284–1,441
bit/s measured from the sender's log (see the goodput note below). oneway28 in
total: **17 attempted, 15 delivered, 2 corrupted**.

**oneway28r** (reverse, station 2 / Sabrent → station 1 / Syba, 4 runs, `--recover`).
Pre-check (22:35): tone unchanged. 16QAM path check: Syba → Syba 21.0 dB, flat. The
paths the Sabrent receives read 15.7 / 13.2 dB, 2–4 dB lower than at 20:40 (its
intermittent capture timing).

| run | start | outcome | delivered | goodput (receiver's log) | failure | recovery |
|---|---|---|---|---|---|---|
| 0001 | 22:43:52 | dnc | 4/10 | 1,517–1,553 bit/s | checksum error on msg 5, TL9R5WJVJWYT (23:06:08) | ok, 83 s |
| 0002 | 23:10:54 | completed | 10/10 | 1,517–1,556 bit/s | none | none |
| 0003 | 23:59:17 | dnc | 0/10 | none | checksum error on msg 1, 697OUUYZHTAB (00:04:09) | ok, 87 s |
| 0004 | 00:09:00 | completed | 10/10 | 1,517–1,563 bit/s | none | none |

**26 attempted, 24 delivered, 2 corrupted.** The automatic recovery ran twice
unattended and the campaign carried on each time. The first start (22:38) failed
before any run because, after the recovery restart, Winlink's Import dialog
appeared as a child of the main window. That was fixed and the campaign restarted
at 22:43.

**Partials** (`scripts/check_partial.py`):

| message | wrong bytes | span | errors |
|---|---|---|---|
| TL9R5WJVJWYT (0001) | 5 (6 symbols) | 110 bytes | xor 0001, 0001, 0011, 0001, 0011 0001 |
| 697OUUYZHTAB (0003) | 4 | 46 bytes | xor 0001 0000, 0001 0000, 0001, 0001 |

Same pattern as oneway28: a few symbol errors packed into one carrier, accepted
with every frame PASS. Each carrier has 64 RS parity bytes (up to 32 corrections),
so **all four corrupted carriers seen in the one-way runs would have been corrected
by the parity already in the frame**, had 1.0.2.9 checked it.

**Measured S:N** (listen, trimmed to each campaign's runs): data frames **17.9 dB**
(1 → 2, oneway28) and **18.4 dB** (2 → 1, oneway28r), control frames 23.4–23.7 dB.

**Goodput depends on which station's log is used.** Both directions send the
same 16QAM frames, about 42 per message, at the same 5.3 s cycle, with 3–4 NAKs per
run. Measured from the **receiving** station's log, Syba → Sabrent gives
**1,510–1,561 bit/s**, the same as Sabrent → Syba. The sender's log gives about 10%
less (1,284–1,441), because its "Sending … Completed send" interval includes about
20 s of handover after the last frame. `hfbench parse` so far reads only station
1's log. So every **tx** figure in this log, and every Syba → Sabrent figure in
cal7wgn22/28 and oneway28, is sender-side and about 10% low. **From now on goodput
is taken from the receiving station's log.**

### Evaluation so far: ARDOP 1.0.2.9 on the calibrated bench (cal7)

Earlier campaigns (pilot01 to wgn25a, cal6) ran on a bench with a loose plug, hot
levels or IONOS clipping. They are kept as commissioning history, **not** used in
the comparison.

| IONOS | data S:N | mode | messages | delivered | failed | goodput per message (receiver) | net throughput |
|---|---|---|---|---|---|---|---|
| WGN 22 | 14.9 / 15.5 dB | 8PSK.2000 | 20 (two-way) | 20 | 0 | 1,248–1,282 bit/s (run medians) | 1,107 bit/s |
| WGN 28 | 17.9 / 18.4 dB | 16QAM.2000 | 57 (14 two-way, 43 one-way) | 52 | **5 (8.8%)**: 4 checksum, 1 stall | 1,497–1,551 bit/s (run medians) | 1,066 (oneway28), 1,161 (oneway28r), 1,181 (cal7wgn28) bit/s |

*Net throughput* = compressed bytes delivered × 8 ÷ total session time, failed
sessions included (recovery time excluded). Figures recomputed 13 Nov with
`hfbench results`, which reads both stations' logs and takes goodput from the
receiver. One-way WGN 28: oneway28 15 messages
in 77 min ≈ 1,095 bit/s; oneway28r 24 in 116 min ≈ 1,160 bit/s. WGN 22 two-way: 20
in 102 min ≈ 1,105 bit/s.

**Findings:**
1. **16QAM is about 25% faster per message, but at this S:N its failures cancel
   that out.** Each failure throws away the message in progress and ends the
   session. Net throughput at WGN 28 is about the same as 8PSK at WGN 22. The WGN
   22 runs were two-way, so the comparison is approximate.
2. **The failures are an ARDOP 1.0.2.9 property, the same in both directions:**
   Syba → Sabrent 2/17, Sabrent → Syba 2/26. The cause is the per-carrier check
   (see the source analysis above), not a station or an adapter. The bench's own
   impairments only set how often there are symbol errors to miss.
3. **Winlink's end-to-end check caught every corrupted message.** Each surfaced as
   a checksum error or a stall, never as a bad message in the Inbox. **Verified 13
   Nov:** `hfbench results --verify` compared every delivered attachment at the
   receiving station with the payload file. **72 of 72 identical** (cal7wgn22 20,
   cal7wgn28 13, oneway28 15, oneway28r 24).
4. **Bench ceiling:** with the Sabrent in the chain, the highest data S:N reachable
   is about 18–20 dB (bench floor 32 dB below the reference, 16QAM MER 17–22 dB).
   That is enough for ARDOP's top mode, but probably not for VARA HF's fastest levels (to be confirmed on the bench).

---

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

---

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

## Stage 5: ULTRA (ProjectUltra) 0.6.2-pre-alpha, bring-up, paused (19 Nov 2026)

**Install.** `projectultra-windows.zip` (sha256 1225a638…4e36e) unpacked to `C:\ProjectUltra`;
`ultra_tnc` 0.6.2, commit a18a6b84 (`dirty=true`, built 10 Nov), sha256 eb3eff9d…b0daa9. One
install, two TNCs started by `scripts/windows/hfbench_start_ultra.ps1`: station 1 VA3ZTF, C-Media
(Syba), port 8300; station 2 VE3XZQ, "3- USB Audio Device" (Sabrent), port 8310 through the relay.
`ultra_tnc` speaks VARA's TCP command set (`PUBLIC ON`, `CWID ON`, `COMPRESSION ON`, `BW2750`,
`MYCALL`, `LISTEN ON` all answered OK), so Winlink drives it as a Vara HF P2P session; runner
profile `ULTRA`. Drive: ULTRA's default `--tx-drive 0.50` (each burst normalised to a −6.0 dBFS peak).

**One good run.** `cal-ultra` (WGN 40, 3 × 50 KB, 22:12-22:25 UTC): **3/3 delivered, identical**,
3,550-3,833 bit/s per message (ULTRA's receive side), **1,410 bit/s net**, connect 14 s. Transmit
log (station 2, 259 s of data bursts of 7-18 s): mean −18.7 dBFS, PAPR 11.2 dB at 0.01 %, peak
−6.0 dBFS; short control bursts −12.9 dBFS, PAPR 6.1 dB. With the peak pinned, ULTRA's data runs
about 7 dB under the reference level (about −11.7 dBFS mean on station 2's card), and its maximum
drive (0.70) would still leave about 4 dB; its peaks at 0.50 are about VARA's (−5.4 dBFS), which never
reddened the IONOS. Kept at 0.50 (D5 exception, as VARA); measured S:N would place it.

**Why it was paused: it answers its own signal.** One IONOS in half-duplex mode mixes both
stations onto both outputs, so each station hears itself at the other's level (tone check 1 -> 1
−22.7, 2 -> 1 −22.8 dBFS). ARDOP, VARA HF, Mercury and Data2G ignore their own signal; ULTRA
doesn't. Station 1's debug log: PING heard at 25.3 s -> PONG sent 25.35-27.19 s -> a chirp found
at 28.2 s *inside its own PONG* (SNR 19.7 dB) taken for a new PING -> another PONG, every 3 s
until the process was stopped (the 450 mV p-p the operator saw on the IONOS at 23:15). Earlier the
same mechanism gave `Simultaneous CONNECT with identical callsign VA3ZTF, rejecting` (station 2
hearing its own CONNECT) when both ends ran as VA3ZTF.
- **Workaround tried:** `scripts/windows/ultra_rxmute.py` (pycaw, installed on the bench) mutes each
  station's Windows microphone from ULTRA's `PTT ON` until 0.15 s after `PTT OFF`, as a
  transceiver mutes its receiver. Checked: a muted microphone records digital silence (−240 dBFS)
  and unmutes at once. Measured with only station 1 calling: its own signal reaches its microphone
  0.14-0.30 s after `PTT ON` and ends about 0.1 s before `PTT OFF` is reported, so the 0.15-s tail
  can't clip a reply (the other side's turnaround is ≥ 0.3 s plus 0.14 s of path). (A first 0.6-s
  tail would have clipped about 80 ms of a fast reply: replaced.) With it, a direct connect at WGN 17
  completed in about 11 s; at WGN 7 none in 10 attempts.
- **Other faults, no workaround:** after a failed or abandoned call a TNC stays in CONNECTED or
  CONNECTING and refuses the next `CONNECT` until restarted (retries went on after the host had
  closed its connection); a `DISCONNECT` during the handshake got `WRONG`; one `PTT ON` (station 2,
  192.8 s) had no `PTT OFF`. Recovery now restarts both TNCs (profile `restart`), which works, but a
  sweep can't run unattended on that.

**Bench faults during bring-up (not ULTRA results; folders kept):** `cal-ultra-samecall` (both ends
VA3ZTF); `cal-ultra-stale` (station 1's TNC stuck from the previous attempt, 0 calls answered); one
`sweep-ultra-50k` run dnc (WGN 17, the self-PONG loop). Fixed in the runner along the way:
recovery starts the relay first for relay campaigns; `open_session` clicks again after 20 s;
recovery presses OK on Winlink message boxes (an "Unable to open Vara command port" box had
disabled station 1's windows); `folder_mids` checks the grid's row count against the folder's own
count. **Without that check, recovery would have deleted station 1's Inbox:** with its window
disabled, the Outbox click did nothing and the 1,328 Inbox rows were read as the Outbox. Nothing was
deleted (stopped by hand; Winlink log and message files checked).

**Reported** to the developer, 19 Nov: https://github.com/secup/ProjectUltra/issues/38. ULTRA is
paused until a build addresses the self-echo and the stuck states; next is Aether HF (operator).

## Stage 6: Aether HF 0.2.0-beta.159 (19-20 Nov 2026)

**Install and settings.** The operator's two installs (`%LOCALAPPDATA%\Aether HF` and `Aether HF 2`),
both 0.2.0-beta.159 (`aetherd` sha256 76c1f128…4f992a), pinned for the stage. `aetherd` runs headless,
started by `scripts/windows/hfbench_start_aether.ps1`, which writes each station's config in its own
folder (aetherd keeps a settings profile beside it): station 1 VA3ZTF, C-Media, VARA-compatible host
port 8300, control 8515; station 2 VE3XZQ, "3- USB Audio Device", host 8310 (through the relay),
control 8525. Winlink drives it as Vara HF P2P; runner profile `Aether HF`, and recovery restarts both
daemons. Bench settings that differ from Aether's defaults:
- `record.send_to_project = false`. **Aether's default uploads every program-driven session's
  recording (audio), logs and settings to the Aether project** during its field trials; nothing left
  this bench.
- Busy detection off: `wait_for_clear = false` and `busy_threshold_db = 60`. `wait_for_clear` alone only
  stops Aether waiting; its detector still told Winlink `BUSY ON`, and Winlink holds its call while the
  modem says busy: crest-aether-0001 (WGN 40) never called, BUSY ON for 71 s after the IONOS setting
  changed (relay log 11:03:11-11:04:22). With the threshold at 60 dB nothing was reported again.
- `[regulatory] profile = "none"` (Aether transmits nothing until a profile is set; Canadian calls,
  simulator, no radio), PTT none (VOX, as every modem here), no CW ID, compression off unless offered.
- It hears itself on this bench (one IONOS) and only warns ("the radio's receive audio did not change
  while it was keyed"); unlike ULTRA it doesn't answer its own signal.

**Level (D5).** `tx_level` is the amplitude of a sine with the data's RMS. At its default 0.25 the data
bursts averaged −15.0 dBFS digital, PAPR 10.2 dB, peak −4.3 dBFS (cal-aether, 3/3, 2,427 bit/s net).
0.35 put the peaks at −1.5 dBFS, as close to the reference as its peaks allow; the operator watched the
IONOS: peaks about 950 mV p-p, no red (cal-aether-l35b, 20 Nov 00:17-00:25). Bench level 0.35. **Received,
the data was only about 0.9 dB under the reference tone** (noise at WGN 22 −44.5 dBFS, data S:N 20.8 dB:
−23.7 dBFS against the tone's −22.8), not the 3.1 dB the digital levels suggested: the transmit-side
estimate reads about 2.2 dB low, as it did for VARA (8.0 dB digital, 5.4 dB received). Aether's slowest
mode (the 16-FSK floor, WGN −2 and below) runs at −6.6 dBFS mean, PAPR 3.3 dB: 5.6 dB more average power
than its OFDM modes (−12.2 dBFS, PAPR 10.2; 8.7 at WGN 7 and 2), with lower peaks. As VARA's FSK modes,
so measured S:N is the axis; it is also why WGN 2 and WGN −2 measured almost the same (1.5 and 1.1 dB).

**Results.** 50 KB sweep 90/90, 5 KB sweep 180/180, crest 24/24 (crest-aether-0001 re-run as
crest-aether-r40), cliff 36 delivered: **all 339 delivered attachments identical; no corrupted message, no
hung session, no failed sweep run.** Connect 12 s in every run. Median net per setting (3 runs):

| WGN | Measured S:N | Net bit/s | Per message (median) |
|---|---|---|---|
| 40 (50 KB) | 28.8 dB | 2,637 | 3,307-3,340 |
| 22 (50 KB) | 20.8 dB | 2,485 | 3,027-3,137 |
| 17 (50 KB) | 16.3 dB | 2,090 | 2,606-2,654 |
| 17 (5 KB) | 16.3 dB | 1,292 | |
| 12 | 11.4 dB | 1,018 | |
| 7 | 6.4 dB | 875 | |
| 2 | 1.5 dB | 375 | |
| −2 | 1.1 dB | 154 | |
| −5 | −1.9 dB | 155 | |

**Cliff** (`scripts/aether_cliff.sh`; WGN −5, `tx_level` stepped down 3 dB at a time, 2 × 10 × 5 KB per
step, 60-min time box): −3 dB (0.248): 20/20 at −4.8 dB, 151 bit/s; −6 dB: 12 delivered at −8.0 dB,
60 bit/s; −9 dB: 4 at −11.3 dB, 20 bit/s; **−12 dB (0.088): nothing** at −13.6/−14.3 dB (two calls failed,
the third connected and dropped after 12 min; the second run connected nothing). Last delivering point
−11.3 dB.

**Compared on measured S:N** (charts `docs/charts/interim-wgn/`, regenerated with Aether, bench 13-20
Nov). In good conditions Aether is third: VARA HF is faster at the same S:N (2,803 at 17.9 dB against
Aether's 2,090 at 16.3 and 2,485 at 20.8) and Data2G well ahead (3,869 at 17.5). From about 5 to 12 dB
Aether and VARA are level; at the bottom Aether goes about 2 dB further than VARA (last delivery −11.3
against −9.4 dB) and is behind only Data2G (still 15 bit/s at −13.9 dB). It is clearly ahead of ARDOP
1.0.2.9 and Mercury everywhere. (A comparison by IONOS setting, as first reported to the operator,
overstated Aether against VARA: at the same setting Aether's data arrives about 4.5 dB louder.) Equal-peak
view: Aether's OFDM PAPR 10.2 dB is a little below VARA's fast modes (11.7); its FSK floor is 3.3 dB.

**Runner faults on the way (fixed):** a window closing during recovery's process check
(`COMError ... unable to invoke any of the subscribers`, `winlink_ui._mine` now skips it); the chain's
log watch on this machine sometimes cut lines (operator side only). `archive-bench.sh` and
`export_audit_data.py` now also take Aether's and ULTRA's logs.

**ARDOP 1.0.3.3, measured S:N** (sweep-ardop133-50k, now computed): WGN 40 24.4 dB, 22 16.4 dB, 17 11.9 dB
(runs 7-9 not recorded: the power cut). Against 1.0.2.9 (21.9 / 15.4 dB at 40 / 22), 1.0.3.3's frames
arrive about 1-2.5 dB stronger at the same drive; its 1,041 bit/s at 11.9 dB compares with 1.0.2.9's
499 at 10.8 dB (5 KB) and its 50 KB time-outs at WGN 17.

## Modem73 2.5.0: not tested (20 Nov 2026)

The operator's download was the right one: RFnexus's own Windows port (`RFnexus/modem73-win`) of
Modem73 2.5.0, the latest release (2 Nov 2026), two copies (`modem73.exe` sha256 e4165312…). But
Modem73 is a physical-layer modem only: KISS over TCP (8001) and a JSON control port (8073), one
operator-chosen mode at a time (OFDM BPSK-QAM4096 about 790 bit/s-13 kbit/s, ROBUST 149-1,150 bit/s,
MFSK), with no connections, no ARQ, no speed adaptation and no VARA- or ARDOP-style host interface,
so Winlink Express can't drive it as it drives the other modems here. The only Winlink-capable
variant found, the fork `cgrant417/modem73fm` (VARA host interface, its own ARQ and speed ladder), is
built and tested for FM radios through 9600 data jacks, Linux only, based on Modem73 2.4.2. Testing
either (Modem73 as a fixed-mode AX.25 packet TNC, or the FM fork on an HF bench) would give numbers not
comparable with the adaptive ARQ modems. **Decision (operator): skip Modem73**; for the final report:
an OFDM modem of interest, not usable with Winlink Express as released; re-test if an ARQ/Winlink
interface reaches an HF release.

## White-noise stage complete (20 Nov 2026)

Every modem that is stable and usable with Winlink Express has had the full white-noise set (50 KB and
5 KB sweeps, crest runs, cliff search where it still delivered at WGN −5): **ARDOP 1.0.2.9, Mercury
1.9.23, Data2G 0.5.1, VARA HF 4.9.1, Aether HF 0.2.0-beta.159** (summary: `docs/interim-report-wgn.md`).
Not complete, by decision: ARDOP 1.0.3.3 (50 KB sweep only; Phil has a newer build), ULTRA 0.6.2
(paused, secup/ProjectUltra#38), Modem73 (skipped, above); Mercury to be re-tested on its next release.
Next: fading channels (CCIR) for the five.

## Stage 7: fading (CCIR), first attempt invalid: the IONOS ignores channel commands over USB (20-21 Nov 2026)

**What happened.** VARA HF's CCIR campaign (ccir-vara-50k, profiles MPG/MPM/MPP at IONOS 30 and 20,
started 20 Nov 21:40 UTC) delivered 10/10 at 3.1-4.6 kbit/s per message in every one of 15 runs, on
MPP as on MPG and as fast as in white noise. The operator asked whether this followed an established
protocol. N5TW's IONOS report ("Take Three", Nov 2020) has VARA at 30 dB at about 6.1 kbit/s on WGN,
3.9 on MPG and 2.4 on MPP: fading should have cost it 40-60 %. The chain was stopped at run 16
(marked invalid).

**Diagnosis** (received level per 20-ms block, 3 kHz, at station 1's microphone):
- VARA's data level varied by 2.5 dB (10-90 %) in a WGN run (sweep-vara-50k-0002) and by 2.7 dB in
  the "MPM" and "MPP" runs: no fading.
- A steady 1,500 Hz tone from station 2 (`fadetest.py`), IONOS set over USB to WGN, MPG, MPM, MPP or
  MPD (2 or 4 paths): spread about 1 dB in every mode. `WGN:0` over USB did add noise, but
  `OFFSET:100` didn't move the tone (1,499.8 Hz).
- The operator set MPD with the knob, and the IONOS's own test tone fluctuated on its spectrum display.
  With MPD set by hand and nothing sent over USB, our tone faded: spread 13.7 dB, dips to −22.7 dB.
- With MPD set by hand, every run-sheet command sent over USB kept it fading, including `WGN:40` and
  `MPG:40`. The fading rate stayed at MPD's (about 2.6-3.0 median crossings/s; MPG's 0.1 Hz would be
  about ten times slower). `MPD:0` over USB did raise the noise.

**Finding: on this IONOS (firmware 2.03) a channel-type command over USB (`WGN:`/`MPG:`/`MPM:`/`MPP:`/
`MPD:`) changes the display and the S:N, but not the channel processing**: the processing stays in the
mode last chosen with the knob (WGN from power-up). The frequency offset over USB had no effect either.
- **The white-noise results stand**: the IONOS was in WGN from power-up throughout, the knob was never
  moved, and the S:N was set over USB, which works.
- **The 15 ccir-vara-50k runs were white noise** at those settings. Kept on the bench and in the data,
  marked invalid for fading; not used.
- For others: an IONOS driven over USB should be checked with a tone
  before trusting a fading run (`fadetest.py`).

**Decisions (operator, 21 Nov):**
- **Protocol: N5TW's sweep plus MPM.** MPG, MPM and MPP, 2 paths, IONOS S:N 30, 25, 20, 15, 10, 5, 0:
  50 KB at 30-20, 5 KB at 15-0, 2 runs each (42 runs per modem), the same for every modem. Measured S:N
  is the axis, as before.
- **The channel is set with the knob.** Runs are grouped by channel; at each change the bench pauses,
  the operator turns the knob, and a tone check confirms the fading before the runs go on.

Also seen: the IONOS level meter went red once at about 03:20-03:35 UTC while VARA run 16's session was
still sending after the chain was stopped; it cleared when both VARAs were stopped.

## Planned next

> **Superseded 13 Nov 2026 by [test-plan.md](test-plan.md)**, which covers the remaining modems, the metric changes and the open decisions. The items below are kept for the record.

- **Replace the Sabrent** with a second adapter of the Syba's model, since a
  different port didn't fix its input (qam02). Then recalibrate: the tone check,
  then `hfbench audio qam --snr 40 40 40` until all four paths agree within about
  1 dB MER, with flat MER across the carriers. Also check that every plug is
  fully seated at each step, and re-run the tone check after any cable is moved. **Acceptance for the bench:** all four paths
  within about 1 dB MER of each other, before any modem results count.
- Then re-run WGN 20 and WGN 25 to see whether the ARDOP direction asymmetry and
  the corruption go away.
- **WGN 15** (about 9 dB true S:N): what does ARDOP do below the threshold?
- Possibly a receive-level check: raise both microphones by about 6 dB and keep
  the S:N the same. Drive level stays at 90, because it changes the true S:N.
