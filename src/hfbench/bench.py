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
    clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)
    sleep: Callable[[float], None] = lambda s: __import__("time").sleep(s)
    key: Callable[[], str | None] = lambda: None
    say: Callable[[str], None] = print
    poll_s: float = 2.0
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

        armed = self.clock()
        started_at: datetime | None = None
        if resumed:
            start_ev = [e for e in events if e["run_id"] == rid and e["event"] == "start"][-1]
            started_at = datetime.fromisoformat(start_ev["t_utc"])
            armed = started_at
            self.say("Resuming a run that was in progress.")
        else:
            self.say(f"Ready. Start the Winlink session now (expecting {expected} message(s)). "
                     f"Keys: i=invalid, d=did not complete.")

        session: lp.Session | None = None
        last_alert: datetime | None = None
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
                                 extra={"ionos_ack": ack_text,
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

            ref = started_at or armed
            if now - ref > abort and (last_alert is None or now - last_alert >= timedelta(minutes=1)):
                last_alert = now
                self.say(f"\a*** ABORT RULE: {abort} exceeded. Disconnect in Winlink, "
                         f"or press d. ***")
                if session is None:  # never connected: no session to wait for
                    mf.start_run(self.events_path, rid, valid_ids=ids, retry=True, t=armed,
                                 extra={"ionos_ack": ack_text})
                    mf.end_run(self.events_path, rid, "dnc", notes="no connection within abort time", t=now)
                    self.say(f"{rid} -> dnc (no connection)")
                    return RunResult(rid, "dnc", None, "no connection")

            if session is not None and session.closed:
                end = session.disconnected_utc or session.end_of_session_utc or now
                done = [t for t in session.transfers if t.completed]
                incomplete = [t for t in session.transfers if not t.completed]
                over_time = end - started_at > abort
                ok = len(done) >= expected and not incomplete and not over_time
                outcome = "completed" if ok else "dnc"
                why = ("" if ok else
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
        return results
