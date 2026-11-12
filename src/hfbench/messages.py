"""Generate Winlink Express message-import XML for a run's workload.

The format mirrors Winlink Express 1.8.6.0's *Message > Export selected
messages* output for a P2P message in Sent Items, line for line in the MIME
part headers. Messages imported
with folder "Outbox" appear there, ready to send; this was verified on the bench
on 11 Nov 2026. Each message gets a fresh, unique Message-ID, because a
receiving station rejects IDs it has seen before.

Subjects carry the run ID, e.g. "hfbench coarse01-0007 3/5", so every transfer
in the Winlink logs can be traced to its run.
"""

from __future__ import annotations

import base64
import random
import string
import textwrap
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

MID_CHARS = string.ascii_uppercase + string.digits


def new_mid(rng: random.Random | None = None) -> str:
    """12-character Winlink-style message ID."""
    r = rng or random.SystemRandom()
    return "".join(r.choice(MID_CHARS) for _ in range(12))


@dataclass
class OutMessage:
    mid: str
    sender: str
    recipient: str
    subject: str
    attachment: Path
    date: datetime
    body: str = "<No message body>"


def _mime(m: OutMessage, rng: random.Random) -> str:
    boundary = "boundary" + "".join(rng.choice(string.ascii_letters) for _ in range(6)) + "=="
    data = m.attachment.read_bytes()
    b64 = "\n".join(textwrap.wrap(base64.b64encode(data).decode("ascii"), 76))
    name = m.attachment.name
    cancel = (m.date + timedelta(days=21)).strftime("%Y/%m/%d %H:%M")
    # Winlink labels .txt attachments text/plain (as in its own export)
    ctype = "text/plain" if name.lower().endswith(".txt") else "application/octet-stream"
    return "\n".join([
        f"Date: {m.date.strftime('%a, %d %b %Y %H:%M:%S +0000')}",
        f"From: {m.sender}@winlink.org",
        f"Reply-To: {m.sender}@winlink.org",
        f"Subject: {m.subject}",
        f"To: {m.recipient}@winlink.org",
        f"Message-ID: {m.mid}",
        f"X-Cancel: {cancel}",
        f"X-Source: {m.sender}",
        "X-P2P: True",
        "MIME-Version: 1.0",
        f'Content-Type: multipart/mixed; boundary="{boundary}"',
        "",
        f"--{boundary}",
        'Content-Type: text/plain; charset="iso-8859-1"',
        "Content-Transfer-Encoding: quoted-printable",
        "",
        m.body,
        "",
        f"--{boundary}",
        f'Content-Disposition: attachment; name="{name}";',
        f' filename="{name}"',
        f'Content-Type: {ctype}; name="{name}"',
        "Content-Transfer-Encoding: base64",
        "",
        b64,
        f"--{boundary}--",
    ])


def build_import_xml(messages: list[OutMessage], exporter: str, *, folder: str = "Outbox",
                     rng: random.Random | None = None, now: datetime | None = None) -> bytes:
    rng = rng or random.SystemRandom()
    now = (now or datetime.now(timezone.utc)).replace(microsecond=0)
    root = ET.Element("Winlink_Express_message_export")
    ep = ET.SubElement(root, "export_parameters")
    for tag, val in (("xml_file_version", "1.0"), ("winlink_express_version", "1.8.6.0"),
                     ("export_datetime_utc", now.strftime("%Y%m%d%H%M%S")), ("callsign", exporter)):
        ET.SubElement(ep, tag).text = val
    ml = ET.SubElement(root, "message_list")
    for m in messages:
        e = ET.SubElement(ml, "message")
        fields = [
            ("id", m.mid), ("foldertype", "Fixed"), ("folder", folder), ("subject", m.subject),
            ("time", m.date.strftime("%Y/%m/%d %H:%M")), ("sender", m.sender),
            ("acknowledged", None), ("attachmentsopened", None), ("replied", None),
            ("rmsoriginator", None), ("rmsdestination", None), ("rmspath", None),
            ("location", None), ("csize", str(m.attachment.stat().st_size)),
            ("downloadserver", None), ("forwarded", None), ("messageserver", None),
            ("precedence", "2"), ("peertopeer", "True"), ("routingflag", None), ("replied", None),
            ("source", m.sender), ("unread", "False"), ("flags", "2"),
            ("messageoptions", "True|False||||False|"), ("mime", _mime(m, rng)),
        ]
        for tag, val in fields:
            ET.SubElement(e, tag).text = val
    return b'<?xml version="1.0"?>\n' + ET.tostring(root, encoding="utf-8")


def run_messages(run_id: str, sender: str, recipient: str, files: list[Path], *,
                 rng: random.Random | None = None, now: datetime | None = None) -> list[OutMessage]:
    """One message per attachment file, subjects tagged with the run ID."""
    now = (now or datetime.now(timezone.utc)).replace(microsecond=0)
    n = len(files)
    return [OutMessage(new_mid(rng), sender, recipient, f"hfbench {run_id} {i}/{n}", f, now)
            for i, f in enumerate(files, start=1)]


def split_payload_set(directory: str | Path, per_station: int = 5,
                      counts: tuple[int, int] | None = None) -> tuple[list[Path], list[Path]]:
    """Fixed assignment by sorted name: station 1 gets the first n1 files, station 2
    the next n2. counts=(n1, n2) overrides per_station; (10, 0) is a one-way
    workload in which only station 1 sends."""
    n1, n2 = counts if counts is not None else (per_station, per_station)
    if n1 < 0 or n2 < 0 or n1 + n2 == 0:
        raise ValueError(f"message counts must be >= 0 and not both 0, got {n1} + {n2}")
    # exact-name order on every OS (WindowsPath sorts case-insensitively)
    files = sorted((p for p in Path(directory).iterdir() if p.is_file()), key=lambda p: p.name)
    if len(files) < n1 + n2:
        raise ValueError(f"need {n1 + n2} files in {directory}, found {len(files)}")
    return files[:n1], files[n1:n1 + n2]


# --- campaign templates: build once, instantiate per run --------------------------
#
# A template is a complete import XML whose run-specific fields are placeholders.
# Instantiating substitutes only the Message-IDs, dates and run ID, so every
# run's messages are byte-identical apart from those fields. Run IDs in a
# campaign have a fixed width, so message sizes are identical too.

PH_RUN = "@@RUNID@@"
PH_NOW_RFC = "@@DATE_RFC@@"
PH_NOW_TIME = "@@TIME@@"
PH_CANCEL = "@@CANCEL@@"
PH_EXPORT = "@@EXPORT_TS@@"


def _ph_mid(i: int) -> str:
    return f"@@MID{i:02d}@@"   # 12 chars, same length as a real MID


def build_template(sender: str, recipient: str, files: list[Path], *,
                   rng: random.Random | None = None) -> str:
    """Import XML for one station's messages with placeholders for per-run fields."""
    rng = rng or random.Random(0)          # deterministic MIME boundaries
    fixed = datetime(2000, 1, 1, tzinfo=timezone.utc)
    n = len(files)
    msgs = [OutMessage(_ph_mid(i), sender, recipient, f"hfbench {PH_RUN} {i}/{n}", f, fixed)
            for i, f in enumerate(files, start=1)]
    xml = build_import_xml(msgs, sender, rng=rng, now=fixed).decode("utf-8")
    xml = xml.replace(fixed.strftime("%a, %d %b %Y %H:%M:%S +0000"), PH_NOW_RFC)
    xml = xml.replace((fixed + timedelta(days=21)).strftime("%Y/%m/%d %H:%M"), PH_CANCEL)
    xml = xml.replace(fixed.strftime("%Y/%m/%d %H:%M"), PH_NOW_TIME)
    xml = xml.replace(fixed.strftime("%Y%m%d%H%M%S"), PH_EXPORT)
    return xml


def instantiate(template: str, run_id: str, *, now: datetime | None = None,
                rng: random.Random | None = None) -> tuple[bytes, list[str]]:
    """Fill a template for one run. Returns (import XML bytes, message IDs)."""
    rng = rng or random.SystemRandom()
    now = (now or datetime.now(timezone.utc)).replace(microsecond=0)
    out = template
    mids = []
    i = 1
    while _ph_mid(i) in out:
        mid = new_mid(rng)
        mids.append(mid)
        out = out.replace(_ph_mid(i), mid)
        i += 1
    for ph, val in ((PH_RUN, run_id), (PH_NOW_RFC, now.strftime("%a, %d %b %Y %H:%M:%S +0000")),
                    (PH_CANCEL, (now + timedelta(days=21)).strftime("%Y/%m/%d %H:%M")),
                    (PH_NOW_TIME, now.strftime("%Y/%m/%d %H:%M")),
                    (PH_EXPORT, now.strftime("%Y%m%d%H%M%S"))):
        out = out.replace(ph, val)
    if "@@" in out:
        raise ValueError("unfilled placeholder left in template")
    return out.encode("utf-8"), mids


def build_campaign_templates(payload_dir: str | Path, calls: tuple[str, str], out_dir: str | Path,
                             per_station: int = 5, counts: tuple[int, int] | None = None) -> dict[int, Path]:
    """Write messages/station1.template.xml and station2.template.xml (built once).
    A station with no messages gets a template with an empty message list."""
    s1, s2 = split_payload_set(payload_dir, per_station, counts)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {}
    for st, files, me, other in ((1, s1, calls[0], calls[1]), (2, s2, calls[1], calls[0])):
        p = out / f"station{st}.template.xml"
        p.write_text(build_template(me, other, files), encoding="utf-8")
        paths[st] = p
    return paths
