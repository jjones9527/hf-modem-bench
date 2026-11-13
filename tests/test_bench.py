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


class FakeAutomation:
    def __init__(self, mids):
        self.mids, self.calls = mids, []

    def prepare(self, row):
        self.calls.append(("prepare", row["run_id"]))
        return {"mids": list(self.mids)}

    def start(self):
        self.calls.append(("start",))

    def abort(self):
        self.calls.append(("abort",))


SESSION6_MIDS = ["E9RH8Y3I15P8", "VFWD5OS02JX5", "WCR5C7KDEGEL", "8NM9TJ8L9L68",
                 "S8PRSB66GTK1", "QTOVU1YQY0UP", "F0O215LY9V02", "V8VCK0HNF0XO"]


def test_runner_with_automation_counts_only_run_mids(tmp_path):
    d, rows = _campaign(tmp_path, abort_minutes=60, payload_messages=10)
    rp = Replay(FX / "winlink_ardop_p2p_20261110.log", T(17, 49))
    fa = FakeAutomation(SESSION6_MIDS)
    r = BenchRunner(d, rp.sessions, automation=fa, clock=rp.clock, sleep=rp.sleep,
                    say=rp.said.append, poll_s=10).run_one(rows[0])
    assert fa.calls[:2] == [("prepare", rows[0]["run_id"]), ("start",)]
    assert r.outcome == "completed"          # expected = 8 queued MIDs, not the sheet's 10
    man = mf.build_manifest(mx.read_runsheet(d / "runsheet.csv"), mf.read_events(d / "events.jsonl"))
    assert man[0]["mids"].split() == SESSION6_MIDS


def test_runner_missing_mid_is_dnc(tmp_path):
    d, rows = _campaign(tmp_path, abort_minutes=60)
    rp = Replay(FX / "winlink_ardop_p2p_20261110.log", T(17, 49))
    fa = FakeAutomation(SESSION6_MIDS + ["NEVERSENT001"])
    r = BenchRunner(d, rp.sessions, automation=fa, clock=rp.clock, sleep=rp.sleep,
                    say=rp.said.append, poll_s=10).run_one(rows[0])
    assert (r.outcome, r.note) == ("dnc", "8/9 messages")


def test_runner_auto_aborts_over_time(tmp_path):
    d, rows = _campaign(tmp_path, abort_minutes=30)
    rp = Replay(FX / "winlink_ardop_p2p_20261110.log", T(17, 49))
    fa = FakeAutomation(SESSION6_MIDS)
    r = BenchRunner(d, rp.sessions, automation=fa, clock=rp.clock, sleep=rp.sleep,
                    say=rp.said.append, poll_s=10).run_one(rows[0])
    assert ("abort",) in fa.calls and r.outcome == "dnc"


def test_runner_stops_when_prepare_fails(tmp_path):
    d, rows = _campaign(tmp_path)

    class Bad(FakeAutomation):
        def prepare(self, row):
            raise RuntimeError("station 1 Outbox has 1 message(s)")
    rp = Replay(FX / "winlink_ardop_p2p_20261110.log", T(17, 49))
    r = BenchRunner(d, rp.sessions, automation=Bad([]), clock=rp.clock, sleep=rp.sleep,
                    say=rp.said.append, poll_s=10).run_one(rows[0])
    assert r is None and any("Outbox has 1" in s for s in rp.said)
    assert mf.read_events(d / "events.jsonl") == []      # nothing recorded


class FakeUI:
    def __init__(self, call):
        self.call, self.outbox, self.imported = call, [], []

    def folder_counts(self):
        return {"Outbox": len(self.outbox)}

    def folder_mids(self, name):
        return list(self.outbox)

    def import_xml(self, path):
        import xml.etree.ElementTree as ET
        ids = [m.find("id").text for m in ET.parse(path).getroot().findall("message_list/message")]
        self.imported.append(path)
        self.outbox += ids
        return f"Number of messages imported = {len(ids)}"

    def start(self, expect_target):
        self.started = expect_target


def test_winlink_automation_prepare_and_partials(tmp_path):
    from hfbench import messages as mg
    from hfbench.bench import WinlinkAutomation
    inst1, inst2 = tmp_path / "RMS Express", tmp_path / "RMS Express 2"
    for inst, call in ((inst1, "VA3ZTF"), (inst2, "VE3XZQ")):
        (inst / call / "Messages").mkdir(parents=True)
        (inst / call / "Data").mkdir()
        (inst / call / "Partials").mkdir()
        (inst / "Global Folders" / "Messages").mkdir(parents=True)   # real installs have this too
    (inst1 / "VA3ZTF" / "Partials" / "OLD.bin").write_bytes(b"x")
    camp = tmp_path / "camp"
    mg.build_campaign_templates(Path(__file__).resolve().parents[1] / "payloads" / "Text_50KB",
                                ("VA3ZTF", "VE3XZQ"), camp / "messages")
    uis = {}
    wa = WinlinkAutomation(camp, installs=(str(inst1), str(inst2)), say=lambda s: None,
                           ui_factory=lambda call: uis.setdefault(call, FakeUI(call)))
    info = wa.prepare({"run_id": "c-0001"})
    assert len(info["mids"]) == 10 and len(set(info["mids"])) == 10
    assert len(uis["VA3ZTF"].outbox) == 5 and len(uis["VE3XZQ"].outbox) == 5
    assert (camp / "quarantine" / "c-0001" / "station1" / "OLD.bin").exists()
    # resumable: re-preparing the same run keeps the queued messages, imports nothing
    again = wa.prepare({"run_id": "c-0001"})
    assert again["mids"] == info["mids"] and len(uis["VA3ZTF"].imported) == 1
    # partial failure: station 2's queue lost -> only station 2 is re-imported with the same MIDs
    uis["VE3XZQ"].outbox = []
    again = wa.prepare({"run_id": "c-0001"})
    assert again["mids"] == info["mids"] and len(uis["VE3XZQ"].imported) == 2 and len(uis["VA3ZTF"].imported) == 1
    wa.start()
    assert uis["VE3XZQ"].started == "VA3ZTF"           # station 2 calls station 1
    with pytest.raises(Exception, match="not from this run"):
        wa.prepare({"run_id": "c-0002"})                # previous run's messages still queued


def test_winlink_automation_one_way_workload(tmp_path):
    from hfbench import messages as mg
    from hfbench.bench import WinlinkAutomation
    inst1, inst2 = tmp_path / "RMS Express", tmp_path / "RMS Express 2"
    for inst, call in ((inst1, "VA3ZTF"), (inst2, "VE3XZQ")):
        (inst / call / "Messages").mkdir(parents=True)
        (inst / call / "Data").mkdir()
        (inst / call / "Partials").mkdir()
    camp = tmp_path / "camp"
    mg.build_campaign_templates(Path(__file__).resolve().parents[1] / "payloads" / "Text_50KB",
                                ("VA3ZTF", "VE3XZQ"), camp / "messages", counts=(10, 0))
    uis = {}
    wa = WinlinkAutomation(camp, installs=(str(inst1), str(inst2)), say=lambda s: None,
                           ui_factory=lambda call: uis.setdefault(call, FakeUI(call)))
    info = wa.prepare({"run_id": "c-0001"})
    assert len(info["mids"]) == 10
    assert len(uis["VA3ZTF"].outbox) == 10
    assert uis["VE3XZQ"].outbox == [] and uis["VE3XZQ"].imported == []   # nothing imported
    again = wa.prepare({"run_id": "c-0001"})                               # resumable
    assert again["mids"] == info["mids"]
    uis["VE3XZQ"].outbox = ["STRAY"]
    with pytest.raises(Exception, match="not from this run"):
        wa.prepare({"run_id": "c-0001"})   # the silent station's Outbox must be empty too


class RecUI(FakeUI):
    """FakeUI that also models the windows the recovery touches."""
    def __init__(self, call, log):
        super().__init__(call)
        self.log, self.main_open, self.session_open, self.connected = log, True, True, False

    def has_main_window(self):
        return self.main_open

    def has_session_window(self):
        return self.session_open

    def status(self):
        from hfbench.winlink_ui import SessionStatus
        return SessionStatus(self.connected, "", "", not self.connected, self.connected, "")

    def abort(self):
        self.log.append((self.call, "abort")); self.connected = False

    def delete_folder_messages(self, name):
        gone, self.outbox = list(self.outbox), []
        self.log.append((self.call, "delete", len(gone)))
        return gone

    def close_session_window(self):
        self.session_open = False; self.log.append((self.call, "close-session"))

    def close_main(self):
        assert not self.session_open
        self.main_open = False; self.log.append((self.call, "close"))
        return True

    def wait_main(self):
        assert self.main_open

    def open_session(self, session_type="Ardop P2P"):
        assert self.main_open
        self.session_type = session_type
        self.session_open = True; self.log.append((self.call, "open-session"))


class FakeProcs:
    def __init__(self, uis, log, stuck=()):
        self.uis, self.log, self.stuck = uis, log, set(stuck)

    def _ui(self, install):
        return self.uis["VA3ZTF" if install.endswith("RMS Express") else "VE3XZQ"]

    def running(self, install):
        return self._ui(install).main_open or install in self.stuck

    def kill(self, install):
        self.stuck.discard(install); self._ui(install).main_open = False
        self.log.append((install, "kill")); return [1234]

    def launch(self, install):
        self._ui(install).main_open = True; self.log.append((install, "launch"))


def _recovery_bench(tmp_path, stuck=()):
    from hfbench import messages as mg
    from hfbench.bench import WinlinkAutomation
    inst1, inst2 = tmp_path / "RMS Express", tmp_path / "RMS Express 2"
    for inst, call in ((inst1, "VA3ZTF"), (inst2, "VE3XZQ")):
        for sub in ("Messages", "Data", "Partials"):
            (inst / call / sub).mkdir(parents=True)
    (inst2 / "VE3XZQ" / "Partials" / "S176LKCKL8SF.bin").write_bytes(b"x")
    camp = tmp_path / "camp"
    mg.build_campaign_templates(Path(__file__).resolve().parents[1] / "payloads" / "Text_50KB",
                                ("VA3ZTF", "VE3XZQ"), camp / "messages", counts=(10, 0))
    log, uis = [], {}
    procs = FakeProcs(uis, log, stuck={str(inst2)} if "2" in stuck else set())
    wa = WinlinkAutomation(camp, installs=(str(inst1), str(inst2)), say=lambda s: None,
                           ui_factory=lambda call: uis.setdefault(call, RecUI(call, log)),
                           procs=procs, sleep=lambda s: None)
    return wa, uis, log, camp


def test_recover_follows_the_operator_procedure(tmp_path):
    wa, uis, log, camp = _recovery_bench(tmp_path)
    wa.prepare({"run_id": "c-0001"})
    uis["VA3ZTF"].outbox = uis["VA3ZTF"].outbox[1:]        # one message got through
    uis["VE3XZQ"].connected = True                           # caller still connected
    info = wa.recover("c-0001")
    assert len(info["deleted"][1]) == 9 and info["deleted"][2] == [] and not info["forced"]
    order = [e[1] for e in log]
    assert order.index("abort") < order.index("delete") < order.index("close-session") < order.index("close")
    assert order.index("close") < order.index("launch") < order.index("open-session")
    assert (camp / "quarantine" / "c-0001" / "station2" / "S176LKCKL8SF.bin").exists()   # moved while closed
    assert all(u.session_open and u.main_open and u.outbox == [] for u in uis.values())
    wa.prepare({"run_id": "c-0002"})                         # the next run can be queued


def test_recover_force_stops_a_stuck_instance(tmp_path):
    wa, uis, log, _ = _recovery_bench(tmp_path, stuck="2")
    info = wa.recover("c-0001")
    assert list(info["forced"]) == [2] and any(e[1] == "kill" for e in log)


def test_runner_recovers_after_dnc_and_records_it(tmp_path):
    d, rows = _campaign(tmp_path, abort_minutes=60)
    rp = Replay(FX / "winlink_ardop_p2p_20261110.log", T(17, 49))

    class Rec(FakeAutomation):
        def recover(self, run_id):
            self.calls.append(("recover", run_id)); return {"note": "deleted 9 + 0 Outbox messages"}
    fa = Rec(SESSION6_MIDS + ["NEVERSENT001"])                # -> dnc
    BenchRunner(d, rp.sessions, automation=fa, clock=rp.clock, sleep=rp.sleep, say=rp.said.append,
                poll_s=10, recover=True).run(max_runs=1)
    assert ("recover", rows[0]["run_id"]) in fa.calls
    man = mf.build_manifest(mx.read_runsheet(d / "runsheet.csv"), mf.read_events(d / "events.jsonl"))
    assert man[0]["outcome"] == "dnc" and "recovery ok" in man[0]["notes"] and "8/9 messages" in man[0]["notes"]


def test_runner_stops_after_two_failed_recoveries(tmp_path):
    d, rows = _campaign(tmp_path, abort_minutes=60)
    rp = Replay(FX / "winlink_ardop_p2p_20261110.log", T(17, 49))

    class Bad(FakeAutomation):
        def recover(self, run_id):
            self.calls.append(("recover", run_id)); raise RuntimeError("Outbox still has 9")
    fa = Bad(SESSION6_MIDS + ["NEVERSENT001"])
    res = BenchRunner(d, rp.sessions, automation=fa, clock=rp.clock, sleep=rp.sleep, say=rp.said.append,
                      poll_s=10, recover=True).run()
    assert len(res) == 1 and [c for c in fa.calls if c[0] == "recover"] == [("recover", rows[0]["run_id"])] * 2
    assert any("Stopping" in s for s in rp.said)
    man = mf.build_manifest(mx.read_runsheet(d / "runsheet.csv"), mf.read_events(d / "events.jsonl"))
    assert man[0]["notes"].count("recovery FAILED") == 2


def test_winlink_ui_script_entry_point_exists():
    import hfbench.winlink_ui as w
    import inspect
    src = inspect.getsource(w._main)
    for action in ("status", "delete-outbox", "close-session", "close", "open-session", "launch"):
        assert f'"{action}"' in src


def test_time_box_ends_session_and_is_not_a_failure(tmp_path):
    d, rows = _campaign(tmp_path, abort_minutes=90, time_box_minutes=20)
    rp = Replay(FX / "winlink_ardop_p2p_20261110.log", T(17, 49))
    fa = FakeAutomation(SESSION6_MIDS + ["NEVERSENT001"])          # 9 queued, 8 get through
    r = BenchRunner(d, rp.sessions, automation=fa, clock=rp.clock, sleep=rp.sleep,
                    say=rp.said.append, poll_s=10).run_one(rows[0])
    assert ("abort",) in fa.calls                                    # box reached -> session ended
    assert r.outcome == "timeboxed" and r.note == "8/9 messages in the 20-min time box"
    assert any("Time box of 20 min" in s for s in rp.said)


def test_no_time_box_same_run_is_dnc(tmp_path):
    d, rows = _campaign(tmp_path, abort_minutes=90, time_box_minutes=0)
    rp = Replay(FX / "winlink_ardop_p2p_20261110.log", T(17, 49))
    fa = FakeAutomation(SESSION6_MIDS + ["NEVERSENT001"])
    r = BenchRunner(d, rp.sessions, automation=fa, clock=rp.clock, sleep=rp.sleep,
                    say=rp.said.append, poll_s=10).run_one(rows[0])
    assert r.outcome == "dnc" and ("abort",) not in fa.calls


def test_time_box_must_be_shorter_than_abort():
    import dataclasses
    m = mx.load_matrix(EXAMPLE)
    with pytest.raises(mx.MatrixError, match="time_box"):
        mx.validate(dataclasses.replace(m, time_box_minutes=m.abort_minutes))


def test_modem_profiles_and_tnc_paths():
    from hfbench.bench import modem_profile, MODEM_PROFILES
    from hfbench.winlink_ui import WinlinkProcesses
    assert modem_profile("ardop").session_type == "Ardop P2P" and modem_profile("ARDOP").verified
    assert not modem_profile("VARA HF").verified
    with pytest.raises(Exception, match="no modem profile"):
        modem_profile("PACTOR")
    seen = []
    wp = WinlinkProcesses(run=lambda args: (seen.append(args[-1]), "")[1],
                          tnc_exes={r"C:\RMS Express": r"C:\VARA\VARA.exe"})
    assert wp.paths(r"C:\RMS Express")[1] == r"C:\VARA\VARA.exe"
    assert not wp.running(r"C:\RMS Express")
    assert any("VARA.exe" in q for q in seen)


def test_recovery_opens_the_profiles_session_type(tmp_path):
    from hfbench.bench import MODEM_PROFILES
    wa, uis, log, camp = _recovery_bench(tmp_path)
    wa.profile = MODEM_PROFILES["VARA HF"]
    wa.recover("c-0001")
    assert all(u.session_type == "Vara HF P2P" for u in uis.values())
