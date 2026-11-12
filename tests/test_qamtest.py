import numpy as np
import pytest

from hfbench import qamtest as q


def _channel(y, fs_out, fs_in, *, delay_s=0.123, gain=0.3, snr_db=None, ppm=0.0, clip=None, seed=2):
    """Resample y (fs_out) to fs_in with a rate error, delay, gain, optional clip and noise."""
    rng = np.random.default_rng(seed)
    t_in = np.arange(int((len(y) / fs_out + 2 * delay_s) * fs_in)) / fs_in
    t_src = (t_in - delay_s) * (1 + ppm * 1e-6)   # player time at each recorded sample
    x = np.interp(t_src * fs_out, np.arange(len(y)), y, left=0.0, right=0.0) * gain
    if clip is not None:
        x = np.clip(x, -clip, clip)
    if snr_db is not None:
        p = np.mean(x[x != 0] ** 2)
        x = x + rng.normal(0, np.sqrt(p / 10 ** (snr_db / 10)), len(x))
    return x


def test_clean_path_has_high_mer():
    y, syms = q.make_signal(48000.0, n_sym=200)
    r = q.analyze(_channel(y, 48000.0, 48000.0), 48000.0, syms, 48000.0)
    assert r.found
    assert r.mer_db > 35
    assert r.flatness_db < 0.5


def test_mer_tracks_noise():
    y, syms = q.make_signal(48000.0, n_sym=300)
    r = q.analyze(_channel(y, 48000.0, 48000.0, snr_db=20), 48000.0, syms, 48000.0)
    # wideband noise in 0..24 kHz; in-carrier S:N is far higher than 20 dB broadband
    assert 20 < r.mer_db < 45


def test_rate_error_is_measured_and_tracked():
    y, syms = q.make_signal(48000.0, n_sym=300)
    r = q.analyze(_channel(y, 48000.0, 48000.0, ppm=80.0), 48000.0, syms, 48000.0)
    assert r.ppm == pytest.approx(-80.0, abs=5)   # recorder runs slow re the player
    assert r.mer_db > 30


def test_clipping_degrades_mer_and_lower_level_recovers():
    y, syms = q.make_signal(48000.0, n_sym=300)
    hard = q.analyze(_channel(y, 48000.0, 48000.0, gain=1.0, clip=0.3), 48000.0, syms, 48000.0)
    y2, syms2 = q.make_signal(48000.0, n_sym=300, peak_dbfs=-1.0 - 12)
    soft = q.analyze(_channel(y2, 48000.0, 48000.0, gain=1.0, clip=0.3), 48000.0, syms2, 48000.0)
    assert hard.mer_db < 20
    assert soft.mer_db > hard.mer_db + 10


def test_missing_signal_is_reported():
    _, syms = q.make_signal(48000.0, n_sym=100)
    x = np.random.default_rng(0).normal(0, 0.01, 48000 * 3)
    r = q.analyze(x, 48000.0, syms, 48000.0)
    assert not r.found or r.mer_db < 5
