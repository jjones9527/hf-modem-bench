"""Tone-based level check for the two-station IONOS bench.

Plays a sine from each station's speaker output in turn while recording both
stations' microphone inputs. With the IONOS in half-duplex mode, both inputs
are mixed into one channel that feeds both outputs, so the four measured
levels L[i][j] (station i plays, station j records), in dB, are

    L[i][j] = T[i] + C + R[j]

where T is each station's transmit gain into the IONOS, R is each station's
receive gain and C is the common channel. Hence

    transmit mismatch  T1 - T2 = L11 - L21 = L12 - L22
    receive mismatch   R1 - R2 = L11 - L12 = L21 - L22

The two estimates of each must agree. If they don't, the IONOS isn't mixing
as assumed (check the Y cables). For a symmetric bench both mismatches should
be near 0 dB.

Analysis (numpy only) is separate from audio I/O (sounddevice), so it can be
tested anywhere. Audio I/O must run in the Windows desktop session, not over
SSH.
"""

from __future__ import annotations

import configparser
import math
from dataclasses import dataclass, asdict, field
from pathlib import Path

import numpy as np

BAND = (300.0, 3300.0)        # IONOS 3 kHz operating bandwidth
REF_BW = 3000.0               # S:N reference bandwidth (IONOS)
TONE_HZ = 1500.0
TONE_DBFS = -6.0


# --- analysis ------------------------------------------------------------------

@dataclass
class ToneStats:
    tone_dbfs: float          # tone power re full-scale sine
    noise_dbfs_3k: float      # noise power in 3000 Hz, re full-scale sine
    snr_db: float             # tone / noise in 3 kHz (IONOS S:N definition)
    h2_dbc: float             # 2nd harmonic re tone (in band: either side)
    h3_dbc: float             # 3rd harmonic re tone (4.5 kHz: above the IONOS filter,
                              #   so if present it was made after the IONOS, i.e. at the input)
    peak_dbfs: float
    clipped: bool


def _psd(x: np.ndarray, fs: float, nfft: int = 8192) -> tuple[np.ndarray, np.ndarray]:
    """One-sided Welch PSD (power per Hz, full-scale sine = 0.5 power), Hann, 50% overlap."""
    x = np.asarray(x, dtype=np.float64)
    x = x - x.mean()
    nfft = min(nfft, len(x))
    w = np.hanning(nfft)
    step = nfft // 2
    segs = [x[i:i + nfft] for i in range(0, len(x) - nfft + 1, step)]
    acc = np.zeros(nfft // 2 + 1)
    for s in segs:
        acc += np.abs(np.fft.rfft(s * w)) ** 2
    psd = acc / len(segs) / (fs * np.sum(w ** 2))
    psd[1:-1] *= 2.0
    return np.fft.rfftfreq(nfft, 1.0 / fs), psd


def _band_power(f, p, lo, hi) -> float:
    m = (f >= lo) & (f <= hi)
    return float(np.sum(p[m]) * (f[1] - f[0]))


def _db(p: float) -> float:
    return 10.0 * math.log10(max(p, 1e-20))


def analyze(x: np.ndarray, fs: float, tone_hz: float = TONE_HZ) -> ToneStats:
    f, p = _psd(x, fs)
    df = f[1] - f[0]
    half = max(4 * df, 15.0)            # Hann main lobe + slack
    tone = _band_power(f, p, tone_hz - half, tone_hz + half)
    h2 = _band_power(f, p, 2 * tone_hz - half, 2 * tone_hz + half)
    h3 = _band_power(f, p, 3 * tone_hz - half, 3 * tone_hz + half) if 3 * tone_hz + half < fs / 2 else 0.0
    # noise density from the band, excluding tone/harmonic neighbourhoods (median: robust to hum/spurs)
    m = (f >= BAND[0]) & (f <= BAND[1])
    for k in (1, 2):
        m &= np.abs(f - k * tone_hz) > 3 * half
    density = float(np.median(p[m])) if m.any() else 0.0
    noise = density * REF_BW
    full = 0.5
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    return ToneStats(
        tone_dbfs=_db(tone / full), noise_dbfs_3k=_db(noise / full),
        snr_db=_db(tone) - _db(noise), h2_dbc=_db(h2) - _db(tone), h3_dbc=_db(h3) - _db(tone),
        peak_dbfs=20 * math.log10(max(peak, 1e-10)), clipped=peak >= 0.98,
    )


def noise_floor_dbfs_3k(x: np.ndarray, fs: float) -> float:
    """Band noise with nothing playing, scaled to 3 kHz, re full-scale sine."""
    f, p = _psd(x, fs)
    m = (f >= BAND[0]) & (f <= BAND[1])
    return _db(float(np.median(p[m])) * REF_BW / 0.5)


@dataclass
class Mismatch:
    tx_db: float              # station 1 minus station 2, into the IONOS (nan if unknown)
    rx_db: float              # station 1 minus station 2, at the microphones
    tx_spread_db: float       # max disagreement between the available estimates
    rx_spread_db: float
    consistent: bool
    n_tx: int = 0             # number of estimates used
    n_rx: int = 0


def mismatch(L: dict[tuple[int, int], float], tol_db: float = 1.0, *,
             clipped: set[tuple[int, int]] = frozenset(),
             floors: dict[int, float] | None = None) -> Mismatch:
    """L[(i, j)]: tone level in dBFS when station i plays and station j records.
    Clipped paths are left out. With the IONOS noise dominating, both
    microphones hear the same noise, so floor1 - floor2 is another receive
    estimate."""
    ok = lambda *ks: all(k not in clipped for k in ks)
    tx = [L[1, j] - L[2, j] for j in (1, 2) if ok((1, j), (2, j))]
    rx = [L[i, 1] - L[i, 2] for i in (1, 2) if ok((i, 1), (i, 2))]
    if floors:
        rx.append(floors[1] - floors[2])
    mean = lambda v: sum(v) / len(v) if v else float("nan")
    spread = lambda v: (max(v) - min(v)) if len(v) > 1 else 0.0
    return Mismatch(mean(tx), mean(rx), spread(tx), spread(rx),
                    bool(tx) and bool(rx) and max(spread(tx), spread(rx)) <= tol_db, len(tx), len(rx))


def tx_offsets(paths: dict[str, dict], setting_snr: float) -> dict[int, float]:
    """Each station's transmit level relative to the IONOS S:N reference:
    measured S:N of its tone at the *other* station minus the IONOS setting.
    0 dB means the IONOS setting is the true S:N for that station's signal.
    (Valid because the IONOS adds noise at a fixed level; see bench-setup.md.)
    Device noise adds to the IONOS noise, so at high settings (within ~10 dB
    of the device noise) this reads low. Measure at a moderate setting (WGN 20)."""
    out = {}
    for i in (1, 2):
        for k in (f"{i}->{3 - i}", f"{i}->{i}"):
            if k in paths and not paths[k]["clipped"]:
                out[i] = paths[k]["snr_db"] - setting_snr
                break
    return out


def advice(m: Mismatch, L: dict[tuple[int, int], float], drive: tuple[int | None, int | None] = (None, None),
           target_rx_dbfs: float = -12.0, tol_db: float = 1.0, *,
           tx_ref: dict[int, float] | None = None, clipped: set[tuple[int, int]] = frozenset()) -> list[str]:
    out = []
    if not m.consistent and (m.n_tx > 1 or m.n_rx > 1):
        out.append(f"Estimates disagree by up to {max(m.tx_spread_db, m.rx_spread_db):.1f} dB: "
                   "the IONOS may not be mixing both inputs to both outputs. Check the Y cables "
                   "(they must be L/R splitters) and the IONOS mode before trusting the numbers below.")
    # 1. transmit: against the IONOS reference if known, else relative
    if tx_ref:
        for i, off in sorted(tx_ref.items()):
            if abs(off) <= tol_db:
                out.append(f"Transmit, station {i}: at the IONOS reference ({off:+.1f} dB). Leave it.")
            else:
                verb = "Raise" if off < 0 else "Lower"
                out.append(f"Transmit, station {i}: {abs(off):.1f} dB {'below' if off < 0 else 'above'} the IONOS reference, "
                           f"so its real S:N is {off:+.1f} dB off the setting. {verb} station {i}'s level into the IONOS "
                           f"by {abs(off):.1f} dB (Windows speaker level; for more than ~6 dB use one IONOS CH IN step).")
    elif not math.isnan(m.tx_db):
        if abs(m.tx_db) > tol_db:
            loud, quiet = (1, 2) if m.tx_db > 0 else (2, 1)
            out.append(f"Transmit: station {loud} reaches the IONOS {abs(m.tx_db):.1f} dB hotter than station {quiet}.")
        else:
            out.append(f"Transmit levels match ({m.tx_db:+.1f} dB).")
    # 2. receive
    if not math.isnan(m.rx_db):
        if abs(m.rx_db) > tol_db:
            loud, quiet = (1, 2) if m.rx_db > 0 else (2, 1)
            out.append(f"Receive: station {loud}'s microphone is {abs(m.rx_db):.1f} dB more sensitive than station {quiet}'s. "
                       f"Bring them together (IONOS CH OUT steps for large changes, Windows microphone level to trim). "
                       f"Fix transmit first: raising a weak transmitter raises what the other microphone receives.")
        else:
            out.append(f"Receive levels match ({m.rx_db:+.1f} dB).")
    for j in (1, 2):
        lvl = L.get((3 - j, j))
        if lvl is not None and (3 - j, j) not in clipped and abs(lvl - target_rx_dbfs) > 3:
            out.append(f"Station {j} receives the other station at {lvl:.1f} dBFS; aim for about {target_rx_dbfs:.0f} dBFS "
                       f"once transmit is fixed.")
    for (i, j) in sorted(clipped):
        who = "its own transmission" if i == j else f"station {i}"
        out.append(f"Station {j}'s microphone clips on {who}: lower its input level"
                   f"{' (harmless while it transmits, but a sign its gain is too high)' if i == j else ''}.")
    d1, d2 = drive
    if d1 and d2 and d1 != d2:
        extra = 20 * math.log10(d1 / d2)
        out.append(f"ARDOP DriveLevel differs ({d1} vs {d2}, {extra:+.1f} dB): the tone bypasses it, so real ARDOP "
                   f"traffic adds that to the transmit difference. Set both DriveLevels the same.")
    return out


def device_noise_db(floor_hi_snr: float, floor_lo_snr: float, snr_hi: float, snr_lo: float) -> float | None:
    """A microphone's own noise relative to the IONOS reference signal, in dB
    (negative = below), from noise floors measured at two IONOS S:N settings.
    The IONOS noise scales with the setting and the device noise doesn't."""
    expect = 10 ** ((snr_hi - snr_lo) / 10)          # IONOS noise ratio
    got = 10 ** ((floor_lo_snr - floor_hi_snr) / 10)
    if got >= expect or got <= 1:
        return None                                   # device noise not measurable
    d_over_i = (expect - got) / (got - 1)             # device / IONOS noise at snr_hi
    return 10 * math.log10(d_over_i) - snr_hi


# --- station configuration from ARDOP_Win TNC.ini ------------------------------

@dataclass
class Station:
    number: int
    playback: str
    capture: str
    drive_level: int | None = None


def station_from_ardop_ini(number: int, install_dir: str | Path) -> Station:
    cp = configparser.ConfigParser(interpolation=None, strict=False)
    raw = Path(install_dir, "ARDOP_Win TNC.ini").read_bytes().decode("utf-8-sig", errors="replace")
    cp.read_string(raw)
    sec = cp["ARDOP_Win TNC"]
    dl = sec.get("DriveLevel")
    return Station(number, sec["PlaybackDevice"], sec["CaptureDevice"], int(dl) if dl else None)


def pick_device(devices: list[dict], hostapis: list[dict], name: str, kind: str) -> int:
    """Index of the device called `name` with input ('in') or output ('out') channels.
    Prefers WASAPI (full names), then any host API; exact match before prefix match
    (MME truncates names to 31 characters)."""
    chan = "max_input_channels" if kind == "in" else "max_output_channels"
    api_name = {i: h["name"] for i, h in enumerate(hostapis)}
    want = name.strip().lower()

    def candidates(pred):
        return [i for i, d in enumerate(devices)
                if d[chan] > 0 and pred(d["name"].strip().lower())]

    for pred in (lambda n: n == want, lambda n: want.startswith(n) and len(n) >= 20):
        c = candidates(pred)
        if c:
            c.sort(key=lambda i: 0 if "WASAPI" in api_name.get(devices[i]["hostapi"], "") else 1)
            return c[0]
    raise LookupError(f"no {kind}put device named {name!r}")


# --- audio I/O (Windows desktop session) ---------------------------------------

@dataclass
class CheckResult:
    ionos_setting: str
    floor_dbfs_3k: dict[int, float]
    paths: dict[str, dict]           # "1->2": ToneStats as dict
    mismatch: dict
    advice: list[str]
    devices: dict = field(default_factory=dict)
    tx_ref_db: dict = field(default_factory=dict)


def _sine(fs: float, seconds: float, hz: float, dbfs: float, channels: int) -> np.ndarray:
    n = int(fs * seconds)
    t = np.arange(n) / fs
    a = 10 ** (dbfs / 20.0)
    y = a * np.sin(2 * np.pi * hz * t)
    ramp = int(0.02 * fs)
    env = np.ones(n)
    env[:ramp] = np.linspace(0, 1, ramp)
    env[-ramp:] = np.linspace(1, 0, ramp)
    y = (y * env).astype(np.float32)
    return np.repeat(y[:, None], channels, axis=1)


def _extra(sd, dev):
    """WASAPI shared mode needs format conversion for mono/odd rates."""
    api = sd.query_hostapis(sd.query_devices(dev)["hostapi"])["name"]
    if "WASAPI" in api:
        return sd.WasapiSettings(auto_convert=True)
    return None


def _record_while(sd, rec_devs: dict[int, int], play_dev: int | None, seconds: float,
                  tone_hz: float, tone_dbfs: float) -> dict[int, tuple[np.ndarray, float]]:
    """Record all rec_devs for `seconds`; if play_dev is set, play a tone on it meanwhile.
    Returns {station: (mono samples, fs)} trimmed to the steady middle."""
    import threading
    import time

    bufs: dict[int, list] = {k: [] for k in rec_devs}
    streams = []
    for k, dev in rec_devs.items():
        info = sd.query_devices(dev)
        fs = float(info["default_samplerate"])

        def cb(indata, frames, t, status, k=k):
            bufs[k].append(indata[:, 0].copy())
        s = sd.InputStream(device=dev, channels=1, samplerate=fs, dtype="float32", callback=cb,
                           extra_settings=_extra(sd, dev))
        streams.append((k, s, fs))
    for _, s, _ in streams:
        s.start()
    time.sleep(0.4)
    if play_dev is not None:
        info = sd.query_devices(play_dev)
        fs_out = float(info["default_samplerate"])
        ch = min(2, int(info["max_output_channels"]))
        sd.play(_sine(fs_out, seconds, tone_hz, tone_dbfs, ch), samplerate=fs_out, device=play_dev,
                blocking=True, extra_settings=_extra(sd, play_dev))
    else:
        time.sleep(seconds)
    time.sleep(0.2)
    out = {}
    for k, s, fs in streams:
        s.stop()
        s.close()
        x = np.concatenate(bufs[k]) if bufs[k] else np.zeros(1)
        lo, hi = int(0.6 * fs), len(x) - int(0.6 * fs)   # drop ramps and start-up
        out[k] = (x[lo:hi] if hi > lo else x, fs)
    return out


def run_check(stations: tuple[Station, Station], *, seconds: float = 3.0, tone_hz: float = TONE_HZ,
              tone_dbfs: float = TONE_DBFS, ionos_setting: str = "", say=print) -> CheckResult:
    import sounddevice as sd

    devs = sd.query_devices()
    apis = sd.query_hostapis()
    play = {s.number: pick_device(devs, apis, s.playback, "out") for s in stations}
    rec = {s.number: pick_device(devs, apis, s.capture, "in") for s in stations}
    names = {f"station{s.number}": {"play": devs[play[s.number]]["name"], "rec": devs[rec[s.number]]["name"],
                                    "api": apis[devs[rec[s.number]]["hostapi"]]["name"]} for s in stations}

    say("Measuring noise floor (nothing playing)...")
    quiet = _record_while(sd, rec, None, seconds, tone_hz, tone_dbfs)
    floor = {k: noise_floor_dbfs_3k(x, fs) for k, (x, fs) in quiet.items()}

    L, paths = {}, {}
    for s in stations:
        say(f"Tone from station {s.number} speaker...")
        got = _record_while(sd, rec, play[s.number], seconds, tone_hz, tone_dbfs)
        for j, (x, fs) in got.items():
            st = analyze(x, fs, tone_hz)
            L[s.number, j] = st.tone_dbfs
            paths[f"{s.number}->{j}"] = asdict(st)

    return evaluate(ionos_setting, floor, paths, names,
                    (stations[0].drive_level, stations[1].drive_level))


def evaluate(ionos_setting: str, floor: dict, paths: dict, names: dict | None = None,
             drive: tuple[int | None, int | None] = (None, None)) -> CheckResult:
    """Derive mismatch, reference offsets and advice from measured paths.
    Also used to re-analyze saved results (hfbench audio report)."""
    floor = {int(k): v for k, v in floor.items()}
    L = {(int(k[0]), int(k[-1])): v["tone_dbfs"] for k, v in paths.items()}
    clipped = {(int(k[0]), int(k[-1])) for k, v in paths.items() if v["clipped"]}
    m = mismatch(L, clipped=clipped, floors=floor)
    ref = {}
    if ionos_setting.upper().startswith("WGN:"):
        ref = tx_offsets(paths, float(ionos_setting.split(":")[1]))
    adv = advice(m, L, drive, tx_ref=ref, clipped=clipped)
    return CheckResult(ionos_setting, floor, paths, asdict(m), adv, names or {}, ref)


def format_result(r: CheckResult) -> str:
    lines = [f"IONOS: {r.ionos_setting or '(not set by hfbench)'}",
             "",
             "path  (station plays -> station records)   level dBFS   S:N(3k) dB   H2 dBc   H3 dBc   peak dBFS",
             "-" * 98]
    for k in ("1->1", "1->2", "2->1", "2->2"):
        p = r.paths[k]
        flag = "  CLIPPED" if p["clipped"] else ""
        lines.append(f"{k:<42}{p['tone_dbfs']:>8.1f}{p['snr_db']:>13.1f}{p['h2_dbc']:>10.1f}"
                     f"{p['h3_dbc']:>9.1f}{p['peak_dbfs']:>11.1f}{flag}")
    lines += ["",
              f"noise floor, nothing playing (3 kHz):  station 1 mic {r.floor_dbfs_3k[1]:.1f} dBFS,"
              f"  station 2 mic {r.floor_dbfs_3k[2]:.1f} dBFS",
              f"transmit mismatch (st1 - st2): {r.mismatch['tx_db']:+.1f} dB   "
              f"receive mismatch (st1 - st2): {r.mismatch['rx_db']:+.1f} dB   "
              f"(spread {max(r.mismatch['tx_spread_db'], r.mismatch['rx_spread_db']):.1f} dB; clipped paths excluded)"]
    if r.tx_ref_db:
        lines.append("transmit vs IONOS reference (0 = real S:N equals the setting):  " +
                     "   ".join(f"station {i} {v:+.1f} dB" for i, v in sorted(r.tx_ref_db.items())))
    lines += [""]
    lines += [f"* {a}" for a in r.advice]
    return "\n".join(lines)
