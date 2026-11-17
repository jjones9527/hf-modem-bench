"""Per-message and per-run results from BOTH stations' Winlink logs.

Rules (test-plan.md, 13 Nov 2026; reporting set by the operator 17 Nov 2026):
- Headline: net throughput = compressed bytes delivered x 8 / session time (connect to
  disconnect), failed sessions included: what an operator sees. Recovery time between
  runs is not session time.
- Transfer rate (rate_bps), the second figure: per proposal batch (the messages the
  receiver accepts with one "FS" answer; Winlink proposes up to a few at once), the
  batch's compressed bytes x 8 over the time from that "FS" line to the batch's last
  "received" line; each message carries its batch's rate. Same rule for every modem.
- goodput_bps is the older receiver window ("Receiving" -> "received"). Kept for
  comparison only: it starts when the first data reaches Winlink, so it leaves out
  most of the first burst (about 17 s for Data2G's 12-s bursts), and a message carried
  in the same burst as the one before it gets a 0-s window.
- Time to connect (connect_s): from the caller's "Calling <peer>" to the connection,
  for the run's first session.
- Every message offered in a run gets a status:
    delivered  - the receiver logged it as received
    corrupted  - the receiver logged a checksum/decompress link error during it
    stall      - started but never finished, no error logged (ARQ timeout, link lost)
    cut        - in progress when the run's time box closed (not a failure)
    not_reached- never started (the session ended earlier)
- Net throughput = compressed bytes delivered x 8 / session time, failed sessions
  included. Recovery time between runs is not session time.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from . import logparse as lp

SLACK = timedelta(seconds=30)
CORRUPT_MARKERS = ("checksum error", "unable to decompress", "failed to assemble",
                   "not correct format")   # B2F block framing rejected the data


@dataclass
class MessageResult:
    run_id: str
    mid: str
    sender: int | None
    receiver: int | None
    status: str
    compressed_bytes: int | None = None
    start_utc: str = ""
    end_utc: str = ""
    seconds: int | None = None          # receiver's Winlink transfer time
    goodput_bps: float | None = None    # receiver side, older window (see module doc)
    xfer_start_utc: str = ""            # its proposal batch's FS acceptance
    xfer_seconds: float | None = None   # its batch's transfer time
    rate_bps: float | None = None       # its batch's transfer rate (module doc)
    error: str = ""
    integrity: str = ""                 # delivered only: ok / MISMATCH / missing (see verify_attachments)


@dataclass
class RunResult:
    run_id: str
    outcome: str
    attempted: int = 0                  # delivered + failed (cut and not_reached excluded)
    delivered: int = 0
    corrupted: int = 0
    stall: int = 0
    cut: int = 0
    not_reached: int = 0
    delivered_bytes: int = 0
    integrity_bad: int = 0              # delivered messages whose attachment differs from the payload
    session_s: int | None = None
    net_bps: float | None = None
    goodput_median_bps: float | None = None
    rate_median_bps: float | None = None
    connect_s: float | None = None      # time to connect, first session of the run
    sessions: int = 0
    messages: list[MessageResult] = field(default_factory=list)


def _sessions_between(sessions: list[lp.Session], start: datetime, end: datetime) -> list[lp.Session]:
    return [s for s in sessions if start - SLACK <= s.connected_utc <= end + SLACK]


def _session_seconds(s: lp.Session) -> int | None:
    end = s.disconnected_utc or s.end_of_session_utc
    return int((end - s.connected_utc).total_seconds()) if end else None


def _error_after(s: lp.Session, t: datetime | None) -> str:
    for et, ev in s.events:
        if (t is None or et >= t) and any(k in ev.lower() for k in CORRUPT_MARKERS):
            return ev
    return ""


def batch_transfers(s: lp.Session) -> dict[str, tuple[datetime, float, float]]:
    """Per received message: (start, seconds, rate) of its PROPOSAL BATCH, i.e. every
    message the receiver accepted with one "FS" answer. Start = that FS line; end = the
    batch's last "received" line; rate = the batch's compressed bytes x 8 / that time.
    A modem may carry a batch's messages in the same bursts (Data2G does), so a
    message's own end is not where the next one starts; the batch is the unit that
    means the same for every modem."""
    batches: dict[datetime, list[lp.Transfer]] = {}
    for t in s.transfers:
        if t.direction == "rx" and t.completed and t.accepted_utc and t.end_utc and t.compressed_bytes:
            batches.setdefault(t.accepted_utc, []).append(t)
    out = {}
    for start, ts in batches.items():
        secs = (max(t.end_utc for t in ts) - start).total_seconds()
        if secs <= 0:
            continue
        rate = sum(t.compressed_bytes for t in ts) * 8 / secs
        for t in ts:
            out[t.mid] = (start, secs, rate)
    return out


def run_results(row: dict, logs: dict[int, list[lp.Session]]) -> RunResult:
    """Results for one manifest row. logs = {1: station 1 sessions, 2: station 2 sessions}."""
    rid = row["run_id"]
    start = datetime.fromisoformat(row["start_utc"])
    end = datetime.fromisoformat(row["end_utc"]) if row.get("end_utc") else start + timedelta(hours=3)
    mids = (row.get("mids") or "").split()
    sess = {st: _sessions_between(logs[st], start, end) for st in (1, 2)}
    rr = RunResult(rid, row.get("outcome", ""))
    timeboxed = rr.outcome == "timeboxed"

    def find(st: int, mid: str, direction: str) -> tuple[lp.Session | None, lp.Transfer | None]:
        for s in sess[st]:
            for t in s.transfers:
                if t.mid == mid and t.direction == direction:
                    return s, t
        return None, None

    for mid in mids:
        tx = {st: find(st, mid, "tx") for st in (1, 2)}
        sender = next((st for st in (1, 2) if tx[st][1] is not None), None)
        receiver = (3 - sender) if sender else None
        rs, rt = find(receiver, mid, "rx") if receiver else (None, None)
        m = MessageResult(rid, mid, sender, receiver, "not_reached")
        if rt is not None:
            m.compressed_bytes = rt.compressed_bytes
            m.start_utc = rt.start_utc.isoformat() if rt.start_utc else ""
            m.end_utc = rt.end_utc.isoformat() if rt.end_utc else ""
        elif sender:
            m.compressed_bytes = tx[sender][1].compressed_bytes
        if rt is not None and rt.completed:
            m.status, m.seconds, m.goodput_bps = "delivered", rt.winlink_time_s, rt.goodput_bps
            b = batch_transfers(rs).get(mid)
            if b is not None:
                m.xfer_start_utc, m.xfer_seconds, m.rate_bps = b[0].isoformat(), b[1], b[2]
        elif rt is not None and rt.start_utc is not None:
            err = _error_after(rs, rt.start_utc)
            if err:
                m.status, m.error = "corrupted", err
            elif timeboxed:
                m.status = "cut"
            else:
                m.status = "stall"
        elif sender and tx[sender][1].start_utc is not None:
            # sender started but the receiver never logged "Receiving"
            m.status = "cut" if timeboxed else "stall"
        rr.messages.append(m)

    for m in rr.messages:
        setattr(rr, m.status, getattr(rr, m.status) + 1)
    rr.attempted = rr.delivered + rr.corrupted + rr.stall
    rr.delivered_bytes = sum(m.compressed_bytes or 0 for m in rr.messages if m.status == "delivered")
    secs = [x for x in (_session_seconds(s) for s in sess[1] or sess[2]) if x]
    rr.session_s = sum(secs) if secs else None
    if rr.session_s:
        rr.net_bps = rr.delivered_bytes * 8 / rr.session_s
    def med(v):
        v = sorted(v)
        return (v[len(v) // 2] if len(v) % 2 else (v[len(v) // 2 - 1] + v[len(v) // 2]) / 2) if v else None
    rr.goodput_median_bps = med(m.goodput_bps for m in rr.messages if m.goodput_bps)
    rr.rate_median_bps = med(m.rate_bps for m in rr.messages if m.rate_bps)
    caller = sess[2] if any(s.calling_utc for s in sess[2]) else sess[1]
    first = min(caller, key=lambda s: s.connected_utc, default=None)
    if first is not None and first.calling_utc is not None:
        rr.connect_s = (first.connected_utc - first.calling_utc).total_seconds()
    rr.sessions = len(sess[1] or sess[2])
    return rr


def campaign_results(manifest_rows: list[dict], logs: dict[int, list[lp.Session]]) -> list[RunResult]:
    """Only each run's final attempt counts: an earlier attempt that was later marked
    invalid (bench fault) and re-run is not a result."""
    return [run_results(r, logs) for r in manifest_rows
            if r.get("start_utc") and r.get("outcome") not in ("invalid", "")
            and r.get("final_attempt", "yes") == "yes"]


def write_csvs(results: list[RunResult], out_dir: str | Path) -> tuple[Path, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    mp, rp = out / "messages.csv", out / "runs.csv"
    with open(mp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(MessageResult.__dataclass_fields__))
        w.writeheader()
        for r in results:
            for m in r.messages:
                w.writerow(asdict(m))
    with open(rp, "w", newline="", encoding="utf-8") as f:
        fields = [k for k in RunResult.__dataclass_fields__ if k != "messages"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in results:
            w.writerow({k: getattr(r, k) for k in fields})
    return mp, rp


def format_summary(results: list[RunResult]) -> str:
    lines = [f"{'run':<18} {'outcome':<10} {'deliv':>5} {'att':>4} {'corr':>4} {'stall':>5} {'cut':>4} "
             f"{'net':>10} {'per msg med':>12} {'connect':>8}"]
    for r in results:
        lines.append(f"{r.run_id:<18} {r.outcome:<10} {r.delivered:>5} {r.attempted:>4} {r.corrupted:>4} "
                     f"{r.stall:>5} {r.cut:>4} {(r.net_bps or 0):>6.0f} b/s {(r.rate_median_bps or 0):>8.0f} b/s "
                     f"{'' if r.connect_s is None else f'{r.connect_s:.0f} s':>8}")
    att = sum(r.attempted for r in results)
    dl = sum(r.delivered for r in results)
    secs = sum(r.session_s or 0 for r in results)
    byt = sum(r.delivered_bytes for r in results)
    checked = [m for r in results for m in r.messages if m.integrity]
    if checked:
        bad = [m for m in checked if m.integrity != "ok"]
        lines.append(f"attachments checked against the payload: {len(checked) - len(bad)}/{len(checked)} identical"
                     + (f"; NOT identical: {', '.join(m.mid + ' (' + m.integrity + ')' for m in bad)}" if bad else ""))
    if att:
        lines.append(f"total: {dl}/{att} delivered ({100 * (att - dl) / att:.1f}% failed), "
                     f"net {byt * 8 / secs:.0f} bit/s over {secs / 60:.0f} min of sessions" if secs else "")
    return "\n".join(lines)


def verify_attachments(results: list[RunResult], message_dirs: dict[int, Path], payload_dir: str | Path) -> None:
    """Compare every delivered attachment with the payload file of the same name.

    message_dirs[st] is the receiving station's '<install>/<CALL>/Messages' folder,
    where Winlink keeps each message as <MID>.mime. Sets MessageResult.integrity to
    'ok', 'MISMATCH' (any byte differs, or a different/missing attachment) or
    'missing' (no .mime file)."""
    import email

    payload_dir = Path(payload_dir)
    for r in results:
        for m in r.messages:
            if m.status != "delivered" or m.receiver not in message_dirs:
                continue
            f = Path(message_dirs[m.receiver]) / f"{m.mid}.mime"
            if not f.exists():
                m.integrity = "missing"
                continue
            parts = [(p.get_filename(), p.get_payload(decode=True))
                     for p in email.message_from_bytes(f.read_bytes()).walk() if p.get_filename()]
            ok = bool(parts) and all((payload_dir / name).exists() and (payload_dir / name).read_bytes() == data
                                     for name, data in parts)
            m.integrity = "ok" if ok else "MISMATCH"
        r.integrity_bad = sum(1 for m in r.messages if m.integrity in ("MISMATCH", "missing"))
