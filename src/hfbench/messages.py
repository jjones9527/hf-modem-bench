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


def split_payload_set(directory: str | Path, per_station: int = 5) -> tuple[list[Path], list[Path]]:
    """Fixed assignment: sorted names; first half station 1, second half station 2."""
    files = sorted(p for p in Path(directory).iterdir() if p.is_file())
    if len(files) < 2 * per_station:
        raise ValueError(f"need {2 * per_station} files in {directory}, found {len(files)}")
    return files[:per_station], files[per_station:2 * per_station]
