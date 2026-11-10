"""Bench runner and IONOS client tests with fake hardware. The runner replays
the real (redacted) station 1 log against a simulated clock."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from hfbench import logparse as lp
from hfbench import manifest as mf
from hfbench import matrix as mx
from hfbench.bench import BenchRunner, latest_winlink_logs
from hfbench.ionos import Ionos, IonosError, split_commands

FX = Path(__file__).parent / "fixtures"
EXAMPLE = Path(__file__).resolve().parents[1] / "runs" / "example-matrix.toml"


class FakeSerial:
    """Mimics IONOS fw 2.03: 'OK' for known commands, '?' otherwise."""
    KNOWN = ("WGN", "MPG", "MPM", "MPP", "MPD", "MULTIPATH", "FADE DEPTH", "FADE FREQ",
             "OFFSET", "FM DEVIATION", "FM RATE", "CH1 IN", "CH2 IN", "CH1 OUT", "CH2 OUT", "BANDWIDTH")

    def __init__(self, silent=False):
        self.sent, self.silent, self._reply = [], silent, b""

    def reset_input_buffer(self):
        self._reply = b""

    def write(self, data):
        assert data.endswith(b"\r\n")
        cmd = data[:-2].decode()
        self.sent.append(cmd)
        name = cmd.split(":")[0].strip().upper()
        self._reply = b"" if self.silent else (b"OK\r\n" if name in self.KNOWN else b"?\r\n")

    def readline(self):
        r, self._reply = self._reply, b""
        return r

    def close(self):
        pass


def test_ionos_apply_and_probe():
    ser = FakeSerial()
    io = Ionos(ser)
    acks = io.apply("BANDWIDTH:3000; MULTIPATH:2; MPP:10")
    assert [a.ok for a in acks] == [True] * 3 and ser.sent == ["BANDWIDTH:3000", "MULTIPATH:2", "MPP:10"]
    assert io.probe()
    with pytest.raises(IonosError, match="rejected 'BOGUS:1'"):
        io.apply("WGN:20; BOGUS:1; MPG:5")
    assert ser.sent[-1] == "BOGUS:1"  # stopped before MPG:5


def test_ionos_no_reply():
    with pytest.raises(IonosError, match="no reply"):
        Ionos(FakeSerial(silent=True), retries=0).send("WGN:20")


def test_split_commands():
    assert split_commands(" A:1;B:2 ;; ") == ["A:1", "B:2"]


class Replay:
    """Clock + log source that reveal the fixture log line by line as time passes."""

    def __init__(self, path, start):
        self.lines = lp.read_text(path)
        self.now = start
        self.said = []

    def clock(self):
        return self.now

    def sleep(self, s):
        self.now += timedelta(seconds=s)

    def sessions(self):
        stamp = self.now.strftime("%Y/%m/%d %H:%M:%S")
        return lp.parse_winlink_log([l for l in self.lines if l[:19] <= stamp])


def _campaign(tmp_path, **overrides):
    rows = mx.build_runs(mx.load_matrix(EXAMPLE))[:3]
    for r in rows:
        r.update(overrides)
    d = tmp_path / "camp"
    mx.write_runsheet(rows, d / "runsheet.csv")
    return d, rows


T = lambda h, m, s=0: datetime(2026, 11, 10, h, m, s, tzinfo=timezone.utc)


def test_runner_completed_from_real_log(tmp_path):
    d, rows = _campaign(tmp_path, abort_minutes=60, payload_messages=8)
    rp = Replay(FX / "winlink_ardop_p2p_20261110.log", T(17, 49))
    ser = FakeSerial()
    r = BenchRunner(d, rp.sessions, ionos=Ionos(ser), clock=rp.clock, sleep=rp.sleep,
                    say=rp.said.append, poll_s=10).run_one(rows[0])
    assert r.outcome == "completed" and len(r.session.transfers) == 8
    assert ser.sent == split_commands(rows[0]["ionos_commands"])
    man = mf.build_manifest(mx.read_runsheet(d / "runsheet.csv"), mf.read_events(d / "events.jsonl"))
    assert man[0]["start_utc"] == "2026-11-10T17:49:28+00:00"   # from the log, not the PC clock
    assert man[0]["end_utc"] == "2026-11-10T18:39:36+00:00"
    assert man[0]["outcome"] == "completed"
    assert man[0]["ionos_ack"].count("=OK") == len(ser.sent)
    assert man[0]["log_connected_utc"] == "2026-11-10T17:49:28+00:00"


def test_runner_over_abort_time_is_dnc(tmp_path):
    d, rows = _campaign(tmp_path, abort_minutes=30, payload_messages=8)
    rp = Replay(FX / "winlink_ardop_p2p_20261110.log", T(17, 49))
    r = BenchRunner(d, rp.sessions, clock=rp.clock, sleep=rp.sleep, say=rp.said.append,
                    poll_s=10).run_one(rows[0])
    assert (r.outcome, r.note) == ("dnc", "over abort time")
    assert any("ABORT RULE" in s for s in rp.said)


def test_runner_ignores_sessions_before_arming(tmp_path):
    # Armed at 17:37: the 17:31 session must not be taken; the 17:49 one is.
    d, rows = _campaign(tmp_path, abort_minutes=60, payload_messages=8)
    rp = Replay(FX / "winlink_ardop_p2p_20261110.log", T(17, 37))
    r = BenchRunner(d, rp.sessions, clock=rp.clock, sleep=rp.sleep, say=rp.said.append,
                    poll_s=10).run_one(rows[0])
    assert r.session.connected_utc == T(17, 49, 28)


def test_runner_no_connection_is_dnc(tmp_path):
    d, rows = _campaign(tmp_path, abort_minutes=5)
    rp = Replay(FX / "winlink_ardop_p2p_20261110.log", T(18, 45))  # nothing after this
    r = BenchRunner(d, rp.sessions, clock=rp.clock, sleep=rp.sleep, say=rp.said.append,
                    poll_s=30).run_one(rows[0])
    assert (r.outcome, r.note) == ("dnc", "no connection")


def test_operator_invalid_then_rerun(tmp_path):
    d, rows = _campaign(tmp_path, abort_minutes=60)
    rp = Replay(FX / "winlink_ardop_p2p_20261110.log", T(18, 45))
    keys = iter([None, None, "i"])
    runner = BenchRunner(d, rp.sessions, clock=rp.clock, sleep=rp.sleep, say=rp.said.append,
                         key=lambda: next(keys, None), poll_s=5)
    assert runner.run_one(rows[0]).outcome == "invalid"
    assert runner.next_row()["run_id"] == rows[0]["run_id"]  # invalid runs are repeated


def test_latest_winlink_logs(tmp_path):
    logs = tmp_path / "RMS Express" / "N0AAA" / "Logs"
    logs.mkdir(parents=True)
    for n in ("RMS Express 20261109.log", "RMS Express 20261110.log", "RMS Express 20261111.log",
              "RMS Express Exceptions 20261111.log", "RMS Express Autoupdate 20261111.log"):
        (logs / n).write_text("")
    assert [p.name for p in latest_winlink_logs(tmp_path / "RMS Express")] == [
        "RMS Express 20261110.log", "RMS Express 20261111.log"]
