# Results log — Stage 7: fading (MPG, MPM, MPP)

Part of the [results log](../results-log.md). All times UTC.

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

**VARA busy reports (21 Nov, 14:44-14:52 UTC).** On the first real fading runs (MPG) the operator saw VARA's
busy detect on. VARA HF has no switch for it (none in VARA.ini or its menus), and with fading it
reported `BUSY ON` to Winlink for about 1.5 s every 30 s; Winlink holds its call while BUSY is on. The
bench relay now drops the modem's BUSY ON/OFF lines (`vara_relay.py --drop-busy`, the relay's default
from 21 Nov 14:50, `relay-20261121-1450.log`): for Winlink that is busy detection off, as the plan asks.
Only station 2 (the caller) goes through the relay; station 1 answers regardless. Earlier: in VARA's
white-noise runs BUSY was reported about 10-40 times an hour, with connect times steady at 8-9 s;
Data2G's (17 Nov, no switch either) 100-340 an hour, connect 4-5 s. Those results weren't held up
measurably, and they stand.

### VARA HF on fading channels, MPG, MPM and MPP (21-24 Nov 2026)

IONOS channel set with the knob and checked with `ionos_fadetest.py` before each group: MPG spread
6-13 dB, 0.16-0.32 median crossings/s; MPM 11-12 dB, 0.8-0.95/s; MPP 15.8 dB, 1.37/s (MPD for comparison
about 3/s). Relay dropping VARA's BUSY reports. 2 runs per setting, net bit/s (per-message median in
brackets):

| IONOS S:N | MPG (good) | MPM (moderate) | MPP (poor) |
|---|---|---|---|
| 30 (50 KB) | 1,848 / 1,765 (1,876-1,944) | 1,685 / 1,694 (1,783-1,847) | 1,401 / 1,363 (1,426-1,548) |
| 25 (50 KB) | 1,606 / 1,637 (1,692-1,722) | 1,705 / 1,569 (1,675-1,809) | 1,347 / 1,345 (1,362-1,397) |
| 20 (50 KB) | 1,404 / 1,389 (1,442-1,454) | 1,408 / 1,414 (1,482-1,485) | 1,221 / 1,298 (1,280-1,387) |
| 15 (5 KB) | 824 / 768 | 775 / 770 | 783 / 762 |
| 10 (5 KB) | 505 / 450 | 512 / 497 | 593 / 557 |
| 5 (5 KB) | 214 / 205 | 264 / 215 | 220 / 247 |
| 0 (5 KB) | 115 / 111 | 129 / 128 | 136 / 136 |

**420 of 420 delivered, all identical; connect 8 s in every run.** MPG and MPM are within run-to-run
spread of each other at every setting. MPP costs 15-25 % at 20-30 dB; from 15 dB down it is level with
MPG and MPM (at 10 and 0 dB slightly ahead, by more than their run-to-run spread). The IONOS S:N is its
setting, the average over the fading; measured S:N from the recordings (to 24 Nov 04:24 UTC: MPP's last
four 5 KB runs fall after it) is still to do. Against N5TW's 2020 VARA on MPG (about 3.9, 2.6 and 1.6
kbit/s at 30, 25 and 20 dB), these are lower at the top and about equal at 20 dB; our VARA runs 5.4 dB
under the reference level (its peaks), so measured S:N will place them. One run (fade-vara-mpm-50k-0006)
hit a runner COM error while preparing and was run again after the 5 KB set. MPP was paused 22 Nov 06:40
UTC for other work and run 23-24 Nov (22:52-06:48 UTC), on the same Winlink Express 1.8.6.0.

### Data2G 0.5.1 on fading channels, MPG (26-27 Nov 2026)

**Level first.** The first MPG group ran at `output_volume=-1.0` (the WGN setting). At S:N 0 the operator
saw the IONOS Lvl stay above 1,200 mV p-p, over the protocol's limit: fading peaks are largest at low S:N.
That group was stopped (`fade-data2g-mpg-5k-0005` ended invalid) and both campaigns marked superseded;
the runs they completed (50 KB 1-6, 5 KB 1-4) are not results, because the level at the time is not known
to have been clean. Level checks at MPG S:N 0, one 5 KB run each, operator watching the meter:
`lvl-data2g-mpg-v3`/`-v3b` at -3.0 still reached about 1,300 mV p-p; `lvl-data2g-mpg-v5` at -5.0 stayed
under 1,000 (10/10 delivered, 257 bit/s net). Both stations now run at -5.0, set in
`hfbench\data2g\station{1,2}.conf` (`scripts/windows/hfbench_d2gvol.ps1`) so a restart keeps it. Every
Data2G fading campaign uses -5.0. Measured S:N is the axis, so the lower drive shows up there rather than
skewing the comparison.

**MPG redo** (`fade-data2g-mpg-50k-v2`, `fade-data2g-mpg-5k-v2`; same seeds and order), 26 Nov 23:47 to
27 Nov 03:28 UTC, tone check before the group. Measured S:N from the transmit log and station 1's
recording (`scripts/txlog_snr.py`), per run; net bit/s (per-message median in brackets):

| IONOS S:N | Payload | Measured S:N | Net bit/s |
|---|---|---|---|
| 30 | 50 KB | 22.9 / 24.0 dB | 4,254 (4,890) / 4,309 (4,890) |
| 25 | 50 KB | 20.7 / 20.3 dB | 3,778 (4,442) / 4,155 (4,719) |
| 20 | 50 KB | 17.7 / 17.3 dB | 3,031 (3,374) / 2,859 (3,136) |
| 15 | 5 KB | 13.5 / 13.1 dB | 1,417 (1,763) / 1,105 (1,167) |
| 10 | 5 KB | 9.8 / 10.0 dB | 1,066 (1,392) / 1,091 (1,477) |
| 5 | 5 KB | 4.2 / 4.8 dB | 589 (670) / 549 (628) |
| 0 | 5 KB | -0.7 / -0.6 dB | 274 (290) / 297 (309) |

**140 of 140 delivered, all identical; connect 4-5 s (one 20 s).** Net 3,632 bit/s over the 50 KB sessions,
571 over the 5 KB. Measured S:N is 6-7 dB under the setting at 25-30 and within 1.5 dB of it from 15 down
(at the top the modem's own signal level, now lower, limits it). Against VARA HF on the same preset
(above), net, by IONOS setting (VARA's measured S:N is still to do), Data2G is about 2.1-2.5 x faster at
20-30 dB, 1.6 x at 15, 2.3 x at 10, 2.7 x at 5 and 2.5 x at 0 dB. MPP and MPM follow at -5.0.
