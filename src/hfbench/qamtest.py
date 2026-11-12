"""16QAM path test: how cleanly does each audio path carry an ARDOP-like signal?

ARDOP's 16QAM.2000.100 frames ran at very different decode quality depending
on which USB adapter transmitted and which received, at the same measured S:N
(see docs/results-log.md, wgn25a). A sine tone can't show that, so this plays
a known multi-carrier 16QAM signal from each station and records it on both
microphones. That covers all four paths: station i plays, station j records.

Signal (at the playback rate):

    0.3 s silence | chirp 300->2700 Hz, 0.2 s | 50 ms gap |
    N symbols: 10 carriers 600..2400 Hz, 200 Hz apart, 100 baud, random 16QAM |
    50 ms gap | chirp | 0.3 s silence

Analysis: the two chirps give the start and the true sample-rate ratio between
the playing DAC and the recording ADC. Each symbol is demodulated over the
middle 5 ms of its 10 ms (orthogonal at 200 Hz spacing, clear of the
transitions). Per carrier, the complex gain is fitted, with a linear phase drift
for any residual timing error. What's left is the error vector:

    MER = 10 log10( sum |fitted signal|^2 / sum |error|^2 )   (dB, higher is better)

The noise the IONOS adds limits MER to about the in-band S:N. A path that is
clearly worse than the others at the same setting has some other impairment.
Measuring at two drive levels separates the two kinds:
- noise-like (MER falls as the level drops)
- distortion such as clipping or compression (MER *improves* at the lower level).

Numpy only; audio I/O is in run_qam (sounddevice, Windows desktop session).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, asdict, field

import numpy as np

CARRIERS = tuple(600.0 + 200.0 * k for k in range(10))   # Hz
BAUD = 100.0
WIN_S = 0.005                                           # demod window per symbol
CHIRP = (300.0, 2700.0, 0.2)                            # f0, f1, seconds
LEAD_S, GAP_S = 0.3, 0.05
LEVELS_DB = (0.0, -6.0)                                 # re the default drive


def _qam16(rng: np.random.Generator, shape) -> np.ndarray:
    lv = np.array([-3, -1, 1, 3], dtype=float)
    s = lv[rng.integers(0, 4, shape)] + 1j * lv[rng.integers(0, 4, shape)]
    return s / np.sqrt(10.0)                            # unit mean power


def _chirp(fs: float) -> np.ndarray:
    f0, f1, d = CHIRP
    t = np.arange(int(d * fs)) / fs
    c = np.sin(2 * np.pi * (f0 * t + (f1 - f0) * t * t / (2 * d)))
    r = int(0.005 * fs)
    c[:r] *= np.linspace(0, 1, r)
    c[-r:] *= np.linspace(1, 0, r)
    return c


@dataclass
class Layout:
    fs: float
    n_sym: int
    sym_start: float          # seconds from the start of the first chirp to the first symbol
    chirp_sep: float          # seconds between the starts of the two chirps


def layout(fs: float, n_sym: int) -> Layout:
    d = CHIRP[2]
    data = n_sym / BAUD
    return Layout(fs, n_sym, d + GAP_S, d + GAP_S + data + GAP_S)


def make_signal(fs: float, n_sym: int = 800, peak_dbfs: float = -1.0, seed: int = 1
                ) -> tuple[np.ndarray, np.ndarray]:
    """Returns (mono float32 waveform, symbols[n_sym, n_carriers])."""
    rng = np.random.default_rng(seed)
    syms = _qam16(rng, (n_sym, len(CARRIERS)))
    ns = int(round(fs / BAUD))
    t = np.arange(ns) / fs
    tones = np.exp(2j * np.pi * np.outer(CARRIERS, t))        # [k, t]
    data = np.empty(n_sym * ns)
    for n in range(n_sym):
        # phase-continuous carriers: reference each symbol to absolute time
        ph = np.exp(2j * np.pi * np.array(CARRIERS) * n / BAUD)
        data[n * ns:(n + 1) * ns] = np.real((syms[n] * ph) @ tones)
    data /= np.max(np.abs(data))
    ch = _chirp(fs)
    gap = np.zeros(int(GAP_S * fs))
    lead = np.zeros(int(LEAD_S * fs))
    y = np.concatenate([lead, ch, gap, data, gap, ch, lead])
    y = y / np.max(np.abs(y)) * 10 ** (peak_dbfs / 20)
    return y.astype(np.float32), syms


def _find(x: np.ndarray, ref: np.ndarray, lo: int, hi: int) -> float:
    """Sub-sample position of ref in x[lo:hi] (cross-correlation peak, parabolic fit)."""
    seg = x[max(lo, 0):min(hi, len(x))]
    n = len(seg) + len(ref)
    nfft = 1 << (n - 1).bit_length()
    c = np.fft.irfft(np.fft.rfft(seg, nfft) * np.conj(np.fft.rfft(ref, nfft)), nfft)[:len(seg) - len(ref) + 1]
    i = int(np.argmax(np.abs(c)))
    if 0 < i < len(c) - 1:
        a, b, d = np.abs(c[i - 1]), np.abs(c[i]), np.abs(c[i + 1])
        den = a - 2 * b + d
        i = i + (0.5 * (a - d) / den if den else 0.0)
    return max(lo, 0) + i


@dataclass
class PathResult:
    level_dbfs_rms: float
    mer_db: float                       # all carriers, best window offset
    mer_by_carrier: list[float]
    gain_db_by_carrier: list[float]     # relative to the mean
    flatness_db: float                  # max - min carrier gain
    ppm: float                          # recording rate re playback rate (end to end)
    wander_us: float = float("nan")     # peak-to-peak of the 0.2 s-smoothed timing error
    jitter_us: float = float("nan")     # rms symbol-to-symbol change of the timing error
    offset_ms: float = 0.0              # window offset that gave the best MER
    found: bool = True
    note: str = ""


def _demod(x, p0, scale, fs_in, L, n_sym, off_s):
    f = np.array(CARRIERS)
    w = int(WIN_S * fs_in)
    Y = np.empty((n_sym, len(f)), dtype=complex)
    for n in range(n_sym):
        tc = L.sym_start + (n + 0.5) / BAUD + off_s   # symbol centre, s after chirp start
        c = p0 + tc * fs_in * scale
        i0 = int(round(c - w / 2))
        idx = np.clip(np.arange(i0, i0 + w), 0, len(x) - 1)
        tt = (idx - p0) / (fs_in * scale)              # seconds in the player's time base
        Y[n] = (np.exp(-2j * np.pi * np.outer(f, tt)) @ x[idx]) * 2 / w
    # carriers are phase-continuous from the first symbol: re-reference to it
    return Y * np.exp(2j * np.pi * f * L.sym_start)


def _mer(Y, syms):
    nn = np.arange(len(Y))
    mer_k, gain, E2, S2 = [], [], 0.0, 0.0
    for k in range(Y.shape[1]):
        h = Y[:, k] / syms[:, k]
        a, b = np.polyfit(nn, np.unwrap(np.angle(h)), 1)
        est = np.mean(np.abs(h)) * np.exp(1j * (a * nn + b)) * syms[:, k]
        e2, s2 = np.sum(np.abs(Y[:, k] - est) ** 2), np.sum(np.abs(est) ** 2)
        mer_k.append(10 * np.log10(s2 / e2))
        gain.append(20 * np.log10(np.mean(np.abs(h))))
        E2, S2 = E2 + e2, S2 + s2
    return 10 * np.log10(S2 / E2), mer_k, np.array(gain)


def _timing(Y, syms):
    """Per-symbol timing error (us) from the slope of phase across the carriers."""
    f = np.array(CARRIERS)
    H = Y / syms
    H0 = np.median(H.real, axis=0) + 1j * np.median(H.imag, axis=0)   # static per-carrier gain
    r = H / H0
    tau = np.array([np.polyfit(f, np.unwrap(np.angle(r[n])), 1)[0] for n in range(len(r))]) / (2 * np.pi) * 1e6
    sm = np.convolve(tau, np.ones(20) / 20, mode="valid")
    return float(sm.max() - sm.min()), float(np.std(np.diff(tau)))


def analyze(x: np.ndarray, fs_in: float, syms: np.ndarray, fs_out: float) -> PathResult:
    x = np.asarray(x, dtype=np.float64)
    x = x - x.mean()
    n_sym = syms.shape[0]
    L = layout(fs_out, n_sym)
    ch = _chirp(fs_in)
    sep = L.chirp_sep * fs_in
    p0 = _find(x, ch, 0, int(len(x) - sep * 0.9))
    p1 = _find(x, ch, int(p0 + sep * 0.98), int(p0 + sep * 1.02 + len(ch)))
    scale = (p1 - p0) / sep                       # recorded samples per nominal sample
    ppm = (scale - 1) * 1e6
    lvl = 10 * np.log10(np.mean(x[int(p0):int(p1)] ** 2) / 0.5 + 1e-20)
    if abs(ppm) > 2000:
        return PathResult(lvl, float("nan"), [], [], float("nan"), ppm, found=False, note="chirps not found")
    # the chirps and the carriers see different group delays through filters, so
    # search for the window position (within the 10 ms symbol) that fits best
    best = None
    for off in np.arange(-3.0, 1.01, 0.5) * 1e-3:
        Y = _demod(x, p0, scale, fs_in, L, n_sym, off)
        m = _mer(Y, syms)
        if best is None or m[0] > best[1][0]:
            best = (off, m, Y)
    off, (mer, mer_k, gain), Y = best
    wander, jitter = _timing(Y, syms)
    rel = gain - gain.mean()
    return PathResult(float(lvl), float(mer), [round(float(v), 1) for v in mer_k],
                      [round(float(v), 2) for v in rel], float(rel.max() - rel.min()), float(ppm),
                      wander, jitter, float(off * 1e3))


# --- audio I/O (Windows desktop session) ------------------------------------------

@dataclass
class QamResult:
    ionos_setting: str
    paths: dict = field(default_factory=dict)     # "L0 1->2" -> PathResult as dict
    devices: dict = field(default_factory=dict)
    raw: dict = field(default_factory=dict, repr=False)   # "L0 1->2" -> (samples, fs_in, fs_out); not in JSON


def _play_record(sd, rec_devs: dict[int, int], play_dev: int, y: np.ndarray, fs_out: float):
    from .audio import _extra

    bufs: dict[int, list] = {k: [] for k in rec_devs}
    streams = []
    for k, dev in rec_devs.items():
        fs = float(sd.query_devices(dev)["default_samplerate"])

        def cb(indata, frames, t, status, k=k):
            bufs[k].append(indata[:, 0].copy())
        s = sd.InputStream(device=dev, channels=1, samplerate=fs, dtype="float32", callback=cb,
                           extra_settings=_extra(sd, dev))
        streams.append((k, s, fs))
    for _, s, _ in streams:
        s.start()
    time.sleep(0.3)
    ch = min(2, int(sd.query_devices(play_dev)["max_output_channels"]))
    sd.play(np.repeat(y[:, None], ch, axis=1), samplerate=fs_out, device=play_dev, blocking=True,
            extra_settings=_extra(sd, play_dev))
    time.sleep(0.3)
    out = {}
    for k, s, fs in streams:
        s.stop()
        s.close()
        out[k] = (np.concatenate(bufs[k]) if bufs[k] else np.zeros(1), fs)
    return out


def run_qam(stations, *, n_sym: int = 800, peak_dbfs: float = -1.0, levels_db=LEVELS_DB,
            ionos_setting: str = "", say=print) -> QamResult:
    import sounddevice as sd

    from .audio import pick_device

    devs, apis = sd.query_devices(), sd.query_hostapis()
    play = {s.number: pick_device(devs, apis, s.playback, "out") for s in stations}
    rec = {s.number: pick_device(devs, apis, s.capture, "in") for s in stations}
    res = QamResult(ionos_setting, devices={f"station{s.number}": {"play": devs[play[s.number]]["name"],
                                                                   "rec": devs[rec[s.number]]["name"]}
                                            for s in stations})
    for li, lv in enumerate(levels_db):
        for s in stations:
            fs_out = float(devs[play[s.number]]["default_samplerate"])
            y, syms = make_signal(fs_out, n_sym, peak_dbfs + lv)
            say(f"16QAM test signal from station {s.number}, level {lv:+.0f} dB ({len(y) / fs_out:.1f} s)...")
            got = _play_record(sd, rec, play[s.number], y, fs_out)
            for j, (x, fs_in) in got.items():
                key = f"L{li} {s.number}->{j}"
                res.paths[key] = asdict(analyze(x, fs_in, syms, fs_out))
                res.raw[key] = (x, fs_in, fs_out)
    return res


def format_qam(r: QamResult, levels_db=LEVELS_DB) -> str:
    lines = [f"IONOS: {r.ionos_setting or '(not set by hfbench)'}", "",
             "path  (plays -> records)  drive   level dBFS rms   MER dB   worst carrier   flatness dB"
             "   timing wander us p-p   jitter us    ppm",
             "-" * 135]
    for key, p in r.paths.items():
        li, path = key.split(" ")
        lv = levels_db[int(li[1:])]
        if not p["found"]:
            lines.append(f"{path:<26}{lv:>+5.0f}   {p['note']}")
            continue
        worst = min(p["mer_by_carrier"])
        lines.append(f"{path:<26}{lv:>+5.0f}{p['level_dbfs_rms']:>15.1f}{p['mer_db']:>10.1f}"
                     f"{worst:>14.1f}{p['flatness_db']:>15.1f}{p['wander_us']:>21.0f}{p['jitter_us']:>14.1f}"
                     f"{p['ppm']:>9.0f}")
    return "\n".join(lines)
