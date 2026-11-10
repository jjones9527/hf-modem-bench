"""Run timing events and the run manifest.

Bench timing is recorded as an append-only JSON Lines event log
(``events.jsonl`` in the campaign directory) so that a crash or a typo never
rewrites history. The manifest is *derived*: run sheet + events -> one row per
attempt, which the log parser later joins to Winlink sessions by time.

Outcomes:
  completed  transfer finished within the abort rule
  dnc        did not complete (abort rule hit) -- a result, not missing data
  invalid    bench fault (wrong level, wrong modem, operator error); excluded
             from results and the run should be repeated
"""

from __future__ import annotations

import csv
import json
import socket
from datetime import datetime, timezone
from pathlib import Path

OUTCOMES = ("completed", "dnc", "invalid")

MANIFEST_EXTRA_FIELDS = [
    "attempt",
    "start_utc",
    "end_utc",
    "start_local",
    "end_local",
    "duration_s",
    "outcome",
    "final_attempt",
    "stamp_host",
    "marks",
    "notes",
]


class ManifestError(ValueError):
    pass


def now() -> datetime:
    return datetime.now().astimezone()


def read_events(path: str | Path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    events = []
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ManifestError(f"{path}:{n}: bad JSON: {e}") from None
    return events


def _append(path: Path, event: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, sort_keys=True) + "\n")
        f.flush()


def _stamp(t: datetime) -> dict:
    t = t.astimezone()
    return {
        "t_utc": t.astimezone(timezone.utc).isoformat(timespec="seconds"),
        # Local wall time with offset: Winlink logs are likely local time.
        "t_local": t.isoformat(timespec="seconds"),
        "host": socket.gethostname(),
    }


def run_state(events: list[dict], run_id: str) -> str:
    """'pending', 'running' or 'done' based on the last event for run_id."""
    last = None
    for e in events:
        if e.get("run_id") == run_id:
            last = e["event"]
    return {None: "pending", "start": "running", "mark": "running", "end": "done"}[last]


def start_run(events_path: str | Path, run_id: str, *, valid_ids: set[str],
              retry: bool = False, t: datetime | None = None) -> dict:
    events_path = Path(events_path)
    if run_id not in valid_ids:
        raise ManifestError(f"unknown run id {run_id!r} (not in run sheet)")
    events = read_events(events_path)
    running = [r for r in {e["run_id"] for e in events} if run_state(events, r) == "running"]
    if running:
        raise ManifestError(f"run {running[0]} is still running; end it first")
    state = run_state(events, run_id)
    if state == "done" and not retry:
        raise ManifestError(f"{run_id} already has a result; pass --retry to record another attempt")
    ev = {"event": "start", "run_id": run_id, **_stamp(t or now())}
    _append(events_path, ev)
    return ev


def end_run(events_path: str | Path, run_id: str | None, outcome: str, *,
            notes: str = "", t: datetime | None = None) -> dict:
    events_path = Path(events_path)
    if outcome not in OUTCOMES:
        raise ManifestError(f"outcome must be one of {OUTCOMES}")
    events = read_events(events_path)
    running = [r for r in dict.fromkeys(e["run_id"] for e in events) if run_state(events, r) == "running"]
    if run_id is None:
        if not running:
            raise ManifestError("no run is in progress")
        run_id = running[0]
    elif run_id not in running:
        raise ManifestError(f"{run_id} is not in progress")
    ev = {"event": "end", "run_id": run_id, "outcome": outcome, "notes": notes, **_stamp(t or now())}
    _append(events_path, ev)
    return ev


def mark_run(events_path: str | Path, note: str, *, t: datetime | None = None) -> dict:
    """Timestamp a mid-run event (e.g. an SNR step) on the run in progress."""
    events_path = Path(events_path)
    events = read_events(events_path)
    running = [r for r in dict.fromkeys(e["run_id"] for e in events) if run_state(events, r) == "running"]
    if not running:
        raise ManifestError("no run is in progress")
    ev = {"event": "mark", "run_id": running[0], "notes": note, **_stamp(t or now())}
    _append(events_path, ev)
    return ev


def build_manifest(runsheet: list[dict], events: list[dict]) -> list[dict]:
    """One row per attempt (start/end pair). Unstarted runs are omitted;
    a start with no end is reported with an empty outcome."""
    by_id = {r["run_id"]: r for r in runsheet}
    attempts: dict[str, list[dict]] = {}
    for e in events:
        rid = e["run_id"]
        if rid not in by_id:
            raise ManifestError(f"event for unknown run id {rid!r}")
        lst = attempts.setdefault(rid, [])
        if e["event"] == "start":
            lst.append({"start": e, "end": None, "marks": []})
        elif e["event"] == "end":
            if not lst or lst[-1]["end"] is not None:
                raise ManifestError(f"end without start for {rid}")
            lst[-1]["end"] = e
        elif e["event"] == "mark":
            if not lst or lst[-1]["end"] is not None:
                raise ManifestError(f"mark outside a running attempt for {rid}")
            lst[-1]["marks"].append(e)
        else:
            raise ManifestError(f"unknown event type {e['event']!r}")

    rows = []
    for rid in sorted(attempts, key=lambda r: int(by_id[r]["seq"])):
        lst = attempts[rid]
        for i, a in enumerate(lst, start=1):
            s, e = a["start"], a["end"]
            dur = ""
            if e:
                dur = int((datetime.fromisoformat(e["t_utc"]) - datetime.fromisoformat(s["t_utc"])).total_seconds())
            rows.append({
                **by_id[rid],
                "attempt": i,
                "start_utc": s["t_utc"],
                "end_utc": e["t_utc"] if e else "",
                "start_local": s["t_local"],
                "end_local": e["t_local"] if e else "",
                "duration_s": dur,
                "outcome": e["outcome"] if e else "",
                "final_attempt": "yes" if i == len(lst) else "no",
                "stamp_host": s["host"],
                # seconds after start, so analysis can align marks with the log
                "marks": " | ".join(
                    f"+{int((datetime.fromisoformat(k['t_utc']) - datetime.fromisoformat(s['t_utc'])).total_seconds())}s "
                    f"{k['notes']}" for k in a["marks"]),
                "notes": e.get("notes", "") if e else "",
            })
    return rows


def write_manifest(rows: list[dict], fieldnames: list[str], path: str | Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames + MANIFEST_EXTRA_FIELDS)
        w.writeheader()
        w.writerows(rows)
