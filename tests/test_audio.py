"""Tone-check analysis tests with synthetic signals of known level."""

import math

import numpy as np
import pytest

from hfbench import audio as au
from hfbench.ionos import Ionos, IonosError

FS = 48000.0


def sig(seconds=3.0, tone_dbfs=-12.0, snr_3k=None, h2_dbc=None, h3_dbc=None, seed=1, hz=1500.0):
    rng = np.random.default_rng(seed)
    t = np.arange(int(FS * seconds)) / FS
    a = 10 ** (tone_dbfs / 20)
    x = a * np.sin(2 * np.pi * hz * t)
    if h2_dbc is not None:
        x += a * 10 ** (h2_dbc / 20) * np.sin(2 * np.pi * 2 * hz * t)
    if h3_dbc is not None:
        x += a * 10 ** (h3_dbc / 20) * np.sin(2 * np.pi * 3 * hz * t)
    if snr_3k is not None:
        # white noise whose power in 3000 Hz is tone_power / snr; total over fs/2
        p_tone = a * a / 2
        p_3k = p_tone / 10 ** (snr_3k / 10)
        sigma = math.sqrt(p_3k * (FS / 2) / 3000.0)
        x = x + rng.normal(0, sigma, len(t))
    return x


def test_tone_level_and_snr():
    st = au.analyze(sig(tone_dbfs=-12, snr_3k=30), FS)
    assert st.tone_dbfs == pytest.approx(-12, abs=0.2)
    assert st.snr_db == pytest.approx(30, abs=0.5)
    assert st.noise_dbfs_3k == pytest.approx(-42, abs=0.5)
    assert not st.clipped and -12 < st.peak_dbfs < -9   # sine peak -12 dBFS plus noise


@pytest.mark.parametrize("snr", [10, 20, 40, 50])
def test_snr_range(snr):
    assert au.analyze(sig(snr_3k=snr), FS).snr_db == pytest.approx(snr, abs=0.7)


def test_harmonics_and_clipping():
    st = au.analyze(sig(tone_dbfs=-6, snr_3k=50, h2_dbc=-35, h3_dbc=-28), FS)
    assert st.h2_dbc == pytest.approx(-35, abs=0.5)
    assert st.h3_dbc == pytest.approx(-28, abs=0.5)
    clipped = np.clip(sig(tone_dbfs=0, snr_3k=50), -0.7, 0.7) / 0.7
    st = au.analyze(clipped, FS)
    assert st.clipped and st.h3_dbc > -20  # hard clipping makes strong odd harmonics


def test_noise_floor():
    x = sig(tone_dbfs=-200, snr_3k=None)  # silence...
    x = x + np.random.default_rng(2).normal(0, 1e-3, len(x))
    # white noise sigma=1e-3: power in 3 kHz = 1e-6 * 3000/24000; re 0.5
    expected = 10 * math.log10(1e-6 * 3000 / 24000 / 0.5)
    assert au.noise_floor_dbfs_3k(x, FS) == pytest.approx(expected, abs=0.5)


def levels(t1, t2, r1, r2, c=-20.0):
    return {(i, j): t + c + r for i, t in ((1, t1), (2, t2)) for j, r in ((1, r1), (2, r2))}


def test_mismatch_separates_tx_and_rx():
    m = au.mismatch(levels(t1=3.0, t2=0.0, r1=-1.0, r2=1.5))
    assert m.tx_db == pytest.approx(3.0) and m.rx_db == pytest.approx(-2.5)
    assert m.consistent and m.tx_spread_db == pytest.approx(0)


def test_mismatch_flags_inconsistent_mixing():
    L = levels(0, 0, 0, 0)
    L[1, 1] -= 30  # station 1 doesn't hear itself: outputs not both fed by the mix
    m = au.mismatch(L)
    assert not m.consistent
    assert "Y cables" in au.advice(m, L)[0]


def test_mismatch_ignores_clipped_path_and_uses_floors():
    # the 10 Nov 2026 bench at WGN 40: 2->2 clipped at +2 dBFS
    L = {(1, 1): -37.8, (1, 2): -16.9, (2, 1): -10.5, (2, 2): 2.0}
    m = au.mismatch(L, clipped={(2, 2)}, floors={1: -53.3, 2: -32.3})
    assert (m.n_tx, m.n_rx) == (1, 2)
    assert m.tx_db == pytest.approx(-27.3, abs=0.05)
    assert m.rx_db == pytest.approx(-20.95, abs=0.05) and m.consistent


def test_tx_offsets_against_ionos_reference():
    paths = {"1->2": {"snr_db": 15.2, "clipped": False}, "1->1": {"snr_db": 15.3, "clipped": False},
             "2->1": {"snr_db": 42.7, "clipped": False}, "2->2": {"snr_db": 44.7, "clipped": True}}
    ref = au.tx_offsets(paths, 40)
    assert ref == {1: pytest.approx(-24.8), 2: pytest.approx(2.7)}
    adv = " ".join(au.advice(au.mismatch({(1, 1): 0, (1, 2): 0, (2, 1): 0, (2, 2): 0}),
                             {(1, 1): 0, (1, 2): 0, (2, 1): 0, (2, 2): 0}, tx_ref=ref))
    assert "Raise station 1's level into the IONOS by 24.8 dB" in adv
    assert "Lower station 2's level into the IONOS by 2.7 dB" in adv


def test_device_noise_from_two_settings():
    # floor rose 19.1 dB from WGN 40 to 20: device noise ~6.4 dB under IONOS noise at 40 -> ~46 dB under ref
    assert au.device_noise_db(-53.3, -34.2, 40, 20) == pytest.approx(-46.4, abs=0.2)
    assert au.device_noise_db(-53.3, -33.3, 40, 20) is None   # exactly 20 dB: no device noise visible


def test_advice_wording_and_drive_level():
    L = levels(t1=2.0, t2=0.0, r1=0.0, r2=0.0, c=-12.0 - 1.0)
    adv = " ".join(au.advice(au.mismatch(L), L, drive=(90, 75)))
    assert "station 1 reaches the IONOS 2.0 dB hotter" in adv
    assert "Receive levels match" in adv
    assert "DriveLevel differs (90 vs 75, +1.6 dB)" in adv


def test_station_from_ardop_ini(tmp_path):
    (tmp_path / "ARDOP_Win TNC.ini").write_bytes(
        "﻿\r\n[ARDOP_Win TNC]\r\nCaptureDevice=Microphone (C-Media USB Audio Device   )\r\n"
        "PlaybackDevice=Speakers (C-Media USB Audio Device   )\r\nDriveLevel=75\r\n[Radio]\r\nX=1\r\n".encode())
    s = au.station_from_ardop_ini(2, tmp_path)
    assert (s.capture, s.playback, s.drive_level) == (
        "Microphone (C-Media USB Audio Device   )", "Speakers (C-Media USB Audio Device   )", 75)


def test_pick_device_prefers_wasapi_and_handles_mme_truncation():
    apis = [{"name": "MME"}, {"name": "Windows WASAPI"}]
    devs = [
        {"name": "Microphone (C-Media USB Audio D", "hostapi": 0, "max_input_channels": 1, "max_output_channels": 0},
        {"name": "Microphone (USB Audio Device)", "hostapi": 0, "max_input_channels": 1, "max_output_channels": 0},
        {"name": "Microphone (C-Media USB Audio Device   )", "hostapi": 1, "max_input_channels": 1, "max_output_channels": 0},
        {"name": "Speakers (USB Audio Device)", "hostapi": 1, "max_input_channels": 0, "max_output_channels": 2},
    ]
    assert au.pick_device(devs, apis, "Microphone (C-Media USB Audio Device   )", "in") == 2
    assert au.pick_device(devs, apis, "Microphone (USB Audio Device)", "in") == 1   # only MME has it
    assert au.pick_device(devs, apis, "Speakers (USB Audio Device)", "out") == 3
    with pytest.raises(LookupError):
        au.pick_device(devs, apis, "Speakers (USB Audio Device)", "in")
    apis_mme = [{"name": "MME"}]
    assert au.pick_device(devs[:1], apis_mme, "Microphone (C-Media USB Audio Device   )", "in") == 0


class NullSerial:
    def __init__(self):
        self.sent = []

    def reset_input_buffer(self):
        pass

    def write(self, d):
        self.sent.append(d)

    def readline(self):
        return b"OK\r\n"


@pytest.mark.parametrize("cmd", ["BUSY:", "busy:", "CH1 OUT:2", "ch2 in:200"])
def test_ionos_guard_blocks_before_sending(cmd):
    ser = NullSerial()
    with pytest.raises(IonosError, match="refusing"):
        Ionos(ser).apply(f"WGN:20; {cmd}")
    assert ser.sent == []  # nothing at all was sent


def test_ionos_gains_allowed_explicitly_but_busy_never():
    ser = NullSerial()
    Ionos(ser, allow_gains=True).apply("CH1 OUT:1")
    assert ser.sent == [b"CH1 OUT:1\r\n"]
    with pytest.raises(IonosError):
        Ionos(ser, allow_gains=True).send("BUSY:")
