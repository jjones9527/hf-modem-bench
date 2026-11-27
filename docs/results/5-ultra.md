# Results log — Stage 5: ULTRA 0.6.2 (paused)

Part of the [results log](../results-log.md). All times UTC.

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
