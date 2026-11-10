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

- **Wiring:** use one IONOS in a half-duplex, symmetric setup, with modem 1 on Ch1 and modem 2 on Ch2. Fit isolation transformers if any hum or ground-loop noise appears; N5TW used them on every connection. Use 3 kHz bandwidth for all HF testing.
- **Record the full chain once per campaign** in `runs/<campaign>/bench.md`:
  - sound devices, Windows sample rates and levels
  - IONOS firmware revision and serial number, and its Ch1/Ch2 IN and OUT gains
  - Winlink Express version
- **Clocks:** run the `hfbench start`, `mark` and `end` stamps on the Windows machine that writes the Winlink logs, so stamps and log timestamps share one clock.
- **Two Winlink instances:** whether they run on one machine or two is TBD. If both are on one machine, their logs have to be told apart, for example by callsign or by a separate install directory.

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

## 4. Workload

- Use one fixed, incompressible payload. Generate it with `hfbench payload make <path> --bytes N --seed S`, which produces pseudo-random bytes that can be regenerated exactly from the size and seed. The SHA-256 goes in the matrix and on every run-sheet row. Winlink B2F compresses messages, so a compressible payload would make timing depend on the content.
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

```text
hfbench next  -d runs/<campaign>             # shows the next run and its IONOS commands
  (set IONOS; check Lvl and that there's no red warning; queue the payload)
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

### Automation (later phase)

IONOS accepts the same commands over USB serial and replies `OK` or `?` to each (manual §6). If the simulator's USB port is connected to the Windows machine, `hfbench` could send `ionos_commands` itself, record each acknowledgement in the event log, and send the mid-run SNR step at an exact time. That would remove manual setup errors. It needs `pyserial` and the COM port name.

## 8. Metrics

| Metric | Definition |
| --- | --- |
| **Goodput** | Payload bytes ÷ data-phase time. Reported in **bytes/min** as well, to compare with N5TW. The data phase is defined from the log once the format is known. |
| **Session time** | Connect to disconnect, including handshake. |
| **Completion rate** | Completed runs ÷ (completed + dnc) at each point. |
| **Messages delivered** | Per run, if the workload is split into messages. |
| **Retries** | Taken from Winlink logs where available. Modem-level retransmits need each modem's own log. |
| **Knee SNR** | The lowest S:N where the completion rate is at least 90%. With 3 replicates this means 3 out of 3, so use 5 replicates near the knee. |
| **Shannon efficiency** | Goodput (bit/s) ÷ C, where C = B·log₂(1 + SNR) and B = 3000 Hz, matching the IONOS reference bandwidth. Results may also be quoted against each modem's occupied bandwidth, labelled as such. |

Report the **median and range** (or IQR when n ≥ 5) for each point, along with n.

## 9. Privacy

Real logs contain callsigns, grid squares and subjects. `logs/`, `runs/<campaign>/` and `reports/` are git-ignored. Test fixtures under `tests/fixtures/` must be redacted before they are committed.

## Open questions

1. Which modems and versions are in the comparison?
2. What firmware does the IONOS unit run (shown at power-on)? Is its USB port connected to the Windows machine, which would allow serial automation?
3. Are the two Winlink Express instances on one Windows machine or two?
4. What is the payload: total size, number of messages, and attachment or body? See the recommendation in §4.
5. Is this for personal evaluation or for publication? The answer sets the required rigour (replicates, reporting of calibration uncertainty).
6. Are CW-interferer and QRN tests wanted badly enough to build external audio injection?
