import csv
from pathlib import Path

from hfbench import logparse as lp
from hfbench import results as rs

FX = Path(__file__).parent / "fixtures" / "oneway28r"


def _load():
    rows = list(csv.DictReader(open(FX / "manifest.csv", encoding="utf-8")))
    logs = {st: lp.parse_winlink_log(FX / f"station{st}-winlink.log") for st in (1, 2)}
    return rs.campaign_results(rows, logs)


def test_oneway28r_per_message_results_from_both_logs():
    res = _load()
    by = {r.run_id: r for r in res}
    assert [by[k].delivered for k in sorted(by)] == [4, 10, 0, 10]
    assert [by[k].corrupted for k in sorted(by)] == [1, 0, 1, 0]
    assert by["oneway28r-0001"].not_reached == 5 and by["oneway28r-0003"].not_reached == 9
    assert sum(r.attempted for r in res) == 26 and sum(r.delivered for r in res) == 24
    bad = [m for r in res for m in r.messages if m.status == "corrupted"]
    assert {m.mid for m in bad} == {"TL9R5WJVJWYT", "697OUUYZHTAB"}
    assert all("Checksum error" in m.error for m in bad)
    # station 2 sends, station 1 receives; goodput from the receiver's log
    d = [m for r in res for m in r.messages if m.status == "delivered"]
    assert all((m.sender, m.receiver) == (2, 1) for m in d)
    assert all(1500 <= m.goodput_bps <= 1570 for m in d)


def test_net_throughput_counts_failed_sessions():
    res = _load()
    secs = sum(r.session_s for r in res)
    byt = sum(r.delivered_bytes for r in res)
    assert 110 * 60 <= secs <= 120 * 60                  # about 116 min of sessions
    assert 1100 <= byt * 8 / secs <= 1200                 # about 1,160 bit/s net
    assert res[2].net_bps == 0                            # 0003 delivered nothing


def test_summary_and_csvs(tmp_path):
    res = _load()
    mp, rp = rs.write_csvs(res, tmp_path)
    assert len(list(csv.DictReader(open(mp)))) == 40 and len(list(csv.DictReader(open(rp)))) == 4
    assert "24/26 delivered" in rs.format_summary(res)


def test_verify_attachments(tmp_path):
    import base64
    res = _load()
    payload = Path(__file__).resolve().parents[1] / "payloads" / "Text_50KB"
    msgs = tmp_path / "Messages"
    msgs.mkdir()
    delivered = [m for r in res for m in r.messages if m.status == "delivered"]
    name = "File-bOgW3.txt"
    good = (payload / name).read_bytes()

    def mime(data):
        b64 = base64.encodebytes(data).decode()
        return (f'MIME-Version: 1.0\nContent-Type: multipart/mixed; boundary="b"\n\n--b\n'
                f'Content-Disposition: attachment; filename="{name}"\nContent-Transfer-Encoding: base64\n\n'
                f'{b64}--b--\n').encode()
    (msgs / f"{delivered[0].mid}.mime").write_bytes(mime(good))
    bad = bytearray(good); bad[100] ^= 1
    (msgs / f"{delivered[1].mid}.mime").write_bytes(mime(bytes(bad)))
    rs.verify_attachments(res, {1: msgs}, payload)
    assert delivered[0].integrity == "ok"
    assert delivered[1].integrity == "MISMATCH"
    assert delivered[2].integrity == "missing"
    assert "NOT identical" in rs.format_summary(res)


def test_report_points_and_charts(tmp_path):
    import shutil
    pytest = __import__("pytest")
    pytest.importorskip("matplotlib")
    from hfbench import report as rp
    camp = tmp_path / "oneway28r"
    camp.mkdir()
    shutil.copy(FX / "manifest.csv", camp / "runsheet.csv")      # manifest rows carry the run-sheet fields
    rs.write_csvs(_load(), camp)
    with open(camp / "snr.csv", "w") as f:
        # 0004 was only partly recorded (5 bursts): it must not move the point's S:N
        f.write("run_id,data_snr_db,data_n\n" + "".join(f"oneway28r-000{i},18.3,400\n" for i in range(1, 4))
                + "oneway28r-0004,25.0,5\n")
    pts = rp.build_points([camp])
    assert len(pts) == 1
    p = pts[0]
    assert (p.modem, p.payload, p.setting_db, p.runs) == ("ARDOP 1.0.2.9", "Text_50KB", 28.0, 4)
    assert (p.delivered, p.attempted) == (24, 26) and p.snr_db == 18.3 and p.snr_runs == 3
    assert 1500 < p.goodput_median < 1570 and 1100 < p.net_bps < 1200
    assert p.rate_median and p.connect_s is not None and p.papr_db is None and p.snr_peak_db is None
    files = rp.plot(pts, tmp_path / "out", ceiling_db=19)
    names = {f.name for f in files}
    assert names >= {"net-wgn.svg", "rate-wgn.png", "success-wgn.png", "connect-wgn.png"}
    assert not any(n.startswith("peak-") for n in names)        # no PAPR: no equal-peak charts
    with open(camp / "crest.csv", "w") as f:
        f.write("run_id,st2_papr_0.01pct_db\n" + "".join(f"oneway28r-000{i},9.0\n" for i in range(1, 5)))
    p = rp.build_points([camp])[0]
    assert p.papr_db == 9.0 and p.snr_peak_db == 18.3 - 6.0
    assert "peak-net-wgn.png" in {f.name for f in rp.plot([p], tmp_path / "out2")}
    assert rp.write_table(pts, tmp_path / "out" / "points.csv").exists()


def test_modem_colors_are_fixed_slots():
    from hfbench import report as rp
    assert rp.modem_color("ARDOP 1.0.2.9") == "#2a78d6" and rp.modem_color("VARA HF 4.09") == "#eb6834"
    __import__("pytest").raises(ValueError, rp.modem_color, "Pactor 4")


def test_framing_error_is_corruption_not_stall():
    """sweep-ardop-50k-0009: Winlink's B2F block parser rejected the stream
    ('Received data stream not correct format'). That is bad data caught by
    Winlink, so it counts as corrupted, not as a stall."""
    fx = Path(__file__).parent / "fixtures" / "sweep0009"
    rows = list(csv.DictReader(open(fx / "manifest.csv", encoding="utf-8")))
    logs = {st: lp.parse_winlink_log(fx / f"station{st}-winlink.log") for st in (1, 2)}
    (r,) = rs.campaign_results(rows, logs)
    assert (r.delivered, r.corrupted, r.stall) == (2, 1, 0)
    (bad,) = [m for m in r.messages if m.status == "corrupted"]
    assert bad.mid == "ERZXWBFBHD5G" and "not correct format" in bad.error


# Data2G (17 Nov 2026, receiver's log, VARA-type tag): two messages accepted with one
# "FS YY" and carried in the same bursts, so the second ends 3 s after the first.
D2G_RX = """\
2026/11/17 05:17:00 1.8.6.0 Vara HF P2P *** Peer-to-Peer Vara Connection from VE3XZQ @ 2026/11/17 05:17:00  USB Dial: 7098.500
2026/11/17 05:17:04 1.8.6.0 Vara HF P2P FC EM AAAAAAAAAAAA 5337 4500 0
2026/11/17 05:17:04 1.8.6.0 Vara HF P2P FC EM BBBBBBBBBBBB 5337 4500 0
2026/11/17 05:17:04 1.8.6.0 Vara HF P2P F> 5A
2026/11/17 05:17:06 1.8.6.0 Vara HF P2P    FS YY
2026/11/17 05:17:18 1.8.6.0 Vara HF P2P *** Receiving AAAAAAAAAAAA
2026/11/17 05:17:21 1.8.6.0 Vara HF P2P *** AAAAAAAAAAAA - 5337/4500 bytes received
2026/11/17 05:17:21 1.8.6.0 Vara HF P2P *** Receiving BBBBBBBBBBBB
2026/11/17 05:17:24 1.8.6.0 Vara HF P2P *** BBBBBBBBBBBB - 5337/4500 bytes received
""".splitlines()
D2G_TX = """\
2026/11/17 05:16:55 1.8.6.0 Vara HF P2P *** Calling VA3ZTF
2026/11/17 05:17:00 1.8.6.0 Vara HF P2P *** Peer-to-Peer Vara Connection to VA3ZTF @ 2026/11/17 05:17:00  USB Dial: 7098.500
2026/11/17 05:17:04 1.8.6.0 Vara HF P2P    FC EM AAAAAAAAAAAA 5337 4500 0
2026/11/17 05:17:04 1.8.6.0 Vara HF P2P    FC EM BBBBBBBBBBBB 5337 4500 0
2026/11/17 05:17:06 1.8.6.0 Vara HF P2P FS YY
2026/11/17 05:17:06 1.8.6.0 Vara HF P2P *** Sending AAAAAAAAAAAA.
2026/11/17 05:17:06 1.8.6.0 Vara HF P2P *** Sending BBBBBBBBBBBB.
""".splitlines()


def test_batch_rate_from_fs_and_time_to_connect():
    rx, tx = lp.parse_winlink_log(D2G_RX), lp.parse_winlink_log(D2G_TX)
    a = rx[0].transfer("AAAAAAAAAAAA", "rx")
    assert a.accepted_utc is not None and a.accepted_utc.second == 6      # receiver's own FS line
    assert tx[0].transfer("AAAAAAAAAAAA", "tx").accepted_utc.second == 6  # the peer's FS, sender side
    assert tx[0].calling_utc is not None and rx[0].calling_utc is None
    row = {"run_id": "t-0001", "start_utc": "2026-11-17T05:16:50+00:00", "end_utc": "2026-11-17T05:18:00+00:00",
           "mids": "AAAAAAAAAAAA BBBBBBBBBBBB", "outcome": "completed"}
    r = rs.run_results(row, {1: rx, 2: tx})
    # both messages carry their batch's rate: 9,000 bytes from FS (05:17:06) to the last end (05:17:24)
    assert [m.rate_bps for m in r.messages] == [9000 * 8 / 18] * 2
    assert r.rate_median_bps == 9000 * 8 / 18 and r.connect_s == 5
    # the older receiver window gives 12,000 bit/s for B (3 s) and leaves out A's first burst
    assert r.messages[1].goodput_bps == 4500 * 8 / 3 or r.messages[1].goodput_bps is None
