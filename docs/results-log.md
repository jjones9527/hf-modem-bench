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

**Stations.** Station 1 is VA3ZTF (`C:\RMS Express`, Sabrent USB adapter) and
station 2 is VE3XZQ (`C:\RMS Express 2`, Syba USB adapter). Station 2 always
places the call.

**Workload.** The Text_50KB set (sha256 `3ec10a0b…279f9`). Each station sends
5 messages, each with one 51,200-byte text attachment, which compresses to about
42,100 bytes on the wire. Station 1 sends files 1–5 of the sorted set and
station 2 sends files 6–10.

**Goodput.** Compressed (FC EM) bytes × 8 divided by the message's transfer time
in the sender's Winlink log.

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
   stays at 8PSK. This differs from pilot01 (WGN 20 at the old, hotter
   levels, about 14 dB data S:N), where 16QAM was used. It is consistent with the lower cal7 levels
   giving a slightly lower data S:N than estimated (S:N recording below).
3. 20 of 20 messages delivered, none corrupted, all at 8PSK.2000 in both
   directions (the Sabrent → Syba path included).

---

## Planned next

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
