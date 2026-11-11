# Test environment

This records the bench as it stood for the report. Items marked **(auto)** were read from the bench machine on 11 Nov 2026 with read-only queries; **(TBC)** items are still to be confirmed. Callsigns, the computer name and serial numbers are left out on purpose.

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
| Windows Time service | **Stopped**. See notes. |

## Audio interfaces (auto, except where noted)

| | Station 1 | Station 2 |
| --- | --- | --- |
| Windows name | "USB Audio Device" | "C-Media USB Audio Device" |
| USB ID | 0D8C:0014 (C-Media) | 0D8C:0008 (C-Media) |
| Driver | Microsoft class driver `wdma_usb.inf` 10.0.19041.2604 | same |
| Make and model of the adapter | **TBC** | **TBC** |
| Shared-mode format | 48 kHz (WASAPI default) | 48 kHz |
| Microphone AGC | Off (since 10 Nov) | Off |
| Output channel used | Left only (Windows balance) | Right only |
| IONOS channel | Ch2 | Ch1 |

**Cabling:** two 3.5 mm stereo *headphone-style* Y splitters. Each joins both stations to one IONOS jack, input or output, with every plug and jack stereo. There are no isolation transformers (**TBC**). The cabling's effects are described in [bench-setup.md](bench-setup.md).

## Channel simulator

| Item | Value |
| --- | --- |
| Unit | Teensy IONOS HF/VHF-UHF simulator (KN6KB / KA6IQA), Teensy 4.0 |
| Firmware | **TBC** (the manual covers rev 2.03; the version shows on the power-on screen) |
| Control | USB serial on COM3 (USB ID 16C0:0483). Lines end in LF or CR+LF. |
| Mode | Half duplex, symmetric, one unit; 3 kHz bandwidth; 2-path for the MP* presets |
| Gains (saved to EEPROM) | CH1 IN 1, CH2 IN 20, CH OUT at defaults (**TBC**) |

## Software (auto)

| Software | Version | Notes |
| --- | --- | --- |
| Winlink Express | 1.8.6.0 | Two installs: `C:\RMS Express` (station 1) and `C:\RMS Express 2` (station 2) |
| ARDOP_Win TNC | 1.0.2.9 | Bundled with Winlink Express, one per install. Settings below. |
| VARA HF | 4.09.0001 | Two installs: `C:\VARA` and `C:\VARA 2`. Registration and bandwidth **TBC**; no settings file yet. |
| VARA FM | 4.04.0001 | Installed; not part of the HF comparison |
| Data2G | 0.4.2 | Two installs: `C:\Program Files\Data2G` and `Data2G 2`. Connected through its VARA-compatible TNC. |
| Mercury HF modem | 1.9.23 (Rhizomatica) | Two installs: `C:\Program Files\MercuryHF` and `MercuryHF 2`. How it connects to Winlink is **TBC**. |
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
- For ARDOP, the real S:N equals the IONOS setting within about 1 dB in both directions.
- Each microphone's own noise is 38 dB below the IONOS reference.

## Notes for the report

- **USB selective suspend is on.** Windows can briefly power down idle USB devices, and USB audio dongles are known to drop out or click when that happens. Consider turning it off for the campaign: Power Options → USB settings. Record the choice either way.
- **Windows Time is stopped.** Every log and timestamp comes from this one machine, so the logs line up with each other regardless. The UTC timestamps can still drift from true UTC; it was about 0.5 s on 10 Nov.
- **Balanced power plan.** CPU frequency scaling is unlikely to matter for these modems on a 6-core CPU. Record it, or switch to High performance for consistency.
- **Audio-only bench.** There's no transmitter ALC or PA linearity, and no receiver AGC. See the limitations in [test-protocol.md](test-protocol.md).
