# Bench setup and level matching

Steps marked **[Manual]** are from the *Teensy IONOS manual rev 2.03*. Steps marked **[N5TW]** are from N5TW's *Take Three* appendix, and **[C-Media]** from the Masters Communications FAQ. Steps marked **[Added]** are not in any of these sources. They come from first principles or from our own logs, so check them on the bench.

## Our bench (checked from Windows on 10 Nov 2026)

| | Station 1 (`C:\RMS Express`) | Station 2 (`C:\RMS Express 2`) |
| --- | --- | --- |
| Sound device | "USB Audio Device", C-Media, USB VID 0D8C PID **0014** | "C-Media USB Audio Device", USB VID 0D8C PID **0008** |
| ARDOP `DriveLevel` | **90** | **75** |
| IONOS channel | Ch1 (assumed; confirm in step 1) | Ch2 |

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

## Step 2: Match the receive levels (IONOS → microphones) [Manual §3.2, §4.1 step 4] [Added]

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

## Step 3: Match the transmit levels (speakers → IONOS) [Manual §4.1 steps 1–3, 5; N5TW] [Added]

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

### How much device noise is acceptable [Added]

A device's own S:N, from step 2.6, should be at least **10 dB above the highest test S:N**. At that margin the device shifts the effective S:N by less than 0.5 dB, so a 30 dB test point needs about 40 dB. If a device can't reach that, lower the top test point or report it as a bench limit.

### Open question: what IONOS measures S:N against

The manual doesn't say whether S:N is set relative to the measured input or to a fixed internal reference. After step 4:

1. Lower one station's Windows speaker level by about 6 dB.
2. Repeat the 15 dB check.

**If that direction's measured S:N drops by about 6 dB**, IONOS uses a fixed reference and step 3's match directly sets symmetry. **If it doesn't drop**, IONOS tracks the input level, and step 3 matters only for headroom.

### Ground loops [Manual Fig. 7 note; N5TW]

N5TW used isolation transformers on every input and output. Hum shows up as spikes at 50/60 Hz and its harmonics in *Plot Spectrum*.

## First logs (10 Nov 2026, back to back, no IONOS)

| Time (UTC) | Station 1 receives (median S:N, dB) | Station 2 receives (median S:N, dB) |
| --- | --- | --- |
| 17:10–17:39 | 20 (ceiling) | 20 (ceiling) |
| 17:40–18:39 | 19 | **13** |

Station 2's receive S:N **stepped down by about 7 dB between 17:36 and 17:45 UTC** and stayed there. This points to a change made between sessions, rather than a constant noise floor.

Station 2 receives through the PID 0008 microphone input and hears station 1 through the PID 0014 speaker output. Step 2.6 will show whether either of those is the noisy one.
