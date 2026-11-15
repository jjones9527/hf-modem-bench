# Log formats

These formats were observed in Winlink Express 1.8.6.0, ARDOP_Win 1.0.2.9 and Mercury 1.9.23 logs (10–15 Nov 2026). The parser is `src/hfbench/logparse.py`, and redacted samples from both ends of each session are in `tests/fixtures/`.

The bench runs two Winlink Express installs on one Windows machine:

| Install | Winlink session log | ARDOP TNC logs |
| --- | --- | --- |
| Station 1 | `C:\RMS Express\<CALL>\Logs\RMS Express YYYYMMDD.log` | `C:\RMS Express\Logs\ARDOP_WinTNC_*_YYYYMMDD.log` |
| Station 2 | `C:\RMS Express 2\<CALL>\Logs\RMS Express YYYYMMDD.log` | `C:\RMS Express 2\Logs\ARDOP_WinTNC_*_YYYYMMDD.log` |

All files are UTF-8 with a BOM and CRLF line endings, with occasional lone CRs. All Winlink and ARDOP timestamps are UTC (Mercury's own log is the exception; see below).

## Winlink Express session log

Each line has this form:

```text
YYYY/MM/DD HH:MM:SS <winlink version> <text>
```

An entry can run onto following lines that have no timestamp. Session lines carry a transport tag: `Ardop P2P` for ARDOP, `Vara HF P2P` for every VARA-protocol modem (VARA HF, Mercury, Data2G). The two are written differently:

```text
2026/11/14 00:02:30 1.8.6.0 *** Ardop P2P *** Receiving GWSDGJQ0GHSZ
2026/11/15 03:15:05 1.8.6.0 Vara HF P2P *** Sending 1LXNP3DKWQQB.
2026/11/15 03:14:41 1.8.6.0 Vara HF P2P    FC EM 1LXNP3DKWQQB 51439 42215 0
```

VARA-style lines have no leading `***`; the parser rewrites them to the ARDOP form
(confirmed with Mercury, 15 Nov; fixture `tests/fixtures/vara_p2p/`).

| Line (after the tag) | Meaning |
| --- | --- |
| `*** Connected to Peer: CALL @ ts  USB Dial: 7098.500` (ARDOP) or `*** Peer-to-Peer Vara Connection to\|from CALL @ ts  USB Dial: 7098.500` (VARA) | Session start |
| `   FC EM <MID> <uncompressed> <compressed> 0` | B2F proposal. A 3-space indent means the local station is sending; no indent means the peer is. |
| `*** Sending <MID>.` … `*** Completed send of message <MID>` | Start and end of a local send |
| `*** Sent 1 message.  Bytes: N,  Time: mm:ss,  bytes/minute: X` | Statistics for the send. Bytes are compressed bytes plus B2F overhead. |
| `*** Receiving <MID>` … `*** <MID> - unc/comp bytes received` | Start and end of a receive |
| `*** Bytes: N,  Time: mm:ss,  bytes/minute: X` | Statistics for the receive |
| `*** --- End of session with CALL at ts ---` | End of the B2F exchange |
| `*** Messages sent: n.  Total bytes sent: …` and `Messages Received: …, Total session time: mm:ss` | Session totals |
| `*** Disconnected from Peer: CALL @ ts` | Link down |
| `*** Session: 50.1 min;  Avg Throughput: N Bytes/min;  1 Min Peak Throughput: N Bytes/min` (ARDOP) or `… 1 Min Peak: N Bytes/min; Average SNR: x dB` (VARA) | Final summary, which closes the session |
| `*** Link Error - Received data stream not correct format. ByteIndex=N` | B2F framing rejected the received data: counted as **corrupted** |
| `*** P2P session inactivity timeout.  Disconnecting.` | Winlink's 5-min P2P timer fired (VARA-protocol sessions; see test-protocol §7) |
| `*** Rejected 1 message as duplicate.` / `Message Id: <MID> rejected - moved to sent items folder.` | The receiver already had the message (Message-ID seen) |

The Winlink log has **no modem-level detail**: no modulation, retries or measured S:N (VARA sessions end with the modem's own average S:N estimate).

## Winlink VARA command log (`<CALL>\Logs\Vara YYYYMMDD.log`)

Written when "Log Vara commands" is on (VARA TNC setup). One line per command sent
(`Out:`) or line received (`In:`) on the modem's control port, plus status changes:

```text
2026/11/15 03:37:45 Out: CONNECT VE3XZQ VA3ZTF
2026/11/15 03:37:53 In: CONNECTED VE3XZQ VA3ZTF 2750
2026/11/15 03:07:43 In: BITRATE (17) 1409 BPS
```

It **leaves out `BUFFER` and `PTT` lines** (15 Nov: the relay saw 156 BUFFER and 44 PTT
lines in a session where this log showed none), and it has no data-port record. Use the
relay log for those.

## Bench relay log (`hfbench\relay-<stamp>.log`)

Written by `scripts/vara_relay.py`, between station 2's Winlink and its modem:

```text
2026-11-15 17:12:35.847 DAT host>modem 42532 bytes
2026-11-15 17:14:46.288 CTL modem>host BUFFER 31032
2026-11-15 17:17:35.877 CTL host>modem DISCONNECT [HELD: host idle 300 s, modem BUFFER 12632; answered OK, not passed on]
```

UTC to the millisecond; `CTL` lines are every control-port line both ways, `DAT` lines
the size of each data-port chunk (contents aren't logged).

## Mercury engine log (`C:\Program Files\MercuryHF[ 2]\logs\mercury_engine.log`)

Written by the Mercury GUI, one file per install, **in local time** (Eastern) unless
`log_utc = true`. Useful lines: `[radio] TX enabled (PTT ON)` / `TX disabled (PTT OFF)`
(transmit times, used to key the S:N measurement), `[arq] Connected to CALL`,
`[arq-timing] connect mode=…`, `[arq-fsm] … DISCONNECT deferred until delivered`, and the
per-session `disconnect reason=… tx_bytes=… rx_bytes=…` summary. Several copies of the
GUI writing to the same file mixes their lines.

## ARDOP ARQ session statistics (`ARDOP_WinTNC_ARQSession_*.log`)

One block is written at each disconnect:

```text
YYYY-MM-DD HH:MM:SS [ver] *** ARQ session stats with CALL (N.N minutes) ***
```

The block then contains these fields:

- Session Bandwidth and Measured Round Trip
- `AvgLeader S:N(3KHz noise BW)`: the S:N as received **by this station**
- Good and Failed Frame Type Decodes
- Total Bytes Sent and Received, and Session Throughput
- per-modulation `Avg <mod> Quality=q on n frames`
- Mode Shift UPs and DOWNs, and Link Turnovers

`match_ardop()` pairs each block with the Winlink session that has the same peer and a disconnect time within 30 s.

## ARDOP debug log (`ARDOP_WinTNC_Debug_*.log`)

Each line has the form `HH:MM:SS.mmm [Component] text`. The line holds the time of day only, so the date comes from the filename. The log contains:

- each frame sent and received (`[Main.SendFrame] Send 16QAM.2000.100.O` and `[Frame Type OK]`, with S:N and frequency offset)
- gear-shift decisions (`Gearshift_9 … AvgQuality=…`)
- quality values reported in ACKs

These are enough for a rate-adaptation timeline. The frame types per run (results log, "Frame Type OK" counts) were counted from it with a short script; it isn't parsed by hfbench yet. The log also contains **raw payload bytes**, so treat it as binary.
