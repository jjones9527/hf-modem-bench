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


def test_templates_instantiate_identically_except_run_fields(tmp_path):
    paths = mg.build_campaign_templates(PAYLOADS, ("VA3ZTF", "VE3XZQ"), tmp_path)
    t1 = paths[1].read_text()
    assert t1.count("@@MID") == 10 and len(set(__import__("re").findall(r"@@MID\d\d@@", t1))) == 5  # id + Message-ID header
    assert "@@RUNID@@" in t1
    a, mids_a = mg.instantiate(t1, "coarse01-0001", now=NOW, rng=random.Random(1))
    b, mids_b = mg.instantiate(t1, "coarse01-0002", now=NOW, rng=random.Random(2))
    assert len(a) == len(b)                       # byte-identical size across runs
    assert set(mids_a).isdisjoint(mids_b)
    root = ET.fromstring(a)
    items = root.findall("message_list/message")
    assert [i.find("id").text for i in items] == mids_a
    assert items[2].find("subject").text == "hfbench coarse01-0001 3/5"
    msg = email.message_from_string(items[0].find("mime").text)
    assert msg["Message-ID"] == mids_a[0] and msg["Date"] == "Wed, 11 Nov 2026 01:43:00 +0000"
    att = [p for p in msg.walk() if p.get_filename()][0]
    assert att.get_payload(decode=True) == (PAYLOADS / "File-2oE8o.txt").read_bytes()
    # station 2 template sends the other five files to station 1
    msg2 = email.message_from_string(ET.fromstring(mg.instantiate(paths[2].read_text(), "x", now=NOW)[0])
                                     .find("message_list/message/mime").text)
    assert msg2["From"] == "VE3XZQ@winlink.org" and msg2["To"] == "VA3ZTF@winlink.org"


def test_cli_messages_build(tmp_path, capsys):
    from hfbench.cli import main
    from hfbench import matrix as mx
    camp = tmp_path / "c"
    mx.write_runsheet([], camp / "runsheet.csv")
    main(["messages", "build", "-d", str(camp), "--payloads", str(PAYLOADS), "--s1-call", "VA3ZTF", "--s2-call", "VE3XZQ"])
    assert (camp / "messages" / "station1.template.xml").exists()
    assert "3ec10a0b30de" in capsys.readouterr().out
