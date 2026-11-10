# Log formats

These formats were observed in Winlink Express 1.8.6.0 and ARDOP_Win 1.0.2.9 logs (10 Nov 2026). The parser is `src/hfbench/logparse.py`, and redacted samples from both ends of each session are in `tests/fixtures/`.

The bench runs two Winlink Express installs on one Windows machine:

| Install | Winlink session log | ARDOP TNC logs |
| --- | --- | --- |
| Station 1 | `C:\RMS Express\<CALL>\Logs\RMS Express YYYYMMDD.log` | `C:\RMS Express\Logs\ARDOP_WinTNC_*_YYYYMMDD.log` |
| Station 2 | `C:\RMS Express 2\<CALL>\Logs\RMS Express YYYYMMDD.log` | `C:\RMS Express 2\Logs\ARDOP_WinTNC_*_YYYYMMDD.log` |

All files are UTF-8 with a BOM and CRLF line endings, with occasional lone CRs. All timestamps are UTC.

## Winlink Express session log

Each line has this form:

```text
YYYY/MM/DD HH:MM:SS <winlink version> <text>
```

An entry can run onto following lines that have no timestamp. Session lines carry a transport tag, for example `Ardop P2P`. The parser reads the tag from the `Connected` line, so other modems' tags are expected to work but haven't been confirmed yet.

| Line (after the tag) | Meaning |
| --- | --- |
| `*** Connected to Peer: CALL @ ts  USB Dial: 7098.500` | Session start |
| `   FC EM <MID> <uncompressed> <compressed> 0` | B2F proposal. A 3-space indent means the local station is sending; no indent means the peer is. |
| `*** Sending <MID>.` … `*** Completed send of message <MID>` | Start and end of a local send |
| `*** Sent 1 message.  Bytes: N,  Time: mm:ss,  bytes/minute: X` | Statistics for the send. Bytes are compressed bytes plus B2F overhead. |
| `*** Receiving <MID>` … `*** <MID> - unc/comp bytes received` | Start and end of a receive |
| `*** Bytes: N,  Time: mm:ss,  bytes/minute: X` | Statistics for the receive |
| `*** --- End of session with CALL at ts ---` | End of the B2F exchange |
| `*** Messages sent: n.  Total bytes sent: …` and `Messages Received: …, Total session time: mm:ss` | Session totals |
| `*** Disconnected from Peer: CALL @ ts` | Link down |
| `*** Session: 50.1 min;  Avg Throughput: N Bytes/min;  1 Min Peak Throughput: N Bytes/min` | Final summary, which closes the session |

The Winlink log has **no modem-level detail**: no modulation, retries or measured S:N.

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

These are enough for a rate-adaptation timeline. The log also contains **raw payload bytes**, so treat it as binary. It isn't parsed yet.
