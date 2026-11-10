# Bench setup and level matching

Steps marked **[Manual]** are from the *Teensy IONOS manual rev 2.03* and those marked **[N5TW]** are from N5TW's *Take Three* appendix. Steps marked **[Added]** are not in either document. They come from first principles or from our own logs, and should be checked on the bench.

## How the half-duplex channel works

In half-duplex mode one IONOS unit carries both directions [Manual §4.0, Fig. 7]:

```text
Modem 1 Audio Out ──► Line In  ch1 ┐                     ┌ Line Out ch1 ──► Modem 1 Audio In
                                   ├─ mix ─► channel ─►──┤
Modem 2 Audio Out ──► Line In  ch2 ┘   (one Watterson     └ Line Out ch2 ──► Modem 2 Audio In
                                        model + noise)
```

- Connect with 3.5 mm stereo plugs and Y-splitters (stereo to two mono). PTT isn't used.
- The CH1 and CH2 inputs are **mixed into one channel model**, whose output goes to both outputs. Each modem therefore also hears its own transmission, which a half-duplex modem ignores.
- Because both directions share one channel and one noise source, the channel is symmetric **only if both modems arrive at the mixer at the same level**. That is what the manual's step 5 below is for.
- [Manual, Fig. 7 note; N5TW] Use stereo isolation transformers if ground loops affect audio. N5TW ran every input and output through isolation transformers.

## 1. Self-test the simulator [Manual §3.1]

1. Connect a stereo patch cord from **Line Out** to **Line In**.
2. Power on. The unit starts in WGN mode at S:N 40 dB.
3. Turn the **Mode (left) knob 17 clicks clockwise** to reach `TEST3K Sine`. This generates a 1500 Hz tone.
4. Wait about 5 seconds. The Ch1 Out, Ch1 In, Ch2 Out and Ch2 In readings (mV p-p) should all show **green**, which means within ±1 dB.
5. Optionally turn the right knob to sweep the tone from 300 to 3300 Hz.

A red reading means a hardware or wiring fault. The manual notes that the self-test "is also useful in setting up initial modem output levels".

## 2. Set the level into the simulator [Manual §4.1 steps 1–3; N5TW]

Do this one modem at a time, with only that modem transmitting.

1. Connect the modem's audio output to its IONOS input (Ch1 or Ch2).
2. Select a channel mode between WGN and MPP. The display shows the internal level `Lvl=` in mV p-p and the crest factor (CF).
3. Make the modem transmit, then adjust **either** the modem's or Windows' output level **or** the IONOS `CH1 IN` / `CH2 IN` gain until `Lvl` reads between **200 and 1100 mV p-p**.
   - The internal level must never exceed 1200 mV. Readings above it turn red and mean clipping.
   - The internal mixer trips red above 1800 mV, which can happen on multipath settings.
   - [N5TW] With the simulator output connector removed, he set each Winlink Express output to about **450 mV**, "plenty of input but away from overrange limits".
   - [N5TW] Set levels on a **low-S:N multipath** setting, where the peaks swing highest.

## 3. Match the two directions [Manual §4.1 step 5]

> If using a single Simulator to model a symmetric half duplex channel make the modem outputs (to the simulator) approximately the same level or adjust the CH1 and CH2 input gains to achieve similar p-p level readings.

Using the same waveform from both sides, set the gains so that **Ch1 and Ch2 give the same `Lvl` reading**. With the same modem software at both ends, the waveforms match, so p-p readings compare fairly.

## 4. Set the level out of the simulator [Manual §4.1 step 4; N5TW]

- Use `CH1 OUT` and `CH2 OUT` to set what each modem receives. The maximum output is 2000 mV p-p.
- [N5TW] Adjust the sound card input and Windows recording levels so each modem's receive indicator stays in its green zone, again on a low-S:N multipath setting.
- [N5TW] He used the IONOS default gains throughout.

## 5. Save and verify [Manual §3.2, §4.1]

1. With a gain or level setting on screen, **push the right knob** to save it to EEPROM as the power-on default.
2. **Write down every level**: Windows playback and recording levels for both devices, the modem drive settings, and IONOS CH1/CH2 IN and OUT. Copy them into `runs/<campaign>/bench.md`.
3. Make test runs on **WGN at 20–30 dB** before any measurement runs.

## 6. The noisy USB audio device [Added]

The IONOS documents don't cover the sound devices' own noise. The principles below apply.

**Where the device's noise enters.** Its noise adds to the noise IONOS injects, and only in the directions that pass through that device:

- **Its output (DAC) into IONOS.** This noise rides along with the signal, so its contribution is fixed by how hard the device is driven. Drive the device's **analog output higher** (Windows playback level near maximum and modem drive up) and bring the level down with the IONOS `CH IN` gain instead.
- **Its input (ADC) from IONOS.** This noise is added after the channel. Give that device **more analog signal** with IONOS `CH OUT`, and reduce the digital or software gain on the recording side to keep the modem in its green zone.

In general, keep analog levels high at the noisy device's connectors and do any attenuation inside IONOS.

**How much it matters.** The device's own S:N should be at least **10 dB above the highest test S:N**. For a 30 dB top point that means ≥ 40 dB, at which the device shifts the effective S:N by less than 0.5 dB. If a device can't reach that, either lower the top test point or report it as a bench limit.

**Measuring each device's own noise.** ARDOP's S:N reading tops out at about **20 dB**, so it can't measure this. Instead:

1. Record a few seconds from each device's input with the IONOS output connected but nothing transmitting.
2. Record again while a modem is transmitting through IONOS at WGN 40.
3. Compare the two RMS levels in a 300–3300 Hz band, for example with Audacity's *Analyze → Plot Spectrum* or *Contrast*.

**Ground loops and USB power.** Both documents recommend isolation transformers. Also try:

- a different USB port or a powered hub
- unplugging chargers and other USB devices
- a ferrite on the USB cable

A device whose noise changes when cables are moved has a ground or shielding problem.

## 7. Check symmetry with the modems themselves [Added]

- Set **WGN at 15 dB**, below ARDOP's 20 dB reading ceiling, and run one session each way.
- `hfbench parse` on both stations' logs shows the ARDOP-measured S:N **per direction**. The two directions should agree with each other, and with 15 dB, to within about 2 dB.
- Repeat at 10 dB.

### Open point: what IONOS measures S:N against

The manual doesn't say whether S:N is set relative to the measured input signal or to a fixed internal reference. To find out, at a fixed setting:

1. Change one modem's input level by about 6 dB, watching that `Lvl` stays in range.
2. See whether the ARDOP-measured S:N for that direction changes.

- **If it changes by about 6 dB**, the noise is fixed and the Ch1/Ch2 level match in step 3 directly sets symmetry.
- **If it doesn't change**, IONOS tracks the signal, and step 3 matters only for headroom.

## What the first logs show (10 Nov 2026, back to back, no IONOS)

Per-frame S:N from both ARDOP debug logs, in 10-minute buckets:

| Time (UTC) | Station 1 receives (median) | Station 2 receives (median) |
| --- | --- | --- |
| 17:10–17:39 | 20 (ceiling) | 20 (ceiling) |
| 17:40–18:39 | 19 | **13** |

Station 2's receive S:N **stepped down by about 7 dB between 17:36 and 17:45 UTC** and stayed there. That pattern points to a change made between sessions 5 and 6, such as a level, a cable or another USB device, rather than a constant device noise floor.
