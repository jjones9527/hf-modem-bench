# ARDOP_Win 1.0.2.9: corrupted data frames pass the per-carrier check and reach Winlink

Bug report for the ARDOP developers (16 Nov 2026), from VA3ZTF's HF modem bench tests,
10–15 Nov 2026. The full record is in [results-log.md](../results-log.md) ("ARDOP 1.0.2.9
source" and "oneway28").

| | |
|---|---|
| Affects | ARDOP_Win 1.0.2.9 as shipped with Winlink Express 1.8.6.0; seen in 16QAM.2000 and 8PSK.2000 |
| Severity | The session is lost and the message must be resent. No bad data was delivered: Winlink's B2F checksum caught every case. |
| Status | Appears to be addressed by the parity-verification experiment in the 1.0.3.x development code. Not yet tested on this bench. |

## Summary

At good S:N (about 15–18 dB), ARDOP 1.0.2.9 occasionally hands Winlink a data frame
containing a few symbol errors. Every frame of the affected message decodes PASS on
the first try with no NAKs. Winlink then fails the message with a checksum, decompress
or B2F framing error, and the session ends.

Two things in `CorrectRawDataWithRS` and `GenCRC16FrameType` combine to let these
errors through:
- a carrier is accepted on its 16-bit CRC alone, and the Reed-Solomon parity is never
  checked when the CRC passes;
- the CRC constant is `&H8810`, not the CCITT `&H1021` its comment names, and it misses
  short symbol-error bursts far more often.

The RS parity already in every frame would have caught every corrupted carrier we found.

## Test setup

- Two Winlink Express 1.8.6.0 installs on one Windows 10 PC, each running its own
  ARDOP_Win 1.0.2.9 TNC (DriveLevel 90, ARQ bandwidth 2000MAX, busy detector off),
  connected through a Teensy IONOS HF simulator (firmware 2.03), WGN, 3 kHz bandwidth,
  one USB audio adapter per station.
- Peer-to-peer B2F sessions, one way, 10 messages per run, each with a 51,200-byte text
  attachment (about 42,100 bytes compressed).
- S:N is measured from the received audio of ARDOP's data frames, not the IONOS setting.
- Every delivered attachment is compared byte for byte with the original. When a
  message fails, Winlink's partial file (`Partials\<MID>.bin`) is decoded and compared
  with the exact compressed stream that was sent, which a re-run of the same LZHUF
  coder reproduces.

## What we see

| Mode | Measured data S:N | Messages | Failed | Winlink error |
|---|---|---|---|---|
| 16QAM.2000 | 17.9–18.4 dB | 57 | 5 (8.8%) | 4× "Checksum error. Failed to assemble correct binary image"; 1 stall (all bytes arrived; probably the same error landing in the B2F framing) |
| 16QAM.2000 | 21.9 dB | 30 | 0 | none |
| 8PSK.2000 | 15.4 dB | 22 | 2 | 1× checksum error; 1× "Received data stream not correct format. ByteIndex=104679" |

In every failed message, ARDOP's log shows each data frame decoded PASS on the first
try (16QAM quality 61–66), with no NAK around the bad frame. Failures were the same in
both directions and on both adapters. All 224 attachments that were delivered are
byte-identical to the original.

### The received bytes

Decoding the partial file and comparing it with the stream that was sent shows a
handful of wrong bytes packed into one short span. That's one carrier's worth, and
each error is a whole-symbol confusion:

| Message (mode) | Wrong bytes | Within | Error pattern |
|---|---|---|---|
| S176LKCKL8SF (16QAM) | 2 | 63 bytes | `1010 → 1001` in the high nibble, then the low nibble |
| RY0VDQU1TRYD (16QAM) | 4 | 104 bytes | each error confined to one nibble |
| TL9R5WJVJWYT (16QAM) | 5 (6 symbols) | 110 bytes | XOR `0001, 0001, 0011, 0001, 0011 0001` |
| 697OUUYZHTAB (16QAM) | 4 | 46 bytes | XOR `0001 0000, 0001 0000, 0001, 0001` |
| KI7L6KOQNGPV (8PSK) | 7 | 78 bytes | XOR patterns of 1–3 adjacent bits |

Everything else in each message arrived intact: for example 41,992 of 41,994 bytes in
the first case. These are demodulation symbol errors that got past the carrier check.
They aren't lost, repeated or reordered data.

## Cause in the source

Source: the ARSFI ARDOP_Win repository at commit `bc11cb3` (20 Jul 2026), whose
AssemblyInfo is 1.0.2.9.

**1. RS parity is skipped whenever the CRC passes.** In `DemodulateDecode12K.vb`,
`CorrectRawDataWithRS`, each carrier holds a byte count, data, a 2-byte CRC and RS
parity. A 16QAM carrier is 1 + 128 + 2 + 64 bytes. If the CRC over count + data
matches, the carrier is accepted. Only when the CRC fails does RS correct (up to 32 byte
errors), after which the CRC is checked again. A carrier whose errors happen to satisfy
the CRC is therefore never looked at by RS, and RS quietly fixing the other carriers
leaves no NAK or log trace.

**2. The CRC is not CRC-16-CCITT.** In `Globals.vb`, `GenCRC16FrameType` /
`CheckCRC16FrameType` are commented as CRC-16-CCITT (x¹⁶ + x¹² + x⁵ + 1). But the
left-shifting routine XORs with `&H8810`, where CCITT needs `&H1021`. `&H8810` is the
generator x¹⁶ + x¹⁵ + x¹¹ + x⁴. It has no +1 term and is divisible by x⁴, which weakens
its detection of short error bursts.

A bit-for-bit port of the routine ([scripts/ardop_crc_sim.py](../../scripts/ardop_crc_sim.py)),
with random 16QAM symbol (nibble) errors put into a 129-byte carrier, 200,000 trials
per row:

| Symbol errors in one carrier | 1.0.2.9 CRC (`&H8810`) misses | CRC-16-CCITT (`&H1021`) misses |
|---|---|---|
| 1 | never | never |
| 2 | 1 in 8,300 | never |
| 4 | 1 in 2,700 | 1 in 67,000 |

A 16QAM message is about 42 frames × 8 carriers, roughly 340 carrier checks. At about
18 dB on this bench many carriers carry a few symbol errors, so an escape rate of 1 in
3,000–8,000 gives a failed message every 10–25 messages. That's the rate observed. At
22 dB there are fewer symbol errors to miss, and we saw none in 30 messages.

With 64 parity bytes per carrier, each corrupted carrier above (2–7 wrong bytes) was
well within what RS can detect and correct. Checking the parity that is already sent
would have rejected or repaired every one of them.

## The development code

The current 1.0.3.x development code has the note "2026-10-10 LAB EXPERIMENT: Verify
parity as well as CRC for every carrier" in `CorrectRawDataWithRS`, and accepts a
carrier only when the RS parity verifies *and* the CRC matches. That matches the cause
above. It is receiver-side only, so it stays compatible on the air with 1.0.2.9
stations. The CRC constant is unchanged there; changing it would break on-air
compatibility, so it seems best left for a future protocol revision.

We haven't run the development build yet. It's planned as the last stage of these
tests, on the same S:N points as 1.0.2.9.

## Suggested fix

1. Release the parity-verification change: accept a carrier only when RS reports no
   errors (or corrects them) *and* the CRC then matches.
2. Correct the CRC comment in `Globals.vb` to name the polynomial actually used. If the
   frame format is ever revised, use `&H1021`.
3. Consider logging a counter of carriers corrected by RS per session, so symbol errors
   are visible in the session statistics.

## Data available

Partial files, both stations' Winlink logs and ARDOP debug logs for each failed message,
and the S:N recordings are available on request. Tools:
[scripts/ardop_crc_sim.py](../../scripts/ardop_crc_sim.py) (CRC escape simulation) and
[scripts/check_partial.py](../../scripts/check_partial.py) (decodes a Winlink partial and
lists the wrong bytes).
