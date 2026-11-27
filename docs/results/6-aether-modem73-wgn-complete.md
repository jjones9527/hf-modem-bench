# Results log — Stage 6: Aether HF; Modem73; white-noise stage complete

Part of the [results log](../results-log.md). All times UTC.

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
