"""hfbench command line.

Typical bench flow (run the stamp commands on the Winlink Express machine so
stamps and Winlink log timestamps share one clock):

    hfbench payload make payloads/payload-20k.bin --bytes 20000 --seed 1
    hfbench sheet runs/coarse-01.toml            # -> runs/<campaign>/runsheet.csv
    hfbench next  -d runs/<campaign>
    hfbench start -d runs/<campaign> <run_id>
    hfbench mark  -d runs/<campaign> "WGN:5"     # optional mid-run event
    hfbench end   -d runs/<campaign> completed|dnc|invalid [--notes ...]
    hfbench manifest -d runs/<campaign>          # -> manifest.csv
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import manifest as mf
from . import matrix as mx
from . import payload as pl

RUNSHEET = "runsheet.csv"
EVENTS = "events.jsonl"
MANIFEST = "manifest.csv"


def _campaign_dir(args) -> Path:
    d = args.dir or os.environ.get("HFBENCH_CAMPAIGN")
    if not d:
        sys.exit("error: give -d/--dir CAMPAIGN_DIR or set HFBENCH_CAMPAIGN")
    d = Path(d)
    if not (d / RUNSHEET).exists():
        sys.exit(f"error: {d / RUNSHEET} not found (generate it with `hfbench sheet`)")
    return d


def _describe(r: dict) -> str:
    imp = r["impairment"] + (f" ({r['impairment_notes']})" if r["impairment_notes"] else "")
    return (f"{r['run_id']}  {r['modem']} {r['modem_version']} | {r['profile']} "
            f"({r['doppler_hz']} Hz / {r['delay_ms']} ms) | S:N {r['snr_db']} dB in "
            f"{r['sim_bandwidth_hz']} Hz | impairment {imp} | rep {r['replicate']}\n"
            f"  IONOS: {r['ionos_commands']}")


def cmd_sheet(args):
    m = mx.load_matrix(args.matrix)
    rows = mx.build_runs(m)
    out = Path(args.out) if args.out else Path(args.matrix).parent / m.campaign / RUNSHEET
    if out.exists() and not args.force:
        sys.exit(f"error: {out} exists; regenerating can renumber runs. Use --force if no runs have started.")
    mx.write_runsheet(rows, out)
    hours = len(rows) * args.minutes_per_run / 60
    print(f"wrote {len(rows)} runs to {out} (~{hours:.0f} h at {args.minutes_per_run} min/run)")


def cmd_next(args):
    d = _campaign_dir(args)
    rows = mx.read_runsheet(d / RUNSHEET)
    events = mf.read_events(d / EVENTS)
    for r in rows:
        st = mf.run_state(events, r["run_id"])
        if st == "running":
            print("IN PROGRESS: " + _describe(r))
            return
    for r in rows:
        if mf.run_state(events, r["run_id"]) == "pending":
            print("NEXT: " + _describe(r))
            return
    print("all runs have a result")


def cmd_start(args):
    d = _campaign_dir(args)
    rows = mx.read_runsheet(d / RUNSHEET)
    ids = {r["run_id"] for r in rows}
    ev = mf.start_run(d / EVENTS, args.run_id, valid_ids=ids, retry=args.retry)
    r = next(r for r in rows if r["run_id"] == args.run_id)
    print(f"started {_describe(r)}\n  at {ev['t_local']}")


def cmd_end(args):
    d = _campaign_dir(args)
    ev = mf.end_run(d / EVENTS, args.run_id, args.outcome, notes=args.notes or "")
    print(f"ended {ev['run_id']} -> {ev['outcome']} at {ev['t_local']}")


def cmd_mark(args):
    d = _campaign_dir(args)
    ev = mf.mark_run(d / EVENTS, args.note)
    print(f"marked {ev['run_id']}: {ev['notes']} at {ev['t_local']}")


def cmd_status(args):
    d = _campaign_dir(args)
    rows = mx.read_runsheet(d / RUNSHEET)
    events = mf.read_events(d / EVENTS)
    man = mf.build_manifest(rows, events)
    final = [r for r in man if r["final_attempt"] == "yes"]
    counts = {o: sum(1 for r in final if r["outcome"] == o) for o in mf.OUTCOMES}
    running = sum(1 for r in final if r["outcome"] == "")
    print(f"{len(rows)} runs: " + ", ".join(f"{k} {v}" for k, v in counts.items())
          + f", running {running}, pending {len(rows) - len(final)}")


def cmd_manifest(args):
    d = _campaign_dir(args)
    rows = mx.read_runsheet(d / RUNSHEET)
    man = mf.build_manifest(rows, mf.read_events(d / EVENTS))
    out = Path(args.out) if args.out else d / MANIFEST
    mf.write_manifest(man, mx.RUNSHEET_FIELDS, out)
    print(f"wrote {len(man)} attempts to {out}")


def cmd_payload_make(args):
    digest = pl.make_payload(args.path, args.bytes, args.seed)
    print(f"{args.path}: {args.bytes} bytes, seed {args.seed}\n"
          f"sha256 = {digest}\nzlib ratio = {pl.compress_ratio(args.path):.3f}")


def cmd_payload_hash(args):
    print(f"sha256 = {pl.sha256_file(args.path)}\n"
          f"bytes = {Path(args.path).stat().st_size}\n"
          f"zlib ratio = {pl.compress_ratio(args.path):.3f} (close to 1.0 means incompressible)")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="hfbench", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def with_dir(sp):
        sp.add_argument("-d", "--dir", help="campaign directory (or set HFBENCH_CAMPAIGN)")
        return sp

    s = sub.add_parser("sheet", help="generate run sheet from a matrix TOML")
    s.add_argument("matrix")
    s.add_argument("-o", "--out")
    s.add_argument("--force", action="store_true")
    s.add_argument("--minutes-per-run", type=float, default=10)
    s.set_defaults(func=cmd_sheet)

    with_dir(sub.add_parser("next", help="show the run in progress or the next pending run")).set_defaults(func=cmd_next)
    with_dir(sub.add_parser("status", help="count outcomes")).set_defaults(func=cmd_status)

    s = with_dir(sub.add_parser("start", help="stamp a run's start time"))
    s.add_argument("run_id")
    s.add_argument("--retry", action="store_true", help="record another attempt of a finished run")
    s.set_defaults(func=cmd_start)

    s = with_dir(sub.add_parser("end", help="stamp the running run's end time and outcome"))
    s.add_argument("outcome", choices=mf.OUTCOMES)
    s.add_argument("--run-id", help="defaults to the run in progress")
    s.add_argument("--notes")
    s.set_defaults(func=cmd_end)

    s = with_dir(sub.add_parser("mark", help="timestamp a mid-run event, e.g. an SNR step"))
    s.add_argument("note")
    s.set_defaults(func=cmd_mark)

    s = with_dir(sub.add_parser("manifest", help="build manifest.csv from run sheet + events"))
    s.add_argument("-o", "--out")
    s.set_defaults(func=cmd_manifest)

    pay = sub.add_parser("payload", help="make or hash the test payload").add_subparsers(dest="pcmd", required=True)
    s = pay.add_parser("make")
    s.add_argument("path")
    s.add_argument("--bytes", type=int, required=True)
    s.add_argument("--seed", type=int, required=True)
    s.set_defaults(func=cmd_payload_make)
    s = pay.add_parser("hash")
    s.add_argument("path")
    s.set_defaults(func=cmd_payload_hash)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except (mx.MatrixError, mf.ManifestError) as e:
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    main()
