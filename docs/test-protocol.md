# Test protocol

Status: **draft**. Items marked **TBD** depend on the open questions at the end.

Simulator references are to the *Teensy IONOS HF/VHF-UHF Channel Simulator* manual, rev 2.03 (KN6KB, 25 Nov 2020), and to N5TW's *A comparison of Winlink digital mode performance… Take Three* (Nov 2020). Both are available from winlink.org/content/ionos_simulator.

## 1. Purpose and scope

The aim is to compare software HF modems used with Winlink Express on a repeatable bench. Two Winlink Express instances run peer-to-peer sessions through one IONOS simulator. Between runs only two things change: the modem and the simulator settings. This is the method N5TW used, which makes his published curves a useful sanity check.

**Modems in scope:** VARA HF, ARDOP, Data2G (through its VARA-compatible TNC) and possibly Mercury. Versions are TBD and are recorded per run. Pactor is out of scope because it needs dedicated hardware and can't be tested with sound cards.

### Limitations (state these in every report)

- **Audio only.** The bench passes audio between sound devices. It doesn't exercise a transmitter's ALC, PA linearity, IMD or thermal limits, or a receiver's AGC. Dense constellations such as 64- and 256-QAM are the most sensitive to these effects, so on-air results for high-rate modes can fall short of bench results. The IONOS display shows the signal's crest factor (PEP ÷ average power). Record it per modem, because a low crest factor at full PEP can exceed a real transmitter's thermal or linearity limits.
- **A simulated channel isn't the real ionosphere.** IONOS is a Watterson model with fixed presets:
  - It has no Flutter profile.
  - It has no CW interferer or impulsive-noise (QRN) source.
  - Frequency offset and drift can't be combined with multipath.
- **Symmetric channel.** One simulator in half-duplex mode applies the same channel model in both directions (manual §4, Fig. 7). An asymmetric channel would need two units.
- **One payload.** The workload is a single incompressible payload, so results don't show the effect of B2F compression on typical text traffic.

## 2. Bench setup

- **Wiring and levels:** follow [bench-setup.md](bench-setup.md). Use one IONOS in a half-duplex, symmetric setup, with modem 1 on Ch1 and modem 2 on Ch2. Fit isolation transformers if any hum or ground-loop noise appears; N5TW used them on every connection. Use 3 kHz bandwidth for all HF testing.
- **Record the full chain once per campaign** in `runs/<campaign>/bench.md`:
  - sound devices, Windows sample rates and levels
  - IONOS firmware revision and serial number, and its Ch1/Ch2 IN and OUT gains
  - Winlink Express version
- **Clocks:** Winlink and ARDOP log in **UTC** to the second, and `hfbench` stamps in UTC. The Windows machine has no Python, so the stamps can come from another machine as long as both clocks use NTP. On 10 Nov 2026 the Mac and the Windows bench machine agreed to within about 0.5 s. Recheck the offset at the start of each session.
- **Two Winlink instances:** both run on one Windows machine from separate installs, `C:\RMS Express` and `C:\RMS Express 2`. Each install has its own callsign and its own logs, so every session is logged from **both ends**. Because both instances share one clock, the two logs line up to within a few seconds. See [log-formats.md](log-formats.md).

## 3. Levels and SNR calibration

### SNR reference bandwidth

IONOS sets S:N from −40 to +40 dB in 1 dB steps, measured in its **3000 Hz** operating bandwidth (manual §3.2, §3.5). This toolchain uses 3000 Hz as the reference and records the bandwidth on every run.

Two conversions are needed when comparing results:

- **To the 2500 Hz convention:** SNR₂₅₀₀ = SNR₃₀₀₀ + 10·log₁₀(3000/2500) = SNR₃₀₀₀ + 0.79 dB.
- **To a modem's own bandwidth:** SNR in the modem's bandwidth = SNR₃₀₀₀ + 10·log₁₀(3000/BW). This is +1.2 dB for 2300 Hz and +7.8 dB for 500 Hz. When modes of different bandwidths share a plot, label which reference the axis uses (manual §3.5).

### Self-test

Run the IONOS self-test at the start of every campaign:

1. Connect a stereo patch cord from output to input.
2. Turn the Mode knob 17 clicks clockwise from power-on to reach TEST3K.
3. Confirm that every reading is green, which means within ±1 dB.

Record the result. This replaces an external level-meter check of the simulator itself.

### Levels (manual §3.4 and §4.1)

- The simulator's internal level (`Lvl=`, mV p-p) must stay between 200 and 1200 mV p-p and must **never exceed 1200 mV**. A red level warning means clipping. N5TW set each modem's output to about 450 mV p-p.
- Set levels on the **worst multipath preset at low S:N**, because that's where the peaks are largest. Then save the gains to EEPROM.
- Match the two modems' input levels to each other. With one simulator, unequal Ch1 and Ch2 levels make the channel effectively asymmetric.
- Recheck levels at every modem change, because each modem drives the sound device differently. Record the `Lvl=` and crest-factor readings in the run notes.
- If a run shows a red level, mark it `invalid`.

### Per-direction S:N check (ARDOP)

ARDOP logs the S:N it measured on received leaders, in a 3 kHz noise bandwidth, which is the IONOS reference. Its session statistics give one value per station, so each direction is measured separately. With one IONOS unit in symmetric mode, both directions should read close to the IONOS setting.

**ARDOP's S:N reading tops out at about 20 dB**, so this check works only at test points of about 18 dB and below.

- In the pilot, at those points, compare the measured S:N for each direction with the setting.
- If the two directions differ by more than about 2 dB, treat it as a level fault and mark the run `invalid`.

The first logs (10 Nov 2026, back to back without IONOS) show why this check matters:

- One direction's S:N stepped down from at least 20 dB to about 13 dB between sessions.
- In that direction the link stayed at 4PSK.2000, while the other direction ran at 16QAM.2000.
- Transfers in the weak direction took about twice as long, roughly 720 bit/s against 1,500 bit/s.

The Winlink log alone would have reported this as "the modem is slow one way". [bench-setup.md](bench-setup.md) gives the level-matching procedure.

## 4. Workload

- Use one fixed, incompressible payload. Generate it with `hfbench payload make <path> --bytes N --seed S`, which produces pseudo-random bytes that can be regenerated exactly from the size and seed. The SHA-256 goes in the matrix and on every run-sheet row. Winlink B2F compresses messages, so a compressible payload would make timing depend on the content.
- **What goes over the air:** Winlink carries an attachment base64-encoded inside the message, and B2F then compresses the whole message. A random-binary attachment therefore still shrinks by about 18%. In the first logs, 51,433 bytes compressed to about 42,200. The size actually sent is the *compressed* size, which the log records on the `FC EM` proposal line. Goodput is computed on that figure. Random content keeps the compressed size essentially constant from run to run.
- **Run length:** the IONOS manual (§7.1) recommends at least 5–10 minutes per run. That gives adaptive modems time to settle and averages out slow multipath fading. N5TW sized transfers per mode: 120 KB for fast VARA and Pactor cases, 32 KB for slower ones, and 4–10 KB for ARDOP and WINMOR. A single fixed payload makes goodput directly comparable, but no single size suits both VARA at 30 dB and ARDOP at 0 dB.
- **Recommendation:** split the fixed workload into **N equal messages**, for example 8 × 8 KB of random data. A run that hits the abort rule then still yields "messages delivered" and a partial goodput, instead of nothing. Payload size and message count are TBD.

## 5. Channel profiles

IONOS offers fixed two-path (or four-path) Watterson presets. Delay and Doppler spread can't be set independently.

| IONOS preset | Doppler spread (Hz) | Delay (ms) | Standard equivalent |
| --- | --- | --- | --- |
| WGN | none | none | AWGN baseline |
| MPG | 0.1 | 0.5 | CCIR 520-2 Good / F.1487 mid-latitude quiet |
| MPM | 0.5 | 1 | CCIR 520-2 Moderate / F.1487 mid-latitude moderate |
| MPP | 1 | 2 | CCIR 520-2 Poor / F.1487 mid-latitude disturbed |
| MPD | 2 | 4 | IONOS "Multipath Disturbed"; not one of the CCIR 520 profiles |

**Source of the figures:** they come from the IONOS manual rev 2.03 (specifications page) and N5TW p. 6. The manual says its presets follow CCIR/ITU 520-2 and F.1487. The F.1487 equivalence in the table hasn't been checked against the recommendation text. That check only affects how the profiles are named in a report, because the IONOS values are what's actually used.

### Changes from the original plan

- **Flutter (0.5 ms / 10 Hz) is dropped.** IONOS has no such preset. IONOS flat fading (FADE DEPTH and FADE FREQ, WGN only) is not a substitute, because it has no frequency selectivity or Doppler spread. It can still run as a separate impairment, labelled as flat fading.
- **MPD is added** as the harshest condition available.
- **Number of paths:** 2. This matches N5TW and the CCIR two-path model. The setting is `ionos.multipaths` in the matrix.
- **No seed control.** IONOS has no random seed, so each run sees a different fading realisation (manual §7.1). That makes replicates essential. Report the spread between replicates, and use 5 replicates near the knee.

## 6. Test matrix and staging

Matrices are TOML files; see `runs/example-matrix.toml` and `runs/example-impairments.toml`. `hfbench sheet` expands a matrix into an ordered run sheet. Each row includes `ionos_commands`, the exact IONOS command sequence for that run, for example:

```text
BANDWIDTH:3000; MULTIPATH:2; OFFSET:0; FADE DEPTH:0; FADE FREQ:0; FM DEVIATION:0; FM RATE:0; MPP:10
```

The sequence resets every add-on explicitly, so nothing carries over from the previous run. Set the values with the knobs or send them over USB serial. The commands are the same in both cases (manual Fig. 9 and Fig. 10).

### Stages

1. **Pilot** (about 10 runs). Check that the pipeline matches actual transfers: payload delivered intact, stamps line up with Winlink log sessions, and goodput is plausible against N5TW's curves for VARA 2300 and ARDOP 2000.
2. **Coarse pass.** All modems × {WGN, MPG, MPM, MPP, MPD} × S:N {30, 20, 10, 5, 0} dB × 3 replicates.
3. **Targeted pass.** Refine the SNR around each modem's knee for each profile with `snr_by_profile`, using 1–2 dB steps and 3–5 replicates.
4. **Impairment pass (WGN only).** IONOS ignores offset, fade and FM on multipath presets and shows "no FM or Offset!", so the matrix loader rejects that combination. Run at an S:N a few dB above each modem's WGN knee:

   | Impairment | IONOS setting |
   | --- | --- |
   | Frequency offset | `OFFSET` ±20, ±50 Hz (range ±200 Hz in 10 Hz steps) |
   | Slow drift | `FM DEVIATION` and `FM RATE`, for example ±10 Hz at 0.1 Hz |
   | Flat fading | `FADE DEPTH` and `FADE FREQ` |
   | SNR step (adaptation speed) | Send a new mode command mid-run, for example `WGN:5`, and stamp it with `hfbench mark "WGN:5"` |
   | CW interferer, QRN | **Not supported by IONOS.** These would need external audio summing, so they're deferred. |

**Run order:** runs are blocked by modem, because changing modems is slow and error-prone. Within each block the order is randomised with a recorded seed, so slow drift in levels or temperature doesn't line up with S:N or profile.

## 7. Run procedure

### Semi-automatic (recommended)

Open a Command Prompt **on the Windows bench desktop** and run:

```text
hfbench run -d runs\<campaign>        (defaults: --port COM3  --winlink-dir "C:\RMS Express")
```

For each run, `hfbench run` does the following:

1. Sends the run's IONOS commands over COM3 and records every `OK`. It stops if the unit rejects a command.
2. Asks you to start the Winlink session. Queue the payload and click **Start** on station 1.
3. Finds the session in station 1's Winlink log and stamps the start and end times **from the log's own UTC timestamps**.
4. Applies the abort rule:
   - If no connection is made within `abort_minutes`, the run is recorded as `dnc`.
   - If a session runs past the limit, it sounds an alert. Disconnect in Winlink, and the run is recorded as `dnc`.
5. Records `completed` when the session closes with all `payload_messages` delivered, then waits for Enter before the next run. Type `q` to stop.

While a run is waiting, press **`i`** to mark it `invalid` (a bench fault) or **`d`** to mark it `dnc`. Runs marked `invalid` are repeated automatically. A run interrupted by a crash resumes when you start again.

| Other commands | Use |
| --- | --- |
| `hfbench ionos probe` | Checks the IONOS answers; sends an invalid command, so it changes nothing |
| `hfbench ionos send "WGN:20"` | Sends one command by hand |
| `hfbench ionos apply -d … <run_id>` | Applies one run's settings |

### Manual (no serial, or for debugging)

```text
hfbench next  -d runs/<campaign>             # shows the next run and its IONOS commands
hfbench start -d runs/<campaign> <run_id>    # right before connecting
hfbench mark  -d runs/<campaign> "WGN:5"     # only for mid-run events
hfbench end   -d runs/<campaign> completed   # or dnc / invalid, with --notes "..."
```

### Abort rule

Abort a run after `abort_minutes` (default 30) or `abort_retries` failed connects (default 3), whichever comes first. N5TW reports that ARDOP often dropped links on MPP at low S:N. Record those runs as `dnc` rather than rerunning them until one succeeds.

### Outcomes

| Outcome | Meaning |
| --- | --- |
| `completed` | The payload was delivered within the abort rule. |
| `dnc` | Did not complete under the abort rule. This is a **result**, and it counts against completion rate. |
| `invalid` | Bench fault, such as a wrong setting, a red level warning or operator error. It is excluded from results. Repeat the run with `hfbench start --retry`. |

Every attempt is kept in the event log (`events.jsonl`, append-only). The manifest has one row per attempt and marks the final one.

### Automation status

| Status | Item |
| --- | --- |
| Done | IONOS serial control, log-based stamping, the abort rule and outcomes (`hfbench run`) |
| Next | A timed mid-run SNR step, for the `snr-step` impairment |
| Done | Tone-based level check (`hfbench audio check`); see bench-setup.md |
| Next | Running the tone check automatically before each run in `hfbench run` |
| Later | Starting the Winlink session itself, either by scripting the Winlink Express window or with Pat |

Audio and GUI automation have to run in the desktop session. SSH sessions on Windows are session 0, which can't use the sound devices or windows.

**Serial link (IONOS firmware 2.03):** the unit ignores lines ending in a bare CR, although the manual says CR. A line ending in LF or CR+LF works, so `hfbench` sends CR+LF. Replies are `OK` or `?`. The baud rate makes no difference.

## 8. Metrics

| Metric | Definition |
| --- | --- |
| **Goodput** | Compressed message bytes (`FC EM` line) × 8 ÷ Winlink's per-message transfer time, which runs from "Sending/Receiving" to "Completed/received". Reported **per direction**, and in **bytes/min** as well to compare with N5TW. Session-level figures, which include the handshake and turnarounds, are reported separately. |
| **Session time** | Connect to disconnect, including handshake. |
| **Completion rate** | Completed runs ÷ (completed + dnc) at each point. |
| **Messages delivered** | Per run, if the workload is split into messages. |
| **Retries** | Winlink logs don't record them. For ARDOP, the ARQ session statistics give failed decodes and mode shifts, and the debug log gives a per-frame timeline with ACK/NAK records. Other modems need their own logs. |
| **Knee SNR** | The lowest S:N where the completion rate is at least 90%. With 3 replicates this means 3 out of 3, so use 5 replicates near the knee. |
| **Shannon efficiency** | Goodput (bit/s) ÷ C, where C = B·log₂(1 + SNR) and B = 3000 Hz, matching the IONOS reference bandwidth. Results may also be quoted against each modem's occupied bandwidth, labelled as such. |

Report the **median and range** (or IQR when n ≥ 5) for each point, along with n.

## 9. Privacy

Real logs contain callsigns, grid squares and subjects. `logs/`, `runs/<campaign>/` and `reports/` are git-ignored. Test fixtures under `tests/fixtures/` must be redacted before they are committed.

## Open questions

1. Which modems and versions are in the comparison?
2. What firmware does the IONOS unit run (shown at power-on)? Is its USB port connected to the Windows machine, which would allow serial automation?
3. ~~Are the two Winlink Express instances on one Windows machine or two?~~ One machine, with two installs.
4. What is the payload: total size, number of messages, and attachment or body? See the recommendation in §4.
5. Is this for personal evaluation or for publication? The answer sets the required rigour (replicates, reporting of calibration uncertainty).
6. Are CW-interferer and QRN tests wanted badly enough to build external audio injection?
