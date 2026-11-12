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

## Planned next

- **WGN 20 with the devices swapped**, if wgn25a is clean: does the 16QAM direction
  follow the Sabrent → Syba hardware path, which would now be station 2 → 1?
- **WGN 15** (about 9 dB true S:N): what does ARDOP do below the threshold?
- Possibly a receive-level check: raise both microphones by about 6 dB and keep
  the S:N the same. Drive level stays at 90, because it changes the true S:N.
