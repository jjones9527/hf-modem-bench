import email
import random
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import pytest

from hfbench import messages as mg

PAYLOADS = Path(__file__).resolve().parents[1] / "payloads" / "Text_50KB"
NOW = datetime(2026, 11, 11, 1, 43, tzinfo=timezone.utc)


def test_split_payload_set_fixed_assignment():
    s1, s2 = mg.split_payload_set(PAYLOADS)
    assert [p.name for p in s1] == ["File-2oE8o.txt", "File-A9TS9.txt", "File-FJYnL.txt", "File-NqdBp.txt", "File-YtirF.txt"]
    assert [p.name for p in s2] == ["File-bOgW3.txt", "File-gkTVB.txt", "File-h71Al.txt", "File-ozUgP.txt", "File-z7j7V.txt"]


def test_import_xml_roundtrip():
    s1, _ = mg.split_payload_set(PAYLOADS)
    rng = random.Random(1)
    msgs = mg.run_messages("coarse01-0007", "VA3ZTF", "VE3XZQ", s1, rng=rng, now=NOW)
    xml = mg.build_import_xml(msgs, "VA3ZTF", rng=rng, now=NOW)
    assert xml.startswith(b'<?xml version="1.0"?>')
    root = ET.fromstring(xml)
    assert root.find("export_parameters/callsign").text == "VA3ZTF"
    items = root.findall("message_list/message")
    assert len(items) == 5
    mids = [i.find("id").text for i in items]
    assert len(set(mids)) == 5 and all(len(m) == 12 and m.isalnum() and m.isupper() for m in mids)
    for n, (item, f) in enumerate(zip(items, s1), start=1):
        assert item.find("folder").text == "Outbox" and item.find("peertopeer").text == "True"
        assert item.find("subject").text == f"hfbench coarse01-0007 {n}/5"
        msg = email.message_from_string(item.find("mime").text)
        assert msg["Message-ID"] == item.find("id").text and msg["To"] == "VE3XZQ@winlink.org"
        assert msg["X-P2P"] == "True"
        att = [p for p in msg.walk() if p.get_filename()]
        assert att[0].get_filename() == f.name and att[0].get_payload(decode=True) == f.read_bytes()


def test_new_mids_are_unique():
    assert len({mg.new_mid() for _ in range(2000)}) == 2000
