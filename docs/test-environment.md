# Test environment

This records the bench as it stood for the report (last reviewed 15 Nov 2026). Items marked **(auto)** were read from the bench machine with read-only queries; **(TBC)** items are still to be confirmed. The report will be published. The stations are **VA3ZTF** (station 1) and **VE3XZQ** (station 2), and the owner is happy for them to appear. The computer name and serial numbers are left out.

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
| Windows name | "USB Audio Device" (re-detected as "3- USB Audio Device") | "C-Media USB Audio Device" |
| USB ID | 0D8C:0014 (C-Media) | 0D8C:0008 (C-Media) |
| Driver | Microsoft class driver `wdma_usb.inf` 10.0.19041.2604 | same |
| Make of the adapter | **Sabrent** (model **TBC**) | **Syba** (model **TBC**) |
| Shared-mode format | 48 kHz (WASAPI default) | 48 kHz |
| Microphone AGC | Off (since 10 Nov) | Off |
| Output channel used | Right only (Windows balance L 0 / R 100) since swap02; left only before | Left only (L 90 / R 0) since swap02; right only before |
| Windows levels since cal7 (12 Nov; read 15 Nov) | speaker 50%, right only; microphone 75%, mono | speaker 17%, left only; microphone 35%, mono |
| IONOS channel | Ch1 since swap02; Ch2 before | Ch2 since swap02; Ch1 before |

The two columns are the **adapters**. From wgn25a (12 Nov) on, the ARDOP
instances were swapped: station 1 (VA3ZTF) uses the Syba and station 2
(VE3XZQ) the Sabrent, and every modem since uses the same pairing (station 1: C-Media/Syba,
station 2: USB Audio Device/Sabrent). The Windows volume and balance belong to the
device, so they apply to every modem. Both microphones capture in mono.
[results-log.md](results-log.md) has the bench state
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
| VARA HF | 4.09.0001 | Two installs: `C:\VARA` (TCP 8300) and `C:\VARA 2` (TCP 8310). One registration key, for VA3ZTF, entered in both; the operator found on 15 Nov that **the same licence can't be used on both stations** (D2 still open). ALC drive level −5 in both; level not yet set to the reference. Busy detector found **on** (BUSY ON/OFF seen 15 Nov): turn off before testing. |
| VARA FM | 4.04.0001 | Installed; not part of the HF comparison |
| Data2G | 0.4.2 | Two installs: `C:\Program Files\Data2G` and `Data2G 2`. Connects through its VARA-compatible TNC, so Winlink logs it as **"Vara HF P2P"**. Not yet brought up. |
| Mercury HF modem | 1.9.23 (Rhizomatica, git 09f258f8) | Two installs: `C:\Program Files\MercuryHF` and `MercuryHF 2`. Connects through its VARA-compatible interface, so Winlink logs it as **"Vara HF P2P"**. Settings below. |
| Python | 3.12.10 | With hfbench 0.1.0, sounddevice 0.5.6, numpy 2.5.4, pyserial 3.5. Also runs the bench relay (`scripts/vara_relay.py`). |

### ARDOP_Win TNC settings (identical on both stations)

| Setting | Value |
| --- | --- |
| ARQ bandwidth | `2000MAX` |
| Drive level | 90 |
| Leader length | 160 ms |
| Trailer length | 0 |
| Squelch, busy detect | 5, **0** (off since 13 Nov; 5 before) |
| Tuning range | 100 Hz |
| Connect-request repeats, ARQ timeout | 10, 60 s |
| CW ID | on |
| Ping ACK | on |
| SlowCPU | off |

### Mercury 1.9.23 settings (15 Nov 2026)

| Setting | Station 1 (`MercuryHF`) | Station 2 (`MercuryHF 2`) |
| --- | --- | --- |
| Started | by hand (desktop icon "Mercury HF Modem"), GUI `mercury-ui.exe` | by hand (desktop icon "Mercury HF 2") |
| `arq_tcp_base_port` (control / data) | 8300 / 8301 | 8310 / 8311 |
| `broadcast_tcp_port`, `ui_port` | 8100, 10000 | 8110, 10010 |
| Sound card | C-Media (as ARDOP station 1) | USB Audio Device (as ARDOP station 2) |
| `tx_gain_db` | **+3.5** | **+3.0** |
| `busy_detect` | false | false |
| `[store] enabled` | true | false (one chat-history file per machine) |

Each GUI reads and writes `mercury.ini` in its own folder; station 2's original is
kept as `mercury.ini.orig`. The transmit gains put Mercury's average power at the tone
reference (D5): −0.4 / 0.0 dB, IONOS Lvl 650–750 mV p-p. **Mercury's GUI can keep
running after its window is closed** (15 Nov): check for exactly one
`mercury-ui.exe` per station before a campaign (the campaign start script does).

### Winlink Express settings for VARA-protocol modems

Session type **Vara HF P2P**, automatic VARA launch **off**, "Log Vara commands" **on**
(`<CALL>\Logs\Vara YYYYMMDD.log`). VARA TNC port: station 1 **8300** (the modem
directly); station 2 **8320**, the bench relay, which passes everything to station 2's
modem on 8310 and holds Winlink's 5-minute P2P inactivity DISCONNECT (results-log.md,
"Workaround: relay holds the timer's DISCONNECT"). ARDOP doesn't use the relay.

## Workload

Two payload sets are committed in `payloads/`: `Text_50KB`, 10 files of 51,200 bytes
(set SHA-256 `3ec10a0b…0279f9`), and `Text_5KB`, their first 5,120 bytes (`85741279…384d4`).
From 13 Nov every run sends 10 messages one way, station 2 → station 1, each with one
attachment: Text_50KB at 10 dB and above, Text_5KB below. See [test-protocol.md](test-protocol.md) §4.

## Calibration

The tone check, the 16QAM path check and the true-S:N measurement are in
[bench-setup.md](bench-setup.md) and the results log. Current state (cal7 levels, 12 Nov;
rechecked before every campaign, last 15 Nov 17:34):
- Transmit vs the IONOS reference −0.2 / −0.3 dB at WGN 20; transmit mismatch +0.1 dB,
  receive mismatch +0.7 dB.
- 16QAM path 2 → 1: 22–23 dB MER at full level. Measured data S:N ceiling about 22 dB.
- Each microphone's own noise is 33 dB below the IONOS reference.
- A modem's measured S:N depends on its waveform: ARDOP's PSK frames arrive 2.7–6.2 dB
  below its 4FSK frames at the same drive; Mercury, set to the reference, measures close
  to the setting at high settings. The IONOS noise is not linear in the setting below
  about WGN 7.

## Notes for the report

- **VARA HF registration decides whether its results are fair.** Unregistered VARA HF is speed-limited; users report it stays at speed level 3–4. A comparison is only valid with registered VARA at **both** ends. Registration is keyed to a callsign, and the operator found on 15 Nov that the VA3ZTF licence can't be used on both stations. A key for VE3XZQ or a bench licence is a question for the VARA author. **Don't publish VARA results until this is settled.** Data2G and Mercury are separate programs and aren't affected.
- **Three modems appear as "Vara HF P2P" in Winlink logs** (VARA, Data2G and Mercury). The modem for each run comes from the run sheet and manifest, never from the log. Run only one VARA-protocol modem at a time.
- **TNC ports.** VARA-protocol modems use 8300/8301 at station 1 and 8310/8311 at station 2 (station 2's Winlink reaches its modem through the relay on 8320/8321). Station 2's ARDOP TNC also uses 8300, but it only runs with its Ardop P2P session window, so close that window before a VARA-protocol campaign.
- **Winlink Express P2P inactivity timer.** In a P2P session Winlink sends DISCONNECT after 5 minutes without writing to the modem's data port, even while the modem is still sending a message it was given. VARA HF and Mercury both then end the link after that message, and the receipt is lost. ARDOP isn't affected. The bench relay holds that DISCONNECT for VARA-protocol modems; every such result is labelled with it.

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
