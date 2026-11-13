"""Semi-automatic run executor for the Windows bench.

For each pending run in the run sheet it:
  1. sets the IONOS over USB serial and records every acknowledgement,
  2. waits for the operator to start the Winlink session,
  3. detects the session in station 1's Winlink log and stamps start and end
     from the log's own UTC timestamps,
  4. applies the abort rule and records the outcome.

The operator only clicks Start in Winlink Express. Keys while waiting:
  i = invalid (bench fault)   d = did not complete   q = quit (between runs only)

Everything that touches hardware or the clock is injected, so the logic is
testable on any machine.
"""

from __future__ import annotations

import glob
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from . import logparse as lp
from . import manifest as mf
from . import matrix as mx

RUNSHEET = "runsheet.csv"
EVENTS = "events.jsonl"

CONNECT_SLACK = timedelta(seconds=5)  # log vs. arm-time skew allowed


def latest_winlink_logs(install_dir: str | Path, n: int = 2) -> list[Path]:
    """Newest daily session logs under '<install>/<CALL>/Logs/'. Two files
    cover a session that crosses midnight UTC."""
    pattern = os.path.join(str(install_dir), "*", "Logs", "RMS Express [0-9]*.log")
    files = sorted(glob.glob(pattern), key=lambda p: Path(p).name)
    return [Path(p) for p in files[-n:]]


def winlink_session_source(install_dir: str | Path) -> Callable[[], list[lp.Session]]:
    def read() -> list[lp.Session]:
        lines: list[str] = []
        for p in latest_winlink_logs(install_dir):
            lines += lp.read_text(p)
        return lp.parse_winlink_log(lines)
    return read


@dataclass
class RunResult:
    run_id: str
    outcome: str
    session: lp.Session | None = None
    note: str = ""


@dataclass
class BenchRunner:
    campaign_dir: Path
    sessions: Callable[[], list[lp.Session]]        # station 1 Winlink log
    ionos: object | None = None                       # hfbench.ionos.Ionos or None (manual)
    automation: object | None = None                  # WinlinkAutomation or None (operator queues + starts)
    clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)
    sleep: Callable[[float], None] = lambda s: __import__("time").sleep(s)
    key: Callable[[], str | None] = lambda: None
    say: Callable[[str], None] = print
    poll_s: float = 2.0
    recover: bool = False                             # after a dnc: automation.recover(), then go on
    _used: set = field(default_factory=set)

    @property
    def events_path(self) -> Path:
        return self.campaign_dir / EVENTS

    def rows(self) -> list[dict]:
        return mx.read_runsheet(self.campaign_dir / RUNSHEET)

    def next_row(self) -> dict | None:
        events = mf.read_events(self.events_path)
        rows = self.rows()
        for r in rows:  # resume a run left running by a crash first
            if mf.run_state(events, r["run_id"]) == "running":
                return r
        for r in rows:  # then the first run with no result, or whose last result was invalid
            st = mf.run_state(events, r["run_id"])
            if st == "pending" or (st == "done" and mf.last_outcome(events, r["run_id"]) == "invalid"):
                return r
        return None

    # -- one run ---------------------------------------------------------------

    def run_one(self, row: dict) -> RunResult | None:
        rid = row["run_id"]
        ids = {r["run_id"] for r in self.rows()}
        abort = timedelta(minutes=float(row["abort_minutes"]))
        box_min = float(row.get("time_box_minutes") or 0)
        box = timedelta(minutes=box_min) if box_min > 0 else None
        expected = int(row.get("payload_messages") or 1)
        events = mf.read_events(self.events_path)
        resumed = mf.run_state(events, rid) == "running"

        self.say(f"\n=== {rid}: {row['modem']} | {row['profile']} | S:N {row['snr_db']} dB | "
                 f"{row['impairment']} | rep {row['replicate']}")
        ack_text = ""
        if self.ionos is not None and not resumed:
            acks = self.ionos.apply(row["ionos_commands"])
            ack_text = "; ".join(f"{a.command}={a.reply}" for a in acks)
            self.say(f"IONOS set: {len(acks)} commands acknowledged")
        elif self.ionos is None:
            self.say(f"Set IONOS by hand: {row['ionos_commands']}")

        mids: list[str] = []
        if self.automation is not None and not resumed:
            try:
                mids = self.automation.prepare(row)["mids"]
            except Exception as e:
                self.say(f"*** Automation could not prepare {rid}: {e}\n*** Stopping; fix and rerun.")
                return None
            if len(mids) != expected:
                self.say(f"Note: run sheet expects {expected} messages, queued {len(mids)}; using {len(mids)}.")
            expected = len(mids)

        armed = self.clock()
        started_at: datetime | None = None
        if resumed:
            start_ev = [e for e in events if e["run_id"] == rid and e["event"] == "start"][-1]
            started_at = datetime.fromisoformat(start_ev["t_utc"])
            armed = started_at
            self.say("Resuming a run that was in progress.")
        elif self.automation is not None:
            try:
                self.automation.start()
            except Exception as e:
                self.say(f"*** Could not start the session: {e}\n*** Start it by hand, or press i/d.")
            self.say(f"Session started automatically (expecting {expected} messages). Keys: i=invalid, d=did not complete.")
        else:
            self.say(f"Ready. Start the Winlink session now (expecting {expected} message(s)). "
                     f"Keys: i=invalid, d=did not complete.")

        session: lp.Session | None = None
        last_alert: datetime | None = None
        boxed_at: datetime | None = None
        while True:
            k = (self.key() or "").lower()
            now = self.clock()

            if session is None:
                for s in self.sessions():
                    sid = (s.transport, s.connected_utc)
                    if sid not in self._used and s.connected_utc >= armed - CONNECT_SLACK:
                        session = s
                        self._used.add(sid)
                        break
                if session is not None and started_at is None:
                    started_at = session.connected_utc
                    mf.start_run(self.events_path, rid, valid_ids=ids, retry=True, t=started_at,
                                 extra={"ionos_ack": ack_text, "mids": " ".join(mids),
                                        "log_connected_utc": session.connected_utc.isoformat()})
                    self.say(f"Session detected: {session.transport} with {session.peer} "
                             f"at {started_at:%H:%M:%S}Z")
            else:
                # refresh the same session (it grows as the log is written)
                for s in self.sessions():
                    if (s.transport, s.connected_utc) == (session.transport, session.connected_utc):
                        session = s

            if k in ("i", "d"):
                outcome = "invalid" if k == "i" else "dnc"
                if started_at is None:
                    mf.start_run(self.events_path, rid, valid_ids=ids, retry=True, t=armed,
                                 extra={"ionos_ack": ack_text})
                mf.end_run(self.events_path, rid, outcome, notes="operator", t=now)
                self.say(f"{rid} -> {outcome} (operator)")
                return RunResult(rid, outcome, session, "operator")

            # Time box: end the session and keep what was delivered (not a failure).
            if (box is not None and boxed_at is None and session is not None and started_at is not None
                    and not session.closed and now - started_at > box):
                boxed_at = now
                self.say(f"Time box of {box_min:g} min reached: ending the session.")
                if self.automation is not None:
                    try:
                        self.automation.abort()
                    except Exception as e:
                        self.say(f"(automatic abort failed: {e})")

            ref = started_at or armed
            if now - ref > abort and (last_alert is None or now - last_alert >= timedelta(minutes=1)):
                last_alert = now
                self.say(f"\a*** ABORT RULE: {abort} exceeded. Disconnect in Winlink, "
                         f"or press d. ***")
                if self.automation is not None:
                    try:
                        self.automation.abort()
                    except Exception as e:
                        self.say(f"(automatic abort failed: {e})")
                if session is None:  # never connected: no session to wait for
                    mf.start_run(self.events_path, rid, valid_ids=ids, retry=True, t=armed,
                                 extra={"ionos_ack": ack_text})
                    mf.end_run(self.events_path, rid, "dnc", notes="no connection within abort time", t=now)
                    self.say(f"{rid} -> dnc (no connection)")
                    return RunResult(rid, "dnc", None, "no connection")

            if session is not None and session.closed:
                end = session.disconnected_utc or session.end_of_session_utc or now
                mine = [t for t in session.transfers if not mids or t.mid in mids]
                done = [t for t in mine if t.completed]
                incomplete = [t for t in mine if not t.completed]
                over_time = end - started_at > abort
                ok = len(done) >= expected and not incomplete and not over_time
                boxed = (not ok and box is not None and boxed_at is not None and end >= boxed_at - CONNECT_SLACK
                         and not over_time)
                outcome = "completed" if ok else "timeboxed" if boxed else "dnc"
                why = ("" if ok else
                       f"{len(done)}/{expected} messages in the {box_min:g}-min time box" if boxed else
                       "over abort time" if over_time else
                       f"{len(done)}/{expected} messages")
                mf.end_run(self.events_path, rid, outcome, notes=why, t=end)
                rates = ", ".join(f"{t.direction} {t.goodput_bps:.0f} bit/s" for t in done if t.goodput_bps)
                self.say(f"{rid} -> {outcome}{' (' + why + ')' if why else ''}. {rates}")
                return RunResult(rid, outcome, session, why)

            self.sleep(self.poll_s)

    # -- campaign loop ---------------------------------------------------------

    def run(self, *, max_runs: int | None = None, wait_between: Callable[[], bool] | None = None) -> list[RunResult]:
        """Work through pending runs. wait_between() is called before each run
        after the first; returning False stops (e.g. operator pressed q)."""
        results = []
        while max_runs is None or len(results) < max_runs:
            row = self.next_row()
            if row is None:
                self.say("All runs have a result.")
                break
            if results and wait_between is not None and not wait_between():
                break
            r = self.run_one(row)
            if r is None:
                break
            results.append(r)
            if r.outcome in ("dnc", "timeboxed") and self.recover and self.automation is not None:
                if not self._recover(r.run_id):
                    break
        return results

    def _recover(self, run_id: str) -> bool:
        """Two attempts; if both fail, stop the campaign for the operator."""
        for attempt in (1, 2):
            try:
                info = self.automation.recover(run_id)
                mf.recover_event(self.events_path, run_id, True, notes=info.get("note", ""), t=self.clock())
                return True
            except Exception as e:
                mf.recover_event(self.events_path, run_id, False, notes=f"attempt {attempt}: {e}", t=self.clock())
                self.say(f"*** Recovery attempt {attempt} after {run_id} failed: {e}")
        self.say("*** Stopping: reset the bench by hand (clear Outboxes, restart Winlink, open Ardop P2P) and rerun.")
        return False


# --- Winlink Express automation (Windows desktop session) ------------------------

class AutomationError(RuntimeError):
    pass


def install_callsign(install_dir: str | Path) -> str:
    """The callsign folder of a Winlink Express install (the one holding Messages)."""
    import re
    callsign = re.compile(r"^[A-Z0-9]{1,3}[0-9][A-Z0-9]{0,4}(-\d{1,2})?$", re.I)
    # 'Global Folders' also has a Messages subfolder; a station folder has Data + Messages
    calls = [p.name for p in Path(install_dir).iterdir()
             if p.is_dir() and callsign.match(p.name) and (p / "Messages").is_dir() and (p / "Data").is_dir()]
    if len(calls) != 1:
        raise AutomationError(f"expected one callsign folder in {install_dir}, found {calls}")
    return calls[0]


@dataclass(frozen=True)
class ModemProfile:
    """How Winlink Express runs a modem: the P2P session type selected in its main
    window, and each station's TNC program (for the recovery's process checks).
    ARDOP was verified on the bench (12 Nov 2026). The others are best guesses from
    the installs and must be confirmed at each modem's bring-up (test-plan Stage 2/3);
    override them with --session-type / --tnc1 / --tnc2."""
    session_type: str
    tnc1: str        # station 1 TNC executable ({install} = station 1's Winlink folder)
    tnc2: str
    verified: bool = False


MODEM_PROFILES = {
    "ARDOP": ModemProfile("Ardop P2P", r"{install}\ARDOP_Win.exe", r"{install}\ARDOP_Win.exe", verified=True),
    "VARA HF": ModemProfile("Vara HF P2P", r"C:\VARA\VARA.exe", r"C:\VARA 2\VARA.exe"),
    "Data2G": ModemProfile("Vara HF P2P", r"C:\Program Files\Data2G\data2g-host.exe",
                           r"C:\Program Files\Data2G 2\data2g-host.exe"),
    "Mercury": ModemProfile("Vara HF P2P", r"C:\Program Files\MercuryHF\mercury.exe",
                            r"C:\Program Files\MercuryHF 2\mercury.exe"),
}


def modem_profile(name: str) -> ModemProfile:
    for k, v in MODEM_PROFILES.items():
        if k.lower() == (name or "").strip().lower():
            return v
    raise AutomationError(f"no modem profile for {name!r}; known: {', '.join(MODEM_PROFILES)}")


class WinlinkAutomation:
    """Queues each run's messages by import and starts/aborts the P2P session.

    Templates are built once per campaign (`hfbench messages build`) and only
    the Message-IDs, dates and run ID change per run."""

    def __init__(self, campaign_dir: str | Path, installs: tuple[str, str] = (r"C:\RMS Express", r"C:\RMS Express 2"),
                 caller: int = 2, say: Callable[[str], None] = print, ui_factory=None,
                 procs=None, sleep: Callable[[float], None] = lambda s: __import__("time").sleep(s),
                 profile: "ModemProfile | None" = None):
        from . import messages as mg

        self.mg = mg
        self.dir = Path(campaign_dir)
        self.installs = installs
        self.calls = {1: install_callsign(installs[0]), 2: install_callsign(installs[1])}
        self.caller = caller
        self.say = say
        self.templates = {}
        for st in (1, 2):
            p = self.dir / "messages" / f"station{st}.template.xml"
            if not p.exists():
                raise AutomationError(f"{p} missing: run `hfbench messages build` first")
            self.templates[st] = p.read_text(encoding="utf-8")
        if ui_factory is None:
            from .winlink_ui import WinlinkUI
            ui_factory = lambda call: WinlinkUI(call, log=say)
        self.ui = {st: ui_factory(self.calls[st]) for st in (1, 2)}
        self.profile = profile or MODEM_PROFILES["ARDOP"]
        if procs is None:
            from .winlink_ui import WinlinkProcesses
            tnc = {installs[0]: self.profile.tnc1.format(install=installs[0]),
                   installs[1]: self.profile.tnc2.format(install=installs[1])}
            procs = WinlinkProcesses(tnc_exes=tnc)
        self.procs = procs
        self.sleep = sleep

    def _quarantine_partials(self, run_id: str) -> int:
        n = 0
        for inst, st in zip(self.installs, (1, 2)):
            for f in Path(inst, self.calls[st], "Partials").glob("*"):
                if f.is_file():
                    q = self.dir / "quarantine" / run_id / f"station{st}"
                    q.mkdir(parents=True, exist_ok=True)
                    f.replace(q / f.name)
                    n += 1
        return n

    def prepare(self, row: dict) -> dict:
        """Queue this run's messages at both stations. Resumable: messages already
        in an Outbox from *this* run's import file are kept; anything else in an
        Outbox stops the run, so the workload is always exact."""
        import xml.etree.ElementTree as ET

        run_id = row["run_id"]
        paths = {st: self.dir / "messages" / "runs" / f"{run_id}-station{st}.xml" for st in (1, 2)}
        planned = {}
        for st in (1, 2):
            if paths[st].exists():
                planned[st] = [m.find("id").text for m in
                               ET.parse(paths[st]).getroot().findall("message_list/message")]
        todo = []
        for st in (1, 2):
            have = self.ui[st].folder_mids("Outbox")
            if have and sorted(have) == sorted(planned.get(st, [])):
                self.say(f"station {st}: this run's {len(have)} messages already queued")
            elif have:
                raise AutomationError(f"station {st} ({self.calls[st]}) Outbox has {len(have)} message(s) "
                                      f"not from this run's import; clear it so the workload is exact")
            else:
                todo.append(st)
        if todo:
            moved = self._quarantine_partials(run_id)
            if moved:
                self.say(f"Moved {moved} stale partial file(s) to quarantine/{run_id}")
        for st in todo:
            if self.mg._ph_mid(1) not in self.templates[st]:
                planned[st] = []          # one-way workload: this station sends nothing
                continue
            if st not in planned:
                xml, planned[st] = self.mg.instantiate(self.templates[st], run_id)
                paths[st].parent.mkdir(parents=True, exist_ok=True)
                paths[st].write_bytes(xml)
            self.ui[st].import_xml(str(paths[st].resolve()))
            got = self.ui[st].folder_mids("Outbox")
            if not got and planned[st]:
                # Winlink skips Message-IDs it already holds (e.g. a re-run after an
                # earlier attempt was deleted): give this attempt fresh IDs.
                xml, planned[st] = self.mg.instantiate(self.templates[st], run_id)
                paths[st].write_bytes(xml)
                self.say(f"station {st}: re-import with fresh Message-IDs (the earlier IDs were already known)")
                self.ui[st].import_xml(str(paths[st].resolve()))
                got = self.ui[st].folder_mids("Outbox")
            if sorted(got) != sorted(planned[st]):
                raise AutomationError(f"station {st} Outbox after import has {len(got)} messages, "
                                      f"expected this run's {len(planned[st])}")
        all_mids = planned[1] + planned[2]
        self.say(f"Queued {len(all_mids)} messages ({len(planned[1])} + {len(planned[2])})")
        return {"mids": all_mids}

    def start(self) -> None:
        self.ui[self.caller].start(expect_target=self.calls[3 - self.caller])

    def abort(self) -> None:
        self.ui[self.caller].abort()

    def recover(self, run_id: str) -> dict:
        """The operator's reset after a failed run, automated:
        1. abort the session if it is still connected;
        2. delete everything in both Outboxes (to Deleted Items, as by hand);
        3. close both session windows and both Winlink Express instances
           (force-stop any process of that install still running after 60 s);
        4. move partial files to quarantine/<run_id> while Winlink is closed;
        5. start both instances again and open their Ardop P2P sessions;
        6. check both Outboxes are empty.
        Raises AutomationError if the bench isn't ready afterwards."""
        self.say(f"--- Recovery after {run_id}: clearing Outboxes and restarting Winlink Express "
                 f"({self.profile.session_type})")
        caller = self.ui[self.caller]
        try:
            if caller.has_session_window() and caller.status().connected:
                caller.abort()
                for _ in range(45):
                    self.sleep(2)
                    if not caller.status().connected:
                        break
                else:
                    raise AutomationError(f"{self.calls[self.caller]} still connected 90 s after Abort")
        except AutomationError:
            raise
        except Exception as e:      # a dead session window is what a restart is for
            self.say(f"  (session status not readable: {e})")
        deleted, forced = {}, {}
        for st in (1, 2):
            deleted[st] = self.ui[st].delete_folder_messages("Outbox") if self.ui[st].has_main_window() else []
        for st in (1, 2):
            ui = self.ui[st]
            try:
                ui.close_session_window()
            except Exception as e:
                self.say(f"  ({self.calls[st]}: {e}; Winlink will be closed anyway)")
            closed = ui.close_main()
            self.sleep(3)
            if not closed or self.procs.running(self.installs[st - 1]):
                forced[st] = self.procs.kill(self.installs[st - 1])
                self.say(f"  {self.calls[st]}: force-stopped processes {forced[st]}")
                self.sleep(3)
            if self.procs.running(self.installs[st - 1]):
                raise AutomationError(f"{self.calls[st]}: Winlink/ARDOP processes still running after stop")
        moved = self._quarantine_partials(run_id)
        if moved:
            self.say(f"  moved {moved} partial file(s) to quarantine/{run_id}")
        for st in (1, 2):
            self.procs.launch(self.installs[st - 1])
            self.ui[st].wait_main()
        for st in (1, 2):
            self.ui[st].open_session(self.profile.session_type)
        for st in (1, 2):
            left = self.ui[st].folder_mids("Outbox")
            if left:
                raise AutomationError(f"{self.calls[st]}: Outbox has {len(left)} message(s) after recovery")
        n = {st: len(v) for st, v in deleted.items()}
        note = (f"deleted {n[1]} + {n[2]} Outbox messages, {moved} partial(s) quarantined"
                + (f", force-stopped {sorted(forced)}" if forced else ""))
        self.say(f"--- Recovery done: {note}")
        return {"deleted": deleted, "forced": forced, "partials": moved, "note": note}

