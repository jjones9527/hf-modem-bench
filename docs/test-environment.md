# Test environment

This records the bench as it stood for the report. Items marked **(auto)** were read from the bench machine on 11 Nov 2026 with read-only queries; **(TBC)** items are still to be confirmed. The report will be published. The stations are **VA3ZTF** (station 1) and **VE3XZQ** (station 2), and the owner is happy for them to appear. The computer name and serial numbers are left out.

## Host computer (auto)

| Item | Value |
| --- | --- |
| Hardware | Apple Mac mini 2018 (Macmini8,1), running Windows through Boot Camp |
| CPU | Intel Core i5-8500B, 6 cores and 6 threads, 3.0 GHz |
| RAM | 8 GB |
| Firmware | Apple 2103.160.2.0.0 (iBridge 24.16.6005.0.0) |
| OS | Windows 10 Pro 22H2, build 19045.2965, 64-bit |
| Time zone | Eastern. All bench logs are in UTC. |
| Power plan | Balanced |
| USB selective suspend | **Enabled** on AC and battery. See notes. |
| Display off / sleep / hibernate (AC) | **Never** (set 12 Nov 2026, from 10 min / 30 min / never), so unattended runs can be watched and the machine can't sleep mid-run |
| Windows Time service | **Stopped**. See notes. |

## Audio interfaces (auto, except where noted)

| | Station 1 | Station 2 |
| --- | --- | --- |
| Windows name | "USB Audio Device" | "C-Media USB Audio Device" |
| USB ID | 0D8C:0014 (C-Media) | 0D8C:0008 (C-Media) |
| Driver | Microsoft class driver `wdma_usb.inf` 10.0.19041.2604 | same |
| Make of the adapter | **Sabrent** (model **TBC**) | **Syba** (model **TBC**) |
| Shared-mode format | 48 kHz (WASAPI default) | 48 kHz |
| Microphone AGC | Off (since 10 Nov) | Off |
| Output channel used | Right only (Windows balance L 0 / R 100) since swap02; left only before | Left only (L 90 / R 0) since swap02; right only before |
| IONOS channel | Ch1 since swap02; Ch2 before | Ch2 since swap02; Ch1 before |

The two columns are the **adapters**. From wgn25a (12 Nov) on, the ARDOP
instances were swapped: station 1 (VA3ZTF) uses the Syba and station 2
(VE3XZQ) the Sabrent. [results-log.md](results-log.md) has the bench state
for each campaign. The Sabrent was moved to a different USB port on the Mac
mini itself, not through a hub, on 12 Nov after the qam01 test.

**Cabling:** two 3.5 mm stereo *headphone-style* Y splitters. Each joins both stations to one IONOS jack, input or output, with every plug and jack stereo. There are **no isolation transformers**. The cabling's effects are described in [bench-setup.md](bench-setup.md).

## Channel simulator

| Item | Value |
| --- | --- |
| Unit | Teensy IONOS HF/VHF-UHF simulator (KN6KB / KA6IQA), Teensy 4.0 |
| Firmware | **2.03** (read from the unit, 12 Nov 2026) |
| Control | USB serial on COM3 (USB ID 16C0:0483). Lines end in LF or CR+LF. |
| Mode | Half duplex, symmetric, one unit; 3 kHz bandwidth; 2-path for the MP* presets |
| Gains (saved to EEPROM) | Since 11 Nov (swap02): **CH1 IN 50** (Sabrent), **CH2 IN 2** (Syba). Before that: CH1 IN 1, CH2 IN 20. CH1 and CH2 OUT were never changed, so presumably the default of 1 (**TBC**). |

## Software (auto)

| Software | Version | Notes |
| --- | --- | --- |
| Winlink Express | 1.8.6.0 | Two installs: `C:\RMS Express` (station 1) and `C:\RMS Express 2` (station 2) |
| ARDOP_Win TNC | 1.0.2.9 | Bundled with Winlink Express, one per install. Settings below. |
| VARA HF | 4.09.0001 | Two installs: `C:\VARA` and `C:\VARA 2`. **Not yet registered.** One key exists, for VA3ZTF; whether it may be used on the VE3XZQ instance is **TBC**. Bandwidth **TBC**. |
| VARA FM | 4.04.0001 | Installed; not part of the HF comparison |
| Data2G | 0.4.2 | Two installs: `C:\Program Files\Data2G` and `Data2G 2`. Connected through its VARA-compatible TNC, so **Winlink logs it as "VARA HF"**. |
| Mercury HF modem | 1.9.23 (Rhizomatica) | Two installs: `C:\Program Files\MercuryHF` and `MercuryHF 2`. Connected through its VARA-compatible interface, so **Winlink logs it as "VARA HF"**. |
| Python | 3.12.10 | With hfbench 0.1.0, sounddevice 0.5.6, numpy 2.5.4, pyserial 3.5 |

### ARDOP_Win TNC settings (identical on both stations)

| Setting | Value |
| --- | --- |
| ARQ bandwidth | `2000MAX` |
| Drive level | 90 |
| Leader length | 160 ms |
| Trailer length | 0 |
| Squelch, busy detect | 5, 5 |
| Tuning range | 100 Hz |
| Connect-request repeats, ARQ timeout | 10, 60 s |
| CW ID | on |
| Ping ACK | on |
| SlowCPU | off |

## Workload

The payload set `Text_50KB` is 10 files of 51,200 bytes (set SHA-256 `3ec10a0b…0279f9`), committed in `payloads/`. Each run sends five messages from each station, each with one attachment. See [test-protocol.md](test-protocol.md) §4.

## Calibration

The tone check and the true-S:N measurement are in [bench-setup.md](bench-setup.md). In summary:
- The transmit levels match within 1.1 dB and the receive levels within 0.7 dB.
- For ARDOP's 2000 Hz data frames, the real S:N is about 6 dB below the IONOS setting (about 14 dB at WGN 20), and the two directions are within 0.2 dB of each other. Control frames are about 1–2 dB below the setting.
- Each microphone's own noise is 38 dB below the IONOS reference.

## Notes for the report

- **VARA HF registration decides whether its results are fair.** Unregistered VARA HF is speed-limited; users report it stays at speed level 3–4. A comparison is only valid with registered VARA at **both** ends. Registration is keyed to a callsign. Whether a key issued for VA3ZTF may be used on the second instance (VE3XZQ), or whether a bench licence is available, is a question for the VARA author. **Don't publish VARA results until this is settled.** Data2G and Mercury are separate programs and aren't affected.
- **Three modems appear as "VARA HF" in Winlink logs** (VARA, Data2G and Mercury). The modem for each run comes from the run sheet and manifest, never from the log. `hfbench run` should also record which program held the TNC port when the session started; see test-protocol §7.
- **TNC port clash.** VARA-compatible TNCs use TCP 8300 and 8301 by default, but station 2's ARDOP TNC is configured on **8300**. Give each station's VARA-type modem its own ports (for example 8300/8301 for station 1 and 8400/8401 for station 2). Close the ARDOP TNCs before running a VARA-type session.

- **USB selective suspend is on.** Windows can briefly power down idle USB devices, and USB audio dongles are known to drop out or click when that happens. Consider turning it off for the campaign: Power Options → USB settings. Record the choice either way.
- **Windows Time is stopped.** Every log and timestamp comes from this one machine, so the logs line up with each other regardless. The UTC timestamps can still drift from true UTC; it was about 0.5 s on 10 Nov.
- **Balanced power plan.** CPU frequency scaling is unlikely to matter for these modems on a 6-core CPU. Record it, or switch to High performance for consistency.
- **Audio-only bench.** There's no transmitter ALC or PA linearity, and no receiver AGC. See the limitations in [test-protocol.md](test-protocol.md).

## ARDOP busy detector off (13 Nov 2026)

Both ARDOP_Win TNCs run with **BusyDet = 0** (busy-channel detector off) from 13 Nov
21:50 UTC; it was 5 (the default) before. With very little IONOS noise (WGN 40) the
detector read the bench's own uneven noise as a busy channel and ARDOP never called
(results log, sweep incident). There is no other station on the bench. Change it only
with ARDOP closed: it rewrites its ini on exit (`scripts/windows/busydet_off.ps1`).
