"""Parsers for Winlink Express and ARDOP TNC logs.

Formats were derived from Winlink Express 1.8.6.0 and ARDOP_Win 1.0.2.9 logs
(Nov 2026). All timestamps in both logs are UTC with 1 s resolution.

Winlink Express session log  (C:\\RMS Express\\<CALL>\\Logs\\RMS Express YYYYMMDD.log)
    2026/11/10 17:25:14 1.8.6.0 *** Ardop P2P *** Sending IYNCRCASTUY3.
    <date> <time> <winlink version> <text>
  Session lines are tagged with the transport ("*** Ardop P2P ..."). After the
  tag, three extra spaces mark B2F protocol text sent by the local station; no
  indent means text from the peer. "*** " after the tag marks a client event.
  An entry may continue on following lines that have no timestamp.

ARDOP ARQ session stats    (C:\\RMS Express\\Logs\\ARDOP_WinTNC_ARQSession_YYYYMMDD.log)
  One block per ARQ session, written at disconnect, with S:N measured by the
  TNC in a 3 kHz noise bandwidth, frame-type quality and gear-shift counts.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field, fields, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

_LINE_SPLIT = re.compile(r"\r\n|\r|\n")
_WL_LINE = re.compile(r"^(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}) (\d+(?:\.\d+)+) ?(.*)$")
_EVENT = re.compile(r"^\*\*\* (?P<tag>[^*]+?) \*\*\* (?P<ev>.*)$", re.S)


def read_text(path: str | Path) -> list[str]:
    """Read a Windows log: UTF-8 with BOM, CRLF or lone CR line endings."""
    raw = Path(path).read_bytes().decode("utf-8-sig", errors="replace")
    return _LINE_SPLIT.split(raw)


def _ts(s: str) -> datetime:
    return datetime.strptime(s.replace("-", "/"), "%Y/%m/%d %H:%M:%S").replace(tzinfo=timezone.utc)


def _dur(s: str) -> int:
    """'04:15' or '1:02:03' -> seconds."""
    parts = [int(p) for p in s.split(":")]
    secs = 0
    for p in parts:
        secs = secs * 60 + p
    return secs


def _int(s: str) -> int:
    return int(s.replace(",", ""))


@dataclass
class Transfer:
    mid: str
    direction: str  # "tx" (local sends) or "rx" (local receives)
    uncompressed_bytes: int | None = None
    compressed_bytes: int | None = None
    start_utc: datetime | None = None
    end_utc: datetime | None = None
    wire_bytes: int | None = None  # Winlink "Bytes:" figure (compressed + B2F overhead)
    winlink_time_s: int | None = None
    winlink_bytes_per_min: int | None = None
    completed: bool = False

    @property
    def goodput_bps(self) -> float | None:
        """Compressed payload bits per second over the data phase."""
        if self.completed and self.compressed_bytes and self.winlink_time_s:
            return self.compressed_bytes * 8 / self.winlink_time_s
        return None


@dataclass
class Session:
    transport: str  # e.g. "Ardop P2P"
    peer: str
    connected_utc: datetime
    dial_khz: float | None = None
    sideband: str | None = None
    disconnected_utc: datetime | None = None
    end_of_session_utc: datetime | None = None
    messages_sent: int | None = None
    bytes_sent: int | None = None
    messages_received: int | None = None
    bytes_received: int | None = None
    session_time_s: int | None = None
    avg_bytes_per_min: int | None = None
    peak_1min_bytes_per_min: int | None = None
    winlink_version: str | None = None
    closed: bool = False  # saw the final "Session:" summary line
    transfers: list[Transfer] = field(default_factory=list)
    events: list[tuple[datetime, str]] = field(default_factory=list)

    def transfer(self, mid: str, direction: str) -> Transfer:
        for t in self.transfers:
            if t.mid == mid:
                return t
        t = Transfer(mid=mid, direction=direction)
        self.transfers.append(t)
        return t


# --- Winlink session log -----------------------------------------------------

_RX = {
    "connected": re.compile(r"^Connected to (?:Peer: )?(?P<peer>\S+)(?: @ [\d/: ]+?)?(?:\s+(?P<sb>[A-Z]+) Dial: (?P<dial>[\d.]+))?\s*$"),
    "end": re.compile(r"^--- End of session with (?P<peer>\S+) at (?P<ts>[\d/ :]+) ---"),
    "msgs_sent": re.compile(r"^Messages sent: (?P<n>\d+)\.\s+Total bytes sent: (?P<b>[\d,]+),\s+Time: (?P<t>[\d:]+),\s+bytes/minute: (?P<bpm>[\d,]+)"),
    "msgs_recv": re.compile(r"^Messages Received: (?P<n>\d+)\.\s+Total bytes received: (?P<b>[\d,]+),\s+Total session time: (?P<t>[\d:]+),\s+bytes/minute: (?P<bpm>[\d,]+)"),
    "disconnected": re.compile(r"^Disconnected from (?:Peer: )?(?P<peer>\S+) @ (?P<ts>[\d/ :]+)"),
    "summary": re.compile(r"^Session: (?P<min>[\d.]+) min;\s+Avg Throughput: (?P<avg>[\d,]+) Bytes/min;\s+1 Min Peak Throughput: (?P<peak>[\d,]+) Bytes/min"),
    "sending": re.compile(r"^Sending (?P<mid>\w+)\.?$"),
    "sent_done": re.compile(r"^Completed send of message (?P<mid>\w+)"),
    "sent_stats": re.compile(r"^Sent \d+ messages?\.\s+Bytes: (?P<b>[\d,]+),\s+Time: (?P<t>[\d:]+),\s+bytes/minute: (?P<bpm>[\d,]+)"),
    "receiving": re.compile(r"^Receiving (?P<mid>\w+)"),
    "recv_done": re.compile(r"^(?P<mid>\w+) - (?P<unc>\d+)/(?P<comp>\d+) bytes received"),
    "recv_stats": re.compile(r"^Bytes: (?P<b>[\d,]+),\s+Time: (?P<t>[\d:]+),\s+bytes/minute: (?P<bpm>[\d,]+)"),
}
_FC = re.compile(r"^FC (?P<type>\w+) (?P<mid>\w+) (?P<unc>\d+) (?P<comp>\d+)")


def parse_winlink_log(path_or_lines) -> list[Session]:
    lines = read_text(path_or_lines) if isinstance(path_or_lines, (str, Path)) else path_or_lines

    # Join continuation lines (no timestamp) onto the previous entry.
    entries: list[tuple[datetime, str, str]] = []
    for line in lines:
        m = _WL_LINE.match(line)
        if m:
            entries.append((_ts(m.group(1)), m.group(2), m.group(3)))
        elif entries and line.strip():
            t, v, text = entries[-1]
            entries[-1] = (t, v, text + "\n" + line)

    sessions: list[Session] = []
    cur: Session | None = None
    last_tx: Transfer | None = None  # awaiting "Sent n message. Bytes:" line
    last_rx: Transfer | None = None  # awaiting "Bytes:" line after receive

    for t, ver, text in entries:
        # Client event: "*** <tag> *** <event>". The tag is only unambiguous
        # here; protocol lines are matched against the current session's tag.
        m = _EVENT.match(text)
        if m:
            tag, ev = m.group("tag"), m.group("ev").strip()
            c = _RX["connected"].match(ev)
            if c:
                if cur is not None:
                    sessions.append(cur)  # previous session never closed cleanly
                cur = Session(transport=tag, peer=c.group("peer"), connected_utc=t,
                              dial_khz=float(c.group("dial")) if c.group("dial") else None,
                              sideband=c.group("sb"), winlink_version=ver)
                last_tx = last_rx = None
                continue
            if cur is None or tag != cur.transport:
                continue
            cur.events.append((t, ev))
            if mm := _RX["sending"].match(ev):
                tr = cur.transfer(mm.group("mid"), "tx")
                tr.start_utc = t
            elif mm := _RX["sent_done"].match(ev):
                last_tx = cur.transfer(mm.group("mid"), "tx")
                last_tx.end_utc, last_tx.completed = t, True
            elif (mm := _RX["sent_stats"].match(ev)) and last_tx:
                last_tx.wire_bytes = _int(mm.group("b"))
                last_tx.winlink_time_s = _dur(mm.group("t"))
                last_tx.winlink_bytes_per_min = _int(mm.group("bpm"))
                last_tx = None
            elif mm := _RX["receiving"].match(ev):
                tr = cur.transfer(mm.group("mid"), "rx")
                tr.start_utc = t
            elif mm := _RX["recv_done"].match(ev):
                last_rx = cur.transfer(mm.group("mid"), "rx")
                last_rx.end_utc, last_rx.completed = t, True
                last_rx.uncompressed_bytes = int(mm.group("unc"))
                last_rx.compressed_bytes = int(mm.group("comp"))
            elif (mm := _RX["recv_stats"].match(ev)) and last_rx:
                last_rx.wire_bytes = _int(mm.group("b"))
                last_rx.winlink_time_s = _dur(mm.group("t"))
                last_rx.winlink_bytes_per_min = _int(mm.group("bpm"))
                last_rx = None
            elif mm := _RX["end"].match(ev):
                cur.end_of_session_utc = _ts(mm.group("ts"))
            elif mm := _RX["msgs_sent"].match(ev):
                cur.messages_sent, cur.bytes_sent = int(mm.group("n")), _int(mm.group("b"))
            elif mm := _RX["msgs_recv"].match(ev):
                cur.messages_received, cur.bytes_received = int(mm.group("n")), _int(mm.group("b"))
                cur.session_time_s = _dur(mm.group("t"))
            elif mm := _RX["disconnected"].match(ev):
                cur.disconnected_utc = _ts(mm.group("ts"))
            elif mm := _RX["summary"].match(ev):
                cur.avg_bytes_per_min = _int(mm.group("avg"))
                cur.peak_1min_bytes_per_min = _int(mm.group("peak"))
                cur.closed = True
                sessions.append(cur)
                cur = None
        elif cur is not None and text.startswith(f"*** {cur.transport} "):
            # B2F protocol text; 3-space indent = sent by local station.
            rest = text[len(cur.transport) + 5:]
            local = rest.startswith("   ")
            fc = _FC.match(rest.strip())
            if fc:
                tr = cur.transfer(fc.group("mid"), "tx" if local else "rx")
                tr.uncompressed_bytes = int(fc.group("unc"))
                tr.compressed_bytes = int(fc.group("comp"))

    if cur is not None:
        sessions.append(cur)
    return sessions


# --- ARDOP ARQ session stats --------------------------------------------------

@dataclass
class ArdopSession:
    end_utc: datetime
    tnc_version: str
    peer: str
    minutes: float
    bandwidth_hz: int | None = None
    round_trip_ms: int | None = None
    avg_leader_snr_db: float | None = None  # 3 kHz noise bandwidth
    leader_detects: int | None = None
    good_frame_decodes: int | None = None
    failed_frame_decodes: int | None = None
    bytes_sent: int | None = None
    bytes_received: int | None = None
    throughput_bytes_per_min: int | None = None
    mode_shift_ups: int | None = None
    mode_shift_downs: int | None = None
    link_turnovers: int | None = None
    rx_frame_quality: dict[str, tuple[int, int]] = field(default_factory=dict)  # mod -> (avg quality, frames)


_ARDOP_HDR = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[([\d.]+)\] \*+ ARQ session stats with (\S+) \(([\d.]+) minutes\)")
_ARDOP_FIELDS = {
    "bandwidth_hz": (r"Session Bandwidth=(\d+) Hz", int),
    "round_trip_ms": (r"Measured Round Trip=(\d+) ms", int),
    "avg_leader_snr_db": (r"AvgLeader S:N\(3KHz noise BW\)=(-?[\d.]+)dB", float),
    "leader_detects": (r"LeaderDetects=(\d+)", int),
    "good_frame_decodes": (r"Good Frame Type Decodes=(\d+)", int),
    "failed_frame_decodes": (r"Failed Frame Type Decodes =?(\d+)", int),
    "bytes_sent": (r"Total Bytes Sent=(\d+)", int),
    "bytes_received": (r"Total Bytes Received=(\d+)", int),
    "throughput_bytes_per_min": (r"Session Throughput=(\d+) bytes/min", int),
    "mode_shift_ups": (r"Mode Shift UPs=(\d+)", int),
    "mode_shift_downs": (r"Mode Shift DOWNs=(\d+)", int),
    "link_turnovers": (r"Link Turnovers=(\d+)", int),
}
_ARDOP_QUAL = re.compile(r"Avg (\S+)\s+Quality=(\d+)\s+on (\d+) frames")


def parse_ardop_sessions(path_or_lines) -> list[ArdopSession]:
    lines = read_text(path_or_lines) if isinstance(path_or_lines, (str, Path)) else path_or_lines
    out: list[ArdopSession] = []
    cur: ArdopSession | None = None
    for line in lines:
        h = _ARDOP_HDR.match(line.strip())
        if h:
            cur = ArdopSession(end_utc=_ts(h.group(1)), tnc_version=h.group(2),
                               peer=h.group(3), minutes=float(h.group(4)))
            out.append(cur)
            continue
        if cur is None:
            continue
        if line.strip().startswith(tuple("0123456789")) and "*****" in line:
            cur = None  # closing rule line
            continue
        for name, (rx, conv) in _ARDOP_FIELDS.items():
            m = re.search(rx, line)
            if m:
                setattr(cur, name, conv(m.group(1)))
        q = _ARDOP_QUAL.search(line)
        if q:
            cur.rx_frame_quality[q.group(1)] = (int(q.group(2)), int(q.group(3)))
    return out


def match_ardop(sessions: list[Session], ardop: list[ArdopSession], slack_s: int = 30) -> dict[int, ArdopSession]:
    """Pair Winlink sessions with ARDOP stats blocks by disconnect time and peer."""
    pairs: dict[int, ArdopSession] = {}
    used: set[int] = set()
    for i, s in enumerate(sessions):
        end = s.disconnected_utc or s.end_of_session_utc
        if end is None:
            continue
        best = None
        for j, a in enumerate(ardop):
            if j in used or a.peer != s.peer:
                continue
            gap = abs((a.end_utc - end).total_seconds())
            if gap <= slack_s and (best is None or gap < best[0]):
                best = (gap, j)
        if best:
            used.add(best[1])
            pairs[i] = ardop[best[1]]
    return pairs


# --- CSV export ---------------------------------------------------------------

SESSION_CSV = ["session", "transport", "peer", "connected_utc", "disconnected_utc", "dial_khz",
               "messages_sent", "bytes_sent", "messages_received", "bytes_received",
               "session_time_s", "avg_bytes_per_min", "peak_1min_bytes_per_min", "closed",
               "ardop_snr_db", "ardop_bandwidth_hz", "ardop_shift_ups", "ardop_shift_downs",
               "ardop_failed_decodes", "ardop_rx_quality"]
TRANSFER_CSV = ["session", "transport", "peer", "mid", "direction", "uncompressed_bytes",
                "compressed_bytes", "start_utc", "end_utc", "wire_bytes", "winlink_time_s",
                "winlink_bytes_per_min", "goodput_bps", "completed"]


def _iso(d: datetime | None) -> str:
    return d.isoformat() if d else ""


def write_csvs(sessions: list[Session], ardop: list[ArdopSession], out_dir: str | Path) -> tuple[Path, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pairs = match_ardop(sessions, ardop)
    sp, tp = out_dir / "sessions.csv", out_dir / "transfers.csv"
    with open(sp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SESSION_CSV)
        w.writeheader()
        for i, s in enumerate(sessions, start=1):
            a = pairs.get(i - 1)
            w.writerow({
                "session": i, "transport": s.transport, "peer": s.peer,
                "connected_utc": _iso(s.connected_utc), "disconnected_utc": _iso(s.disconnected_utc),
                "dial_khz": s.dial_khz or "", "messages_sent": s.messages_sent,
                "bytes_sent": s.bytes_sent, "messages_received": s.messages_received,
                "bytes_received": s.bytes_received, "session_time_s": s.session_time_s,
                "avg_bytes_per_min": s.avg_bytes_per_min,
                "peak_1min_bytes_per_min": s.peak_1min_bytes_per_min, "closed": s.closed,
                "ardop_snr_db": a.avg_leader_snr_db if a else "",
                "ardop_bandwidth_hz": a.bandwidth_hz if a else "",
                "ardop_shift_ups": a.mode_shift_ups if a else "",
                "ardop_shift_downs": a.mode_shift_downs if a else "",
                "ardop_failed_decodes": a.failed_frame_decodes if a else "",
                "ardop_rx_quality": "; ".join(f"{k}={q}/{n}" for k, (q, n) in a.rx_frame_quality.items()) if a else "",
            })
    with open(tp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=TRANSFER_CSV)
        w.writeheader()
        for i, s in enumerate(sessions, start=1):
            for t in s.transfers:
                g = t.goodput_bps
                w.writerow({
                    "session": i, "transport": s.transport, "peer": s.peer, "mid": t.mid,
                    "direction": t.direction, "uncompressed_bytes": t.uncompressed_bytes,
                    "compressed_bytes": t.compressed_bytes, "start_utc": _iso(t.start_utc),
                    "end_utc": _iso(t.end_utc), "wire_bytes": t.wire_bytes,
                    "winlink_time_s": t.winlink_time_s, "winlink_bytes_per_min": t.winlink_bytes_per_min,
                    "goodput_bps": f"{g:.1f}" if g else "", "completed": t.completed,
                })
    return sp, tp


# --- Redaction for fixtures ---------------------------------------------------

_GRID = re.compile(r"\(([A-R]{2}\d{2}[A-X]{2})\)", re.I)


def redact(text: str, callsign_map: dict[str, str]) -> str:
    """Replace callsigns (explicit map, longest first) and Maidenhead grids in ( )."""
    for real in sorted(callsign_map, key=len, reverse=True):
        text = re.sub(re.escape(real), callsign_map[real], text, flags=re.I)
    return _GRID.sub("(AA00AA)", text)


# --- ARDOP debug log: transmitter keying ------------------------------------------

_PTT = re.compile(r"^(\d\d:\d\d:\d\d\.\d{3}) \[Main\.KeyPTT\] (True|False)")
_DEBUG_DATE = re.compile(r"(\d{8})")


def parse_ardop_ptt(path: str | Path, date: str | None = None) -> list[tuple[datetime, datetime]]:
    """Transmit intervals (UTC) from an ARDOP_WinTNC_Debug_YYYYMMDD.log.
    The log holds time of day only; the date comes from the filename unless given."""
    p = Path(path)
    if date is None:
        m = _DEBUG_DATE.search(p.name)
        if not m:
            raise ValueError(f"no YYYYMMDD in {p.name}; pass date=")
        date = m.group(1)
    day = datetime.strptime(date, "%Y%m%d").replace(tzinfo=timezone.utc)
    raw = p.read_bytes().replace(b"\x00", b"")
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    raw = raw.decode("latin-1")  # the debug log also holds raw payload bytes
    out, on = [], None
    for line in _LINE_SPLIT.split(raw):
        m = _PTT.match(line.strip())
        if not m:
            continue
        h, mi, s = m.group(1).split(":")
        t = day.replace(hour=int(h), minute=int(mi)) + timedelta(seconds=float(s))
        if m.group(2) == "True":
            on = t
        elif on is not None:
            out.append((on, t))
            on = None
    return out
