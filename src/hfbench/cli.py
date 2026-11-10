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

from . import logparse as lp
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


def cmd_parse(args):
    sessions = []
    for p in args.winlink_log:
        sessions += lp.parse_winlink_log(p)
    ardop = []
    for p in args.ardop or []:
        ardop += lp.parse_ardop_sessions(p)
    sp, tp = lp.write_csvs(sessions, ardop, args.out)
    n_tr = sum(len(s.transfers) for s in sessions)
    print(f"{len(sessions)} sessions, {n_tr} transfers -> {sp}, {tp}")
    for i, s in enumerate(sessions, start=1):
        for t in s.transfers:
            g = f"{t.goodput_bps:7.0f} bit/s" if t.goodput_bps else "   incomplete"
            print(f"  s{i:<3} {s.transport:<12} {t.direction} {t.mid}  {t.compressed_bytes or '?':>6} B  {g}")


def _keypoller():
    """Non-blocking single-key reader for Windows consoles and POSIX terminals."""
    try:
        import msvcrt

        return lambda: msvcrt.getwch() if msvcrt.kbhit() else None
    except ImportError:
        import select

        def poll():
            r, _, _ = select.select([sys.stdin], [], [], 0)
            return sys.stdin.readline().strip()[:1] if r else None
        return poll


def cmd_ionos(args):
    from .ionos import Ionos

    io = Ionos.open(args.port)
    io.allow_gains = getattr(args, "allow_gains", False)
    try:
        if args.icmd == "probe":
            print("IONOS answered" if io.probe() else "no valid reply")
        elif args.icmd == "send":
            for a in io.apply(" ; ".join(args.commands)):
                print(f"{a.command} -> {a.reply}")
        elif args.icmd == "apply":
            d = _campaign_dir(args)
            row = next((r for r in mx.read_runsheet(d / RUNSHEET) if r["run_id"] == args.run_id), None)
            if row is None:
                sys.exit(f"error: unknown run id {args.run_id}")
            for a in io.apply(row["ionos_commands"]):
                print(f"{a.command} -> {a.reply}")
    finally:
        io.close()


def cmd_run(args):
    from .bench import BenchRunner, winlink_session_source

    ionos = None
    if args.port:
        from .ionos import Ionos

        ionos = Ionos.open(args.port)
        if not ionos.probe():
            sys.exit(f"error: no reply from IONOS on {args.port}")
    key = _keypoller()

    def between():
        print("\nNext run ready. Press Enter to continue, q then Enter to stop.")
        return input().strip().lower() != "q"

    runner = BenchRunner(_campaign_dir(args), winlink_session_source(args.winlink_dir),
                         ionos=ionos, key=key, poll_s=args.poll)
    try:
        runner.run(max_runs=args.max_runs, wait_between=between)
    finally:
        if ionos is not None:
            ionos.close()


IONOS_RESET = "BANDWIDTH:3000; MULTIPATH:2; OFFSET:0; FADE DEPTH:0; FADE FREQ:0; FM DEVIATION:0; FM RATE:0"


def cmd_audio(args):
    import json

    from . import audio

    if args.acmd == "devices":
        import sounddevice as sd

        apis = sd.query_hostapis()
        for i, d in enumerate(sd.query_devices()):
            print(f"{i:3d}  in={d['max_input_channels']} out={d['max_output_channels']}  "
                  f"{d['default_samplerate']:>7.0f} Hz  {apis[d['hostapi']]['name']:<22} {d['name']}")
        return

    stations = (audio.station_from_ardop_ini(1, args.s1), audio.station_from_ardop_ini(2, args.s2))
    for s in stations:
        print(f"station {s.number}: play '{s.playback}', record '{s.capture}', DriveLevel {s.drive_level}")
    io = None
    if args.port:
        from .ionos import Ionos

        io = Ionos.open(args.port)
    results = []
    try:
        while True:
            for snr in args.snr:
                setting = f"WGN:{snr}"
                if io is not None:
                    io.apply(f"{IONOS_RESET}; {setting}")
                    print(f"\nIONOS set to WGN, S:N {snr} dB (add-ons off)")
                else:
                    print(f"\nSet the IONOS to WGN, S:N {snr} dB by hand (no --port given).")
                r = audio.run_check(stations, seconds=args.seconds, ionos_setting=setting if io else "")
                print(audio.format_result(r))
                results.append(r)
            if not args.loop:
                break
            print("\n--- adjust levels now; re-measuring in 3 s (Ctrl+C to stop) ---")
            import time
            time.sleep(3)
    except KeyboardInterrupt:
        pass
    finally:
        if io is not None:
            io.close()
    if args.json:
        from dataclasses import asdict
        Path(args.json).write_text(json.dumps([asdict(r) for r in results], indent=2, default=str))
        print(f"\nsaved {args.json}")


def cmd_payload_make(args):
    digest = pl.make_payload(args.path, args.bytes, args.seed)
    print(f"{args.path}: {args.bytes} bytes, seed {args.seed}\n"
          f"sha256 = {digest}\nzlib ratio = {pl.compress_ratio(args.path):.3f}")


def cmd_payload_hash(args):
    if Path(args.path).is_dir():
        digest, per = pl.sha256_set(args.path)
        for name, h in per.items():
            f = Path(args.path) / name
            print(f"  {h}  {name}  {f.stat().st_size} bytes  zlib {pl.compress_ratio(f):.3f}")
        print(f"set sha256 = {digest}  ({len(per)} files)")
        return
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

    s = sub.add_parser("parse", help="parse Winlink Express (and ARDOP) logs to sessions/transfers CSV")
    s.add_argument("winlink_log", nargs="+", help="RMS Express YYYYMMDD.log file(s)")
    s.add_argument("--ardop", nargs="*", help="ARDOP_WinTNC_ARQSession_YYYYMMDD.log file(s)")
    s.add_argument("-o", "--out", default=".", help="output directory")
    s.set_defaults(func=cmd_parse)

    io = sub.add_parser("ionos", help="control the IONOS simulator over USB serial").add_subparsers(dest="icmd", required=True)
    s = io.add_parser("probe", help="check the IONOS answers (changes nothing)")
    s.add_argument("--port", default="COM3")
    s.set_defaults(func=cmd_ionos)
    s = io.add_parser("send", help="send commands, e.g. 'WGN:20' 'OFFSET:0'")
    s.add_argument("commands", nargs="+")
    s.add_argument("--port", default="COM3")
    s.add_argument("--allow-gains", action="store_true", help="permit CH1/CH2 IN/OUT gain commands")
    s.set_defaults(func=cmd_ionos)
    s = with_dir(io.add_parser("apply", help="apply a run's IONOS settings from the run sheet"))
    s.add_argument("run_id")
    s.add_argument("--port", default="COM3")
    s.set_defaults(func=cmd_ionos)

    s = with_dir(sub.add_parser("run", help="semi-automatic bench run: set IONOS, detect sessions, record outcomes"))
    s.add_argument("--winlink-dir", default=r"C:\RMS Express", help="station 1 (calling) Winlink install")
    s.add_argument("--port", default="COM3", help="IONOS serial port; '' to set IONOS by hand")
    s.add_argument("--poll", type=float, default=2.0, help="log poll interval, seconds")
    s.add_argument("--max-runs", type=int)
    s.set_defaults(func=cmd_run)

    au = sub.add_parser("audio", help="tone-based level check (run on the Windows desktop)").add_subparsers(dest="acmd", required=True)
    s = au.add_parser("devices", help="list sound devices")
    s.set_defaults(func=cmd_audio)
    s = au.add_parser("check", help="measure transmit/receive mismatch, S:N and distortion per path")
    s.add_argument("--s1", default=r"C:\RMS Express", help="station 1 install (reads ARDOP_Win TNC.ini)")
    s.add_argument("--s2", default=r"C:\RMS Express 2", help="station 2 install")
    s.add_argument("--port", default="COM3", help="IONOS port; '' to set WGN by hand")
    s.add_argument("--snr", type=int, nargs="+", default=[40], help="IONOS WGN S:N settings to measure at")
    s.add_argument("--seconds", type=float, default=3.0)
    s.add_argument("--loop", action="store_true", help="repeat until Ctrl+C, for live adjustment")
    s.add_argument("--json", help="save results to this file")
    s.set_defaults(func=cmd_audio)

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
