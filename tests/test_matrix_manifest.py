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


def test_seed_modes():
    m = mx.load_matrix(EXAMPLE)
    assert {r["channel_seed"] for r in mx.build_runs(m)} == {"1"}
    m.seed_mode = "per-replicate"
    rows = mx.build_runs(m)
    assert all(int(r["channel_seed"]) == r["replicate"] for r in rows)


def test_snr_by_profile_override():
    m = mx.load_matrix(EXAMPLE)
    m.snr_by_profile = {"Moderate": [12, 10, 8]}
    rows = mx.build_runs(m)
    assert {r["snr_db"] for r in rows if r["profile"] == "Moderate"} == {"12", "10", "8"}
    assert {r["snr_db"] for r in rows if r["profile"] == "AWGN"} == {"30", "20", "10", "5", "0"}


def test_validation_rejects_bad_hash(tmp_path):
    bad = tmp_path / "m.toml"
    bad.write_text(EXAMPLE.read_text().replace('sha256 = "6746', 'sha256 = "zz'))
    with pytest.raises(mx.MatrixError):
        mx.load_matrix(bad)


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
    mf.end_run(ev, None, "dnc", notes="abort at 30 min", t=T0 + timedelta(minutes=30))
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


def test_unknown_run_and_bad_outcome(tmp_path):
    ev = tmp_path / "events.jsonl"
    with pytest.raises(mf.ManifestError):
        mf.start_run(ev, "nope", valid_ids={"x"})
    with pytest.raises(mf.ManifestError):
        mf.end_run(ev, None, "finished")


def test_payload_is_reproducible_and_incompressible(tmp_path):
    p = tmp_path / "p.bin"
    h = pl.make_payload(p, 20000, 1)
    assert h == mx.load_matrix(EXAMPLE).payload_sha256
    assert pl.sha256_file(p) == h
    assert pl.compress_ratio(p) > 0.99


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
