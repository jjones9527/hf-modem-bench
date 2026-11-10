"""Parser tests against real (redacted) Winlink Express 1.8.6.0 / ARDOP_Win 1.0.2.9
logs from a two-instance bench session on 2026-11-10. Station 1 = N0AAA,
station 2 = N0BBB; both ends of every session are present."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from hfbench import logparse as lp
from hfbench.cli import main

FX = Path(__file__).parent / "fixtures"
STN1_WL = FX / "winlink_ardop_p2p_20261110.log"
STN1_ARDOP = FX / "ardop_arqsession_20261110.log"
STN2_WL = FX / "stn2_winlink_ardop_p2p_20261110.log"
STN2_ARDOP = FX / "stn2_ardop_arqsession_20261110.log"


def utc(h, m, s):
    return datetime(2026, 11, 10, h, m, s, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def stn1():
    return lp.parse_winlink_log(STN1_WL)


def test_sessions_found_and_closed(stn1):
    assert len(stn1) == 6
    assert all(s.closed and s.transport == "Ardop P2P" and s.peer == "N0BBB" for s in stn1)
    assert [len(s.transfers) for s in stn1] == [0, 0, 1, 0, 1, 8]
    s = stn1[5]
    assert (s.connected_utc, s.disconnected_utc) == (utc(17, 49, 28), utc(18, 39, 36))
    assert (s.messages_sent, s.bytes_sent, s.messages_received, s.bytes_received) == (4, 170106, 4, 170154)
    assert s.session_time_s == 50 * 60 + 1
    assert (s.avg_bytes_per_min, s.peak_1min_bytes_per_min) == (15252, 15252)
    assert s.dial_khz == 7098.5 and s.sideband == "USB" and s.winlink_version == "1.8.6.0"


def test_tx_transfer(stn1):
    t = stn1[2].transfers[0]
    assert (t.mid, t.direction, t.completed) == ("IYNCRCASTUY3", "tx", True)
    assert (t.uncompressed_bytes, t.compressed_bytes) == (51433, 42205)
    assert (t.start_utc, t.end_utc) == (utc(17, 25, 14), utc(17, 29, 30))
    assert (t.wire_bytes, t.winlink_time_s, t.winlink_bytes_per_min) == (42559, 255, 9985)
    assert t.goodput_bps == pytest.approx(42205 * 8 / 255)


def test_rx_transfer(stn1):
    t = stn1[4].transfers[0]
    assert (t.mid, t.direction, t.completed) == ("PLYBTHW27AG9", "rx", True)
    assert (t.uncompressed_bytes, t.compressed_bytes) == (51433, 42206)
    assert (t.start_utc, t.end_utc, t.winlink_time_s) == (utc(17, 32, 3), utc(17, 35, 55), 231)


def test_direction_alternates_in_long_session(stn1):
    dirs = [t.direction for t in stn1[5].transfers]
    assert dirs == ["rx", "tx"] * 4
    # The long session's tx direction ran at about half speed (see ardop test below).
    tx = [t.goodput_bps for t in stn1[5].transfers if t.direction == "tx"]
    rx = [t.goodput_bps for t in stn1[5].transfers if t.direction == "rx"]
    assert max(tx) < 0.6 * min(rx)


def test_both_ends_agree_on_mids_and_sizes(stn1):
    stn2 = lp.parse_winlink_log(STN2_WL)
    assert len(stn2) == len(stn1)
    for a, b in zip(stn1, stn2):
        assert b.peer == "N0AAA"
        assert abs((a.connected_utc - b.connected_utc).total_seconds()) <= 5
        ta = {t.mid: t for t in a.transfers}
        tb = {t.mid: t for t in b.transfers}
        assert ta.keys() == tb.keys()
        for mid in ta:
            assert {ta[mid].direction, tb[mid].direction} == {"tx", "rx"}
            assert ta[mid].compressed_bytes == tb[mid].compressed_bytes


def test_ardop_stats_and_matching(stn1):
    ardop = lp.parse_ardop_sessions(STN1_ARDOP)
    assert len(ardop) == 6
    a = ardop[4]
    assert (a.end_utc, a.tnc_version, a.peer, a.minutes) == (utc(17, 36, 12), "1.0.2.9", "N0BBB", 4.8)
    assert (a.bandwidth_hz, a.round_trip_ms, a.avg_leader_snr_db) == (2000, 330, 20.6)
    assert (a.bytes_sent, a.bytes_received, a.throughput_bytes_per_min) == (68, 42720, 8880)
    assert (a.mode_shift_ups, a.mode_shift_downs, a.link_turnovers) == (1, 0, 6)
    assert a.rx_frame_quality == {"4FSK": (98, 17), "4PSK": (98, 6), "8PSK": (99, 2), "16QAM": (98, 40)}
    pairs = lp.match_ardop(stn1, ardop)
    assert sorted(pairs) == list(range(6))
    assert pairs[5].minutes == 50.2


def test_ardop_snr_exposes_asymmetric_channel():
    """Session 6: station 2 measured ~8 dB lower S:N than station 1 on what
    should be a symmetric channel -- the bench check this data is for."""
    s1 = lp.parse_ardop_sessions(STN1_ARDOP)[5]
    s2 = lp.parse_ardop_sessions(STN2_ARDOP)[5]
    assert (s1.avg_leader_snr_db, s2.avg_leader_snr_db) == (18.6, 11.9)
    assert s2.failed_frame_decodes == 30


def test_unclosed_session_is_kept():
    lines = [
        "2026/11/10 10:00:00 1.8.6.0 *** VARA HF P2P *** Connected to Peer: N0BBB @ 2026/11/10 10:00:00  USB Dial: 7098.500",
        "2026/11/10 10:00:05 1.8.6.0 *** VARA HF P2P    FC EM ABCDEF123456 1000 900 0",
        "2026/11/10 10:00:06 1.8.6.0 *** VARA HF P2P *** Sending ABCDEF123456.",
        "2026/11/10 10:05:00 1.8.6.0 *** Ardop P2P *** Connected to Peer: N0CCC @ 2026/11/10 10:05:00  USB Dial: 7098.500",
    ]
    s = lp.parse_winlink_log(lines)
    assert [x.transport for x in s] == ["VARA HF P2P", "Ardop P2P"]
    t = s[0].transfers[0]
    assert (s[0].closed, t.direction, t.compressed_bytes, t.completed, t.goodput_bps) == (False, "tx", 900, False, None)


def test_continuation_lines_and_lone_cr(tmp_path):
    p = tmp_path / "x.log"
    p.write_bytes("﻿2026/11/10 17:03:03 1.8.6.0 *** Ardop P2P *** Failure to open port\rCheck port.\r\n"
                  "2026/11/10 17:04:00 1.8.6.0 *** Message ABC posted to Outbox\r\n".encode())
    assert lp.parse_winlink_log(p) == []


def test_redact():
    text = "; N0XYZ DE W1ABC (JJ00XX) ;FW: w1abc"
    assert lp.redact(text, {"W1ABC": "N0AAA", "N0XYZ": "N0BBB"}) == "; N0BBB DE N0AAA (AA00AA) ;FW: N0AAA"


def test_cli_parse(tmp_path, capsys):
    main(["parse", str(STN1_WL), "--ardop", str(STN1_ARDOP), "-o", str(tmp_path)])
    out = capsys.readouterr().out
    assert "6 sessions" in out and "10 transfers" in out
    rows = (tmp_path / "transfers.csv").read_text().splitlines()
    assert len(rows) == 11 and rows[0].startswith("session,transport")
    assert "18.6" in (tmp_path / "sessions.csv").read_text()
