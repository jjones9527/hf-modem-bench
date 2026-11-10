# Test protocol

Status: **draft**. Items marked **TBD** depend on the open questions at the end.

## 1. Purpose and scope

The aim is to compare software HF modems used with Winlink Express on a repeatable bench. Two Winlink Express instances exchange one fixed workload through the IONOS HF channel simulator. Between runs only two things change: the modem and the simulator settings.

**Modems in scope:** VARA HF, ARDOP, Data2G (through its VARA-compatible TNC) and possibly Mercury. Versions are TBD and are recorded per run. Pactor is out of scope because it needs dedicated hardware and can't be tested with sound cards.

### Limitations (state these in every report)

- **Audio only.** The bench passes audio between sound devices, so it doesn't exercise a transmitter's ALC, PA linearity or IMD, or a receiver's AGC. Dense constellations such as 64- and 256-QAM are the most sensitive to these effects, so on-air results for high-rate modes can fall short of bench results.
- **A simulated channel isn't the real ionosphere.** Watterson two-path models leave out several real-world effects: multi-mode propagation with unequal path powers, non-Gaussian Doppler spectra, and time-varying SNR within a run, apart from the step test.
- **One payload.** The workload is a single incompressible payload, so results don't show the effect of B2F compression on typical text traffic.

## 2. Bench setup

- Record the full chain once per campaign in `runs/<campaign>/bench.md`: sound devices, sample rates, Windows audio levels, IONOS version and settings file, and Winlink Express version.
- **Clocks:** run the `hfbench start` and `hfbench end` stamps on the same Windows machine that writes the Winlink logs, so stamps and log timestamps share one clock. If the stamps have to run elsewhere, keep both machines on NTP and record the offset at the start of each session.
- **Two Winlink instances:** whether they run on one machine or two is TBD. If both are on one machine, their logs have to be told apart, for example by callsign or by a separate install directory. Settle this before the parser is finalised.

## 3. Level and SNR calibration

- SNR is defined in a **2500 Hz reference bandwidth**, whatever bandwidth each modem actually occupies.
- Check the IONOS SNR setting with an independent measurement before each session. Use a known tone and a level meter or an FFT, and measure noise power in 2500 Hz. Record the measured value next to the setting.
- Recheck the levels at every modem change. Gain differences between USB sound devices can shift the effective SNR by several dB.
- Keep drive levels well below clipping on every device. If a run shows clipping, record it as `invalid`.

## 4. Workload

- Use one fixed, incompressible payload for every run. Generate it with `hfbench payload make <path> --bytes N --seed S`, which produces pseudo-random bytes that can be regenerated exactly from the size and seed. Its SHA-256 goes in the matrix and on every run-sheet row.
- Winlink B2F compresses messages. A compressible payload would make timing depend on the content, which is why the payload must be incompressible. `hfbench payload hash` reports a zlib ratio, which should be about 1.0.
- The number of messages and the payload size are TBD. A larger payload reduces the share of session time taken by the handshake but makes runs longer.

## 5. Channel profiles

The figures below are for two-path Watterson channels with equal-power paths. **Delay** is the differential time delay between the two paths. **Doppler spread** is the two-sided frequency spread (2σ) of each path.

| Profile | Delay (ms) | Doppler spread (Hz) | Source (to verify) |
| --- | --- | --- | --- |
| AWGN | none | none | baseline |
| Good | 0.5 | 0.1 | ITU-R F.1487 mid-latitude quiet; also CCIR 520 "Good" |
| Moderate | 1.0 | 0.5 | ITU-R F.1487 mid-latitude moderate; also CCIR 520 "Moderate" |
| Poor | 2.0 | 1.0 | ITU-R F.1487 mid-latitude disturbed; also CCIR 520 "Poor" |
| Flutter | 0.5 | 10 | CCIR Rec. 520 "Flutter" (not a mid-latitude F.1487 profile) |

**Verification status:** these figures come from memory of F.1487 and CCIR 520 and haven't yet been checked against the recommendation text. F.1487 also defines low- and high-latitude profiles. Before the pilot:

- Check every row against F.1487 Table 1.
- Check every row against the IONOS presets and documentation (see the PDFs at winlink.org/content/ionos_simulator). Record the exact IONOS preset name or values used, because a preset called "Moderate" in IONOS doesn't necessarily match the figures above.

## 6. Test matrix and staging

Matrices are TOML files (see `runs/example-matrix.toml`). `hfbench sheet` expands them into an ordered run sheet.

1. **Pilot** (about 10 runs). Check that the pipeline matches actual transfers: payload delivered intact, manifest stamps line up with Winlink log sessions, and goodput is plausible.
2. **Coarse pass.** All modems × 5 profiles × SNR {30, 20, 10, 5, 0} dB × 3 replicates.
3. **Targeted pass.** Refine the SNR around each modem's knee for each profile with `snr_by_profile`, using about 2 dB steps and 3–5 replicates.
4. **Impairment pass.** One impairment at a time, at one or two SNRs above the knee:
   - frequency offset of ±20, ±50 Hz
   - an in-band CW interferer (record frequency and level relative to signal)
   - impulsive noise (QRN)
   - a mid-session SNR step, to test adaptation speed (record step size and time)

   The IONOS controls for each of these are TBD.

**Run order:** runs are blocked by modem, because changing modems is slow and error-prone. Within each block the order is randomised with a recorded seed, so slow drift in temperature or levels doesn't line up with SNR or profile.

**Channel seed:** if IONOS supports a random seed, use the same seed for every modem at a given point, so each modem sees the same fading realisation. `seed_mode = "fixed"` reuses one seed for every replicate. `per-replicate` uses seed + replicate − 1, which varies the fading across replicates while keeping it identical across modems. Record which mode was used in the report.

## 7. Run procedure

```text
hfbench next  -d runs/<campaign>             # shows the next run's settings
  (set the IONOS profile, SNR, seed and impairment; check levels; queue the payload)
hfbench start -d runs/<campaign> <run_id>    # right before connecting
  (let the session run)
hfbench end   -d runs/<campaign> completed   # or dnc / invalid, with --notes "..."
```

### Abort rule

Abort a run after `abort_minutes` (default 30) or `abort_retries` failed connects (default 3), whichever comes first.

### Outcomes

| Outcome | Meaning |
| --- | --- |
| `completed` | The payload was delivered within the abort rule. |
| `dnc` | Did not complete under the abort rule. This is a **result**, and it counts against completion rate. |
| `invalid` | Bench fault, such as a wrong setting, clipping or operator error. It is excluded from results. Repeat the run with `hfbench start --retry`. |

Every attempt is kept in the event log (`events.jsonl`, append-only). The manifest has one row per attempt and marks the final one.

## 8. Metrics

| Metric | Definition |
| --- | --- |
| **Goodput** | Payload bytes ÷ data-phase time. The data phase is defined from the log once the format is known. |
| **Session time** | Connect to disconnect, including handshake. |
| **Completion rate** | Completed runs ÷ (completed + dnc) at each point. |
| **Retries** | Taken from Winlink logs where available. Modem-level retransmits need each modem's own log. |
| **Knee SNR** | The lowest SNR where the completion rate is at least 90%. With 3 replicates this means 3 out of 3, so use 5 replicates near the knee. |
| **Shannon efficiency** | Goodput (bit/s) ÷ C, where C = B·log2(1 + SNR) and B = 2500 Hz, matching the SNR reference bandwidth. Results may also be quoted against each modem's occupied bandwidth, labelled as such. |

Report the **median and range** (or IQR when n ≥ 5) for each point, along with n.

If the Winlink logs give only per-second timestamps and totals, the toolchain can report per-session goodput but can't plot rate adaptation over time.

## 9. Privacy

Real logs contain callsigns, grid squares and subjects. `logs/`, `runs/<campaign>/` and `reports/` are git-ignored. Test fixtures under `tests/fixtures/` must be redacted before they are committed.

## Open questions

1. Which modems and versions are in the comparison?
2. Which IONOS controls are available: presets, delay, Doppler, noise, offset, interference, QRN and seed?
3. Are the two Winlink Express instances on one Windows machine or two?
4. What is the exact payload: size, number of messages, and attachment or body?
5. Is this for personal evaluation or for publication? The answer sets the required rigour (replicates, reporting of calibration uncertainty).
