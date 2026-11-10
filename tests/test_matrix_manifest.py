from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from hfbench import manifest as mf
from hfbench import matrix as mx
from hfbench import payload as pl
from hfbench.cli import main

EXAMPLE = Path(__file__).resolve().parents[1] / "runs" / "example-matrix.toml"


def test_example_matrix_expands_to_full_cross():
    m = mx.load_matrix(EXAMPLE)
    rows = mx.build_runs(m)
    assert len(rows) == 3 * 5 * 5 * 3  # modems x profiles x SNRs x replicates
    assert [r["seq"] for r in rows] == list(range(1, len(rows) + 1))
    assert len({r["run_id"] for r in rows}) == len(rows)


def test_blocked_random_keeps_modems_contiguous_and_is_deterministic():
    m = mx.load_matrix(EXAMPLE)
    rows = mx.build_runs(m)
    modems = [r["modem"] for r in rows]
    blocks = [k for i, k in enumerate(modems) if i == 0 or modems[i - 1] != k]
    assert sorted(blocks) == sorted({x.name for x in m.modems})  # each modem one block
    assert rows == mx.build_runs(mx.load_matrix(EXAMPLE))
    # actually shuffled within a block
    first = [(r["profile"], r["snr_db"]) for r in rows if r["modem"] == blocks[0]]
    assert first != sorted(first)


EXAMPLE_IMP = EXAMPLE.with_name("example-impairments.toml")


def test_ionos_commands_reset_addons_and_set_mode_last():
    rows = mx.build_runs(mx.load_matrix(EXAMPLE))
    r = next(r for r in rows if r["profile"] == "MPP" and r["snr_db"] == 10)
    cmds = r["ionos_commands"].split("; ")
    assert cmds[0] == "BANDWIDTH:3000" and cmds[1] == "MULTIPATH:2"
    assert "OFFSET:0" in cmds and "FADE DEPTH:0" in cmds
    assert cmds[-1] == "MPP:10"
    assert (r["doppler_hz"], r["delay_ms"]) == (1.0, 2.0)


def test_impairment_matrix_sets_addons():
    rows = mx.build_runs(mx.load_matrix(EXAMPLE_IMP))
    r = next(r for r in rows if r["impairment"] == "drift10")
    assert "FM DEVIATION:10" in r["ionos_commands"] and "FM RATE:0.1" in r["ionos_commands"]
    assert r["ionos_commands"].endswith("WGN:15")
    assert r["multipaths"] == 1


def _variant(tmp_path, old, new, src=EXAMPLE):
    f = tmp_path / "m.toml"
    text = src.read_text()
    assert old in text
    f.write_text(text.replace(old, new))
    return f


@pytest.mark.parametrize("old,new", [
    ('profiles = ["WGN"]', 'profiles = ["WGN", "MPG"]'),    # WGN-only add-on with multipath
    ("OFFSET = 50", "OFFSET = 55"),                          # not a 10 Hz step
    ('"FADE FREQ" = 10', '"FADE FREQ" = 3'),                 # not a log-scale value
    ("snr_db = [15]", "snr_db = [15.5]"),                    # 1 dB steps only
    ("snr_db = [15]", "snr_db = [45]"),                      # out of range
])
def test_ionos_constraints(tmp_path, old, new):
    with pytest.raises(mx.MatrixError):
        mx.load_matrix(_variant(tmp_path, old, new, EXAMPLE_IMP))


def test_unknown_profile_rejected(tmp_path):
    with pytest.raises(mx.MatrixError):
        mx.load_matrix(_variant(tmp_path, '"MPD"]', '"FLUTTER"]'))


def test_snr_by_profile_override():
    m = mx.load_matrix(EXAMPLE)
    m.snr_by_profile = {"MPM": [12, 10, 8]}
    rows = mx.build_runs(m)
    assert {r["snr_db"] for r in rows if r["profile"] == "MPM"} == {12, 10, 8}
    assert {r["snr_db"] for r in rows if r["profile"] == "WGN"} == {30, 20, 10, 5, 0}


def test_validation_rejects_bad_hash(tmp_path):
    with pytest.raises(mx.MatrixError):
        mx.load_matrix(_variant(tmp_path, 'sha256 = "3ec1', 'sha256 = "zz'))


T0 = datetime(2026, 11, 10, 18, 0, tzinfo=timezone.utc)


def test_start_end_and_manifest(tmp_path):
    ev = tmp_path / "events.jsonl"
    sheet = mx.build_runs(mx.load_matrix(EXAMPLE))[:3]
    sheet = [{k: str(v) for k, v in r.items()} for r in sheet]
    ids = {r["run_id"] for r in sheet}
    a, b = sheet[0]["run_id"], sheet[1]["run_id"]

    mf.start_run(ev, a, valid_ids=ids, t=T0)
    with pytest.raises(mf.ManifestError):  # one run at a time
        mf.start_run(ev, b, valid_ids=ids, t=T0)
    mf.mark_run(ev, "WGN:5", t=T0 + timedelta(minutes=3))
    mf.end_run(ev, None, "dnc", notes="abort at 30 min", t=T0 + timedelta(minutes=30))
    with pytest.raises(mf.ManifestError):  # nothing running
        mf.mark_run(ev, "late")
    with pytest.raises(mf.ManifestError):  # already has a result
        mf.start_run(ev, a, valid_ids=ids, t=T0)
    mf.start_run(ev, a, valid_ids=ids, retry=True, t=T0 + timedelta(minutes=31))
    mf.end_run(ev, a, "completed", t=T0 + timedelta(minutes=40))
    mf.start_run(ev, b, valid_ids=ids, t=T0 + timedelta(minutes=41))  # left running

    man = mf.build_manifest(sheet, mf.read_events(ev))
    assert [(r["run_id"], r["attempt"], r["outcome"], r["final_attempt"]) for r in man] == [
        (a, 1, "dnc", "no"), (a, 2, "completed", "yes"), (b, 1, "", "yes")]
    assert man[0]["duration_s"] == 1800
    assert man[0]["notes"] == "abort at 30 min"
    assert man[0]["marks"] == "+180s WGN:5" and man[1]["marks"] == ""


def test_unknown_run_and_bad_outcome(tmp_path):
    ev = tmp_path / "events.jsonl"
    with pytest.raises(mf.ManifestError):
        mf.start_run(ev, "nope", valid_ids={"x"})
    with pytest.raises(mf.ManifestError):
        mf.end_run(ev, None, "finished")


def test_payload_is_reproducible_and_incompressible(tmp_path):
    p = tmp_path / "p.bin"
    h = pl.make_payload(p, 51200, 1)
    assert h == "a324e9181248799f8023f76ea2277f1d76d731a4302b46ecd26d0c12d927ba0b"
    assert pl.sha256_file(p) == h
    assert pl.compress_ratio(p) > 0.99


def test_payload_set_hash(tmp_path):
    for name, data in (("b.txt", b"two"), ("A.txt", b"one")):
        (tmp_path / name).write_bytes(data)
    h1, per = pl.sha256_set(tmp_path)
    assert list(per) == ["A.txt", "b.txt"]  # deterministic order
    (tmp_path / "b.txt").write_bytes(b"TWO")
    assert pl.sha256_set(tmp_path)[0] != h1


def test_cli_end_to_end(tmp_path, capsys):
    matrix = tmp_path / "m.toml"
    matrix.write_text(EXAMPLE.read_text())
    main(["sheet", str(matrix)])
    d = tmp_path / "coarse01"
    rows = mx.read_runsheet(d / "runsheet.csv")
    main(["next", "-d", str(d)])
    assert rows[0]["run_id"] in capsys.readouterr().out
    main(["start", "-d", str(d), rows[0]["run_id"]])
    main(["end", "-d", str(d), "completed"])
    main(["manifest", "-d", str(d)])
    man = mx.read_runsheet(d / "manifest.csv")  # same CSV reader works
    assert man[0]["outcome"] == "completed" and man[0]["stamp_host"]
    with pytest.raises(SystemExit):  # refuse to renumber an existing sheet
        main(["sheet", str(matrix)])
