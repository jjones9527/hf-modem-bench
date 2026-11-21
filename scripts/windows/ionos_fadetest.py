"""Check that the IONOS is really fading (21 Nov 2026: over USB, firmware 2.03 changes the channel display
and S:N but not the channel processing; the channel type has to be set with the knob).
Station 2 plays a steady 1,500 Hz tone; station 1 records it; per step, the tone's power in 50-ms blocks:
10-90 % spread, min/max against the median, and how often it crosses its median per second.
WGN: spread about 1-2 dB. Fading channels: spread over 10 dB; crossings rise with the Doppler spread
(MPD about 3/s). Each argument is one step: "none" (send nothing) or IONOS commands joined by "+",
with "~" for a space, e.g.  python ionos_fadetest.py none MPP:40 FADE~DEPTH:0. Run in the desktop
session (hfbench_desk_py.ps1); about 25 s per step."""
import subprocess, numpy as np, sounddevice as sd, sys
HF = r"C:\Program Files\Python312\Scripts\hfbench.exe"
def dev(prefix, kind):
    for i, d in enumerate(sd.query_devices()):
        if d[f"max_{kind}_channels"] > 0 and d["name"].startswith(prefix) and sd.query_hostapis(d["hostapi"])["name"] == "Windows WASAPI":
            return i
    raise SystemExit(f"no {kind} device {prefix}")
out2 = dev("Speakers (3- USB Audio Device)", "output"); in1 = dev("Microphone (C-Media USB Audio Device", "input")
fs = 48000; secs = 20
tone = 0.5 * np.sin(2 * np.pi * 1500 * np.arange(int(fs * (secs + 1))) / fs).astype("float32")
tone2 = np.stack([tone, tone], axis=1)
for mode in sys.argv[1:]:
    if mode == "none":
        acks = "nothing sent"
    else:
        r = subprocess.run([HF, "ionos", "send", *[c.replace("~", " ") for c in mode.split("+")]], capture_output=True, text=True)
        acks = " ".join(l.split("->")[-1].strip() for l in r.stdout.splitlines())
    chunks = []
    pos = [0]
    def ocb(outdata, frames, t, status):
        a = tone2[pos[0]:pos[0] + frames]
        outdata[:len(a)] = a; outdata[len(a):] = 0; pos[0] += frames
    def icb(indata, frames, t, status):
        chunks.append(indata[:, 0].copy())
    with sd.OutputStream(device=out2, samplerate=fs, channels=2, dtype="float32", callback=ocb), \
         sd.InputStream(device=in1, samplerate=fs, channels=1, dtype="float32", callback=icb):
        sd.sleep(int(secs * 1000))
    x = np.concatenate(chunks)[fs:]       # skip the first second
    blk = 2400                            # 50 ms
    n = len(x) // blk
    p = []
    for k in range(n):
        y = np.fft.rfft(x[k*blk:(k+1)*blk] * np.hanning(blk)); f = np.fft.rfftfreq(blk, 1/fs)
        p.append(np.sum(np.abs(y[(f > 1400) & (f < 1600)])**2))
    db = 10*np.log10(np.array(p) + 1e-20); med = np.median(db)
    Y = np.abs(np.fft.rfft(x * np.hanning(len(x)))); F = np.fft.rfftfreq(len(x), 1/fs)
    band = (F > 300) & (F < 3300); pk = F[band][np.argmax(Y[band])]
    tot = np.sum(Y[band]**2); tonep = np.sum(Y[(F > pk - 20) & (F < pk + 20)]**2)
    print(f"   peak {pk:7.1f} Hz, tone-to-rest of band {10*np.log10(tonep / max(tot - tonep, 1e-20)):5.1f} dB", flush=True)
    print(f"{mode:8} acks [{acks}]  tone median {med:6.1f} dB  10-90% spread {np.percentile(db,90)-np.percentile(db,10):5.1f} dB  min {db.min()-med:+6.1f}  max {db.max()-med:+5.1f}  median crossings {np.sum(np.diff(np.sign(db-med)) != 0) / (len(db) * 0.05):.2f}/s", flush=True)

