# Bench setup and level matching

Steps marked **[Manual]** are from the *Teensy IONOS manual rev 2.03*. Steps marked **[N5TW]** are from N5TW's *Take Three* appendix, and **[C-Media]** from the Masters Communications FAQ. Steps marked **[Added]** are not in any of these sources. They come from first principles or from our own logs, so check them on the bench.

## Our bench (checked from Windows on 10 Nov 2026)

| | Station 1 (`C:\RMS Express`) | Station 2 (`C:\RMS Express 2`) |
| --- | --- | --- |
| Sound device | "USB Audio Device", C-Media, USB VID 0D8C PID **0014** | "C-Media USB Audio Device", USB VID 0D8C PID **0008** |
| ARDOP `DriveLevel` | 90 | 90 (was 75; matched 10 Nov) |
| IONOS channel | **Ch2**, measured: changing CH1 IN moved only station 2 | **Ch1** |

The two devices use **different chips**, so the same Windows slider position gives different real levels. Their drive levels also differ by about 1.6 dB. **Don't try to match slider positions.** Match measured levels instead, using a test tone, as described below.

## Why matching by ear or by slider fails [Added]

- **Different chips have different gain stages.** "50%" in Windows means a different voltage on each device.
- **The IONOS gains move in coarse steps** [Manual Fig. 9]. CH IN has the steps 0, 1, 2, 5, 10, 20, 50, 100, 200, and CH OUT has 0, .01, .02, .05, .1, .2, .5, 1, 2. That's roughly 6–8 dB per step, so IONOS can only do coarse adjustment. Do the **fine trim in Windows**.
- **IONOS feeds microphone inputs.** IONOS outputs up to 1.8 V p-p at line level, while a USB-dongle mic input is built for millivolts. With the default `CH OUT` of 1, mic boost on, or an AGC running, the input clips. The resulting distortion looks like a high noise floor.
- **ARDOP signals are bursty**, so a meter never settles on them. Use a **steady tone** for setting levels and keep ARDOP for the final check.

## How the half-duplex channel works [Manual §4.0, Fig. 7]

```text
Station 1 Speakers ──► Line In  ch1 ┐                     ┌ Line Out ch1 ──► Station 1 Microphone
                                    ├─ mix ─► channel ─►──┤
Station 2 Speakers ──► Line In  ch2 ┘   (one Watterson     └ Line Out ch2 ──► Station 2 Microphone
                                         model + noise)
```

Both inputs are mixed into one channel model, which feeds both outputs. The channel is symmetric only if both stations reach the mixer at the **same level** [Manual §4.1 step 5]. Both stations should also receive at the **same digital level**.

## The tone check (`hfbench audio check`)

Steps 2 and 3 below can be done by hand in Audacity, but `hfbench audio check` does both together and reports the result in dB. Do step 0 (Windows settings) first.

1. Close both Winlink Express sessions so neither ARDOP is transmitting.
2. Open a **Command Prompt on the Windows desktop**. Over SSH there's no audio.
3. Run:

```text
hfbench audio check --loop
```

The check:

1. Reads each station's playback and capture devices and `DriveLevel` from `C:\RMS Express\ARDOP_Win TNC.ini` and `C:\RMS Express 2\ARDOP_Win TNC.ini`.
2. Sets the IONOS to **WGN, S:N 20** over COM3, with offset, fading and FM off. Gains are never touched. At 40 dB the bench's own noise biases the transmit offsets, which is why 20 is the default.
3. Records both microphones with nothing playing, giving each device's noise floor.
4. Plays a 1500 Hz tone at −6 dBFS from **station 1's speakers**, recording both microphones, then does the same from **station 2's speakers**.
5. Prints, for each of the four paths, the tone level (dBFS), the S:N in 3 kHz, the 2nd and 3rd harmonics, the peak level and any clipping. The 3rd harmonic at 4.5 kHz is above the IONOS's 3.3 kHz filter, so if it appears it was created at the receiving input.
6. Prints the **transmit mismatch** (into the IONOS) and the **receive mismatch** (at the microphones) separately, in dB. It says which station to turn down or up, and on which slider (speaker or microphone).

`--loop` re-measures every few seconds, so you can move one Windows slider at a time and watch the mismatch go to 0. Press Ctrl+C to stop. Add `--json levels.json` to save the numbers for `bench.md`.

**Interpreting the result:**

1. **Transmit vs IONOS reference.** This is the key number. It's each station's tone S:N at the other microphone minus the IONOS setting. Bring **both stations to 0 ± 1 dB**, and the IONOS setting is then the real S:N in both directions.
   - Large changes: one IONOS `CH IN` step is about 6–8 dB.
   - Fine trim: the Windows speaker level.
   - Set both ARDOP `DriveLevel`s the same as well, because the tone bypasses them.
2. **Receive mismatch.** Matched microphones make both stations work at the same point. This doesn't change S:N, because the IONOS noise is fixed, but it does avoid clipping. Fix transmit first, then set each microphone so it hears the other station somewhere between **−26 and −8 dBFS**, the same at both stations.
3. **CLIPPED paths** are left out of the estimates. A microphone that clips on its *own* transmission is harmless while that station transmits, but shows its gain is too high.
4. **The estimates' spread** should be below 1 dB. If it's more, check the Y cables and the IONOS mode.
5. **`--snr 20 40`** also reports each microphone's own noise relative to the IONOS reference. It should be at least 10 dB below the highest S:N you plan to test. Read the transmit offsets from the 20 dB result.

To re-read saved results without playing anything: `hfbench audio report levels.json`.

### Calibration record (10 Nov 2026, headphone-splitter cables)

| Setting | Station 1 (IONOS Ch2) | Station 2 (IONOS Ch1) |
| --- | --- | --- |
| Windows speaker level, channel | 100%, left only | not changed, right only |
| Windows microphone level | 75 | 35 |
| Microphone AGC | **off** | **off** |
| ARDOP `DriveLevel` | 90 | 90 |
| IONOS CH IN | CH2 IN = 20 | CH1 IN = 1 |

| Result (WGN 20) | Station 1 | Station 2 |
| --- | --- | --- |
| Transmit vs IONOS reference | +2.3 dB | +3.3 dB |
| Hears the other station at | −20.5 dBFS | −20.9 dBFS |
| Microphone's own noise | 38 dB below the reference | 38 dB below the reference |

- Mismatch: **transmit 1.1 dB, receive 0.7 dB**. No clipping, and harmonics are −40 dBc or better.
- **AGC was the hidden cause of the 21 dB microphone mismatch.** It was on for both microphones, adding different amounts of gain.
- The CH2 IN gain is high because the headphone-splitter cables load station 1's output. If the cables are replaced with stereo-to-two-mono breakouts, recalibrate.
- The common offset of about +3 dB for the test tone doesn't affect symmetry. ARDOP's own S:N reading is used to calibrate the modem.

### First ARDOP check after calibration (10 Nov 2026, 23:41 UTC, IONOS reportedly at WGN 15)

| | Station 1 receiving (data) | Station 2 receiving (ACKs) |
| --- | --- | --- |
| ARDOP `Early` S:N, median (middle half) | 8 dB (5–10) | 10 dB (7–11) |
| Decode quality, median | 74 | 74 |

- **Symmetric.** Before calibration the two directions read 13 dB and at least 20 dB.
- **About 6 dB below the setting.** ARDOP's signal appears to carry about 9 dB less power than the −6 dBFS test tone. Each modem needs its own offset measured; see "Modem level" below.
- ARDOP stayed at 4PSK.2000. After about 19 KB, Winlink dropped the session with "Received data stream not correct format". That's a modem or protocol result at marginal quality, not a bench fault.

### Answered on 10 Nov 2026: the IONOS adds noise at a fixed level

With nothing playing, both microphones' noise rose 19.1–19.2 dB going from WGN 40 to WGN 20. So the IONOS injects noise at a level set by the S:N setting, **regardless of the input signal**. A station's real S:N is therefore the setting plus its transmit offset. That's why matching the transmit levels is what makes the channel symmetric.

### First tone check (10 Nov 2026, before any adjustment)

| | Station 1 | Station 2 |
| --- | --- | --- |
| Transmit vs IONOS reference | **−24.8 dB** (real S:N about 25 dB below the setting) | +2.7 dB |
| Microphone sensitivity | — | **21 dB higher** than station 1, and clips on its own transmission |
| Microphone's own noise | 46 dB below the reference | 47 dB below the reference |

- Neither device is noisy. Station 2's "higher noise floor" was its 21 dB higher microphone gain.
- The three independent estimates agreed to within 0.1–0.5 dB.

## Step 0: Windows settings for both USB devices [C-Media] [Added]

Open **Control Panel → Sound**, or run `mmsys.cpl`. Do the following for **both** USB devices.

**Playback tab:** set the default device (the green tick) and the default communications device to **Apple Audio**, never a USB device. Otherwise Windows chimes and notifications go straight into the channel.

**Playback tab → Speakers (USB…) → Properties:**
- **Advanced:** use the same default format on both devices, for example *16 bit, 48000 Hz*.
- **Enhancements:** tick "Disable all enhancements" or "Disable all sound effects".

**Recording tab → Microphone (USB…) → Properties:**
- **Levels:** set *Microphone Boost* to **0 dB**, if the device offers it.
- **Advanced** (or **Custom**, depending on the driver): **untick AGC** [C-Media]. Also use the same default format as above. If a "Signal Enhancements" box appears, leave it **off** [C-Media].
- **Enhancements:** disable all.
- **Listen:** make sure "**Listen to this device**" is **off**. If it's on, the received audio is played back out, possibly into the channel.

**Communications tab:** select "**Do nothing**". The setting is currently the Windows default, which turns other audio down by 80% when communications activity is detected.

**ARDOP_Win TNC Setup (both stations):** set **the same `DriveLevel`** on both, for example 90. Then leave it alone and do all adjustment in Windows and IONOS.

Windows sometimes resets microphone levels on its own, so **recheck the levels at the start of each session**.

## Step 1: Self-test, and check the Y cables [Manual §3.1] [Added]

1. Patch Line Out to Line In and power on. Turn the left knob **17 clicks clockwise** to `TEST3K Sine`. All four readings should be **green**.
2. Check the **Y-cable type**. Each Y must be a **stereo-to-two-mono (left/right)** splitter, as shown in the manual's Fig. 7. A *headphone splitter* is wrong: it copies the same channel to both legs, so the two IONOS channels can't be adjusted separately and the two devices' outputs drive each other. To test the cables, use the tone from step 3:
   - **Input side:** play the tone from station 1 only. Setting `CH2 IN` to 0 should **not** change the `Lvl` reading, and setting `CH1 IN` to 0 should drop it to zero. If that doesn't happen, the input Y cable is a headphone splitter.
   - **Output side:** with the IONOS tone on, set `CH2 OUT` to 0. Station 2's microphone should go silent while station 1's doesn't change.

## Step 2 (by hand): match the receive levels (IONOS → microphones) [Manual §3.2, §4.1 step 4] [Added]

Use the IONOS's own 1500 Hz tone, which reaches both microphones identically. Use **Audacity** on Windows (free) as the meter, because it reads in dBFS and can select the recording device.

1. On the IONOS, select **WGN** with **S:N = +40** and **push the right knob** to turn the internal 1500 Hz tone **on**.
2. Set `CH1 OUT` and `CH2 OUT` to **0.1** to start with. Mic inputs need little signal.
3. In Audacity, select station 1's microphone and turn on monitoring by clicking the record meter. Adjust the **Windows microphone level** until the tone peaks at about **−12 dBFS**.
   - If you can't reach −12 dBFS with the slider at 100%, raise `CH OUT` one step.
   - If the slider has to go very low, lower `CH OUT` one step.
4. Repeat for station 2's microphone, aiming for **exactly the same dBFS**, within about 0.5 dB.
5. **Check for clipping.** Record 5 s of tone and run *Analyze → Plot Spectrum*. The harmonics at 3000 and 4500 Hz should be at least 40 dB below the 1500 Hz peak. If they aren't, the input is overdriven: lower `CH OUT` and raise the Windows level.
6. **Measure each device's own noise.** Turn the tone off by pushing the right knob again and record 5 s. Compare the RMS level with the tone's, using *Analyze → Contrast* or the meter.
   - With the IONOS at +40 dB S:N, the result should be close to 40 dB.
   - If one device reads much lower, say 25–30 dB, then that device's input noise dominates. This is the "noisy device". Try a different USB port, a powered hub or a ferrite, and recheck. Its result sets the highest S:N you can test honestly; see the note below.

## Step 3 (by hand): match the transmit levels (speakers → IONOS) [Manual §4.1 steps 1–3, 5; N5TW] [Added]

1. In Audacity, **generate** a 1500 Hz sine at amplitude 0.5 (−6 dBFS) lasting 30 s (*Generate → Tone*). Alternatively, play `tone_1500Hz_-6dBFS.wav`.
2. Set Audacity's playback device to **station 1's speakers** and play the tone in a loop.
3. On the IONOS, select a mode between WGN and MPP and read the input level `Lvl=` in mV p-p. Get it to about **400 mV p-p**:
   - **Coarse:** `CH1 IN`, in steps.
   - **Fine:** the Windows **speaker** level for station 1. Keep it high, about 70–100%, because a noisy device does better with more analog signal.
4. Repeat for **station 2's speakers** using `CH2 IN` and station 2's Windows speaker level. Aim for the **same `Lvl` reading**. Matching these is exactly what the manual's step 5 asks for.
5. Check the real signal. Run an ARDOP session on **MPP at about 5 dB S:N**, where peaks are largest [N5TW]. `Lvl` must stay below about 1100 mV and never turn red [Manual §3.4]. The tone at 400 mV leaves about 8 dB of headroom for ARDOP's peaks. If the reading turns red, lower both `CH IN` settings by the same step.

## Step 4: Save, record, verify [Manual §3.2, §4.1] [Added]

1. **Save** each IONOS gain by pushing the right knob while that setting is displayed.
2. **Record** everything in `runs/<campaign>/bench.md`:
   - both devices' Windows speaker and microphone levels
   - both `DriveLevel` values
   - the IONOS CH1 and CH2 IN and OUT gains
   - the measured dBFS and `Lvl` values
   - each device's noise result from step 2.6
3. **Check symmetry with ARDOP.** Set WGN to **15 dB**, which is below ARDOP's 20 dB reading ceiling, and run one session in each direction. Then run `hfbench parse` on both stations' logs. Each direction's measured S:N should be within about 2 dB of the other, and of 15 dB. Repeat at 10 dB.

## Notes

### Modem level vs the test tone

The tone check matches the stations to each other, but a modem's real S:N also depends on its own signal power, which differs from the test tone's. Every modem and drive setting therefore needs an offset, measured with real traffic. The planned `hfbench audio listen` records both microphones during a session and measures each direction's S:N from the frames themselves.


### How much device noise is acceptable [Added]

A device's own S:N, from step 2.6, should be at least **10 dB above the highest test S:N**. At that margin the device shifts the effective S:N by less than 0.5 dB, so a 30 dB test point needs about 40 dB. If a device can't reach that, lower the top test point or report it as a bench limit.

### What IONOS measures S:N against

Answered: the IONOS uses a fixed noise reference. See the tone-check section above.

### Ground loops [Manual Fig. 7 note; N5TW]

N5TW used isolation transformers on every input and output. Hum shows up as spikes at 50/60 Hz and its harmonics in *Plot Spectrum*.

## First logs (10 Nov 2026, back to back, no IONOS)

| Time (UTC) | Station 1 receives (median S:N, dB) | Station 2 receives (median S:N, dB) |
| --- | --- | --- |
| 17:10–17:39 | 20 (ceiling) | 20 (ceiling) |
| 17:40–18:39 | 19 | **13** |

Station 2's receive S:N **stepped down by about 7 dB between 17:36 and 17:45 UTC** and stayed there. This points to a change made between sessions, rather than a constant noise floor.

Station 2 receives through the PID 0008 microphone input and hears station 1 through the PID 0014 speaker output. Step 2.6 will show whether either of those is the noisy one.
