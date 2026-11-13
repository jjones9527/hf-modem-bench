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
