import numpy as np
import pytest

from hfbench import audio


def _series(snr_db, seed=0, block_s=0.0213, total_s=120.0):
    """Band-power blocks as `record_band_power` makes them: chi-square-ish noise around
    1e-5 (about 60 independent samples per block) plus bursts: 4.4 s data every 5.3 s
    from station 2, and 0.4 s ACKs from station 1 in between (ARDOP 16QAM rhythm)."""
    rng = np.random.default_rng(seed)
    t = np.arange(0, total_s, block_s) + 1_700_000_000.0
    noise = 1e-5 * rng.chisquare(60, len(t)) / 60
    sig = np.zeros(len(t))
    ivs = {1: [], 2: []}
    t0 = t[0] + 2.0
    while t0 + 5.3 < t[-1]:
        ivs[2].append((t0, t0 + 4.4))
        ivs[1].append((t0 + 4.65, t0 + 5.05))
        t0 += 5.3
    for a, b in ivs[1] + ivs[2]:
        sig[(t >= a) & (t <= b)] = 1e-5 * 10 ** (snr_db / 10)
    p = noise + sig * rng.chisquare(60, len(t)) / 60
    return [(float(a), float(b)) for a, b in zip(t, p)], ivs


@pytest.mark.parametrize("snr_db", [10, 3, 0])
def test_energy_bursts_match_truth(snr_db):
    pts, truth = _series(snr_db)
    found = audio.ptt_one_way(audio.bursts_from_energy(pts), sender=2)
    assert abs(len(found[2]) - len(truth[2])) <= 1
    starts = [min(abs(f[0] - tr[0]) for f in found[2]) for tr in truth[2]]
    assert np.median(starts) < 0.1
    res = audio.analyze_listen({1: pts, 2: pts}, found, None)
    data = [d for d in res["directions"] if d["kind"] == "data"][0]
    assert data["snr_median_db"] == pytest.approx(snr_db, abs=1.0)


def test_energy_below_detection_limit_finds_little():
    pts, truth = _series(-8)
    found = audio.bursts_from_energy(pts)
    # a 1 dB rise threshold can't see -8 dB bursts reliably: documented limit
    assert len([b for b in found if b[1] - b[0] >= 1.0]) < len(truth[2]) // 2
