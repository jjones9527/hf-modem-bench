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


def _winlink_log_files(where: str) -> list[Path]:
    """Winlink daily session logs from an install folder (<install>/<CALL>/Logs) or
    from a folder of copied logs (e.g. logs/archive/winlink/station1)."""
    p = Path(where)
    files = sorted(p.glob("*/Logs/RMS Express [0-9]*.log")) or sorted(p.glob("RMS Express [0-9]*.log"))
    if not files:
        sys.exit(f"error: no 'RMS Express YYYYMMDD.log' files under {where}")
    return files


def cmd_results(args):
    from . import results as rs

    d = _campaign_dir(args)
    man = mf.build_manifest(mx.read_runsheet(d / RUNSHEET), mf.read_events(d / EVENTS))
    logs = {}
    for st, where in ((1, args.s1), (2, args.s2)):
        lines = []
        for f in _winlink_log_files(where):
            lines += lp.read_text(f)
        logs[st] = lp.parse_winlink_log(lines)
    res = rs.campaign_results(man, logs)
    if args.verify:
        from .bench import install_callsign
        dirs = {st: Path(where) / install_callsign(where) / "Messages" for st, where in ((1, args.s1), (2, args.s2))}
        rs.verify_attachments(res, dirs, args.verify)
    mp, rp = rs.write_csvs(res, Path(args.out) if args.out else d)
    print(rs.format_summary(res))
    print(f"\nwrote {mp} and {rp}")


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


def cmd_messages(args):
    from . import messages as mg

    d = _campaign_dir(args)
    counts = (args.s1_messages if args.s1_messages is not None else args.per_station,
              args.s2_messages if args.s2_messages is not None else args.per_station)
    paths = mg.build_campaign_templates(args.payloads, (args.s1_call, args.s2_call), d / "messages", counts=counts)
    s1, s2 = mg.split_payload_set(args.payloads, counts=counts)
    for st, files in ((1, s1), (2, s2)):
        print(f"station {st}: {paths[st]}  ({len(files)} messages: {', '.join(f.name for f in files) or 'none'})")
    print(f"payload set sha256 = {pl.sha256_set(args.payloads)[0]}")


def cmd_run(args):
    from .bench import BenchRunner, WinlinkAutomation, winlink_session_source

    ionos = None
    if args.port:
        from .ionos import Ionos

        ionos = Ionos.open(args.port)
        if not ionos.probe():
            sys.exit(f"error: no reply from IONOS on {args.port}")
    key = _keypoller()
    d = _campaign_dir(args)
    automation = None
    if args.automate:
        automation = WinlinkAutomation(d, installs=(args.winlink_dir, args.winlink_dir2))

    def between():
        if args.auto_continue is not None:
            import time
            print(f"\nNext run in {args.auto_continue:.0f} s (press q to stop)...")
            t_end = time.time() + args.auto_continue
            while time.time() < t_end:
                if (key() or "").lower() == "q":
                    return False
                time.sleep(0.5)
            return True
        print("\nNext run ready. Press Enter to continue, q then Enter to stop.")
        return input().strip().lower() != "q"

    runner = BenchRunner(d, winlink_session_source(args.winlink_dir),
                         ionos=ionos, automation=automation, key=key, poll_s=args.poll,
                         recover=bool(args.recover and automation is not None))
    try:
        runner.run(max_runs=args.max_runs, wait_between=between)
    finally:
        if ionos is not None:
            ionos.close()


def cmd_recover(args):
    from .bench import WinlinkAutomation

    d = _campaign_dir(args)
    info = WinlinkAutomation(d, installs=(args.winlink_dir, args.winlink_dir2)).recover(args.run_id)
    print(info["note"])


def _noise_summary(audio, results):
    """Each microphone's own noise, if two IONOS S:N settings were measured."""
    by = {}
    for r in results:
        if r.ionos_setting.upper().startswith("WGN:"):
            by[float(r.ionos_setting.split(":")[1])] = r.floor_dbfs_3k
    if len(by) < 2:
        return
    hi, lo = max(by), min(by)
    low = next(r for r in results if r.ionos_setting.upper() == f"WGN:{lo:g}")
    if low.tx_ref_db:
        print(f"transmit vs IONOS reference, from WGN:{lo:g} (least affected by device noise): " +
              "   ".join(f"station {i} {v:+.1f} dB" for i, v in sorted(low.tx_ref_db.items())))
    for st in (1, 2):
        d = audio.device_noise_db(by[hi][st], by[lo][st], hi, lo)
        txt = f"{-d:.0f} dB below the IONOS reference" if d is not None else "too low to measure"
        print(f"station {st} microphone's own noise: {txt}")


IONOS_RESET = "BANDWIDTH:3000; MULTIPATH:2; OFFSET:0; FADE DEPTH:0; FADE FREQ:0; FM DEVIATION:0; FM RATE:0"


def _asdict_qam(r):
    from dataclasses import asdict as _asdict
    d = _asdict(r)
    d.pop("raw", None)
    return d


def _save_raw_qam(path, results):
    """All recordings as float32 arrays in one .npz, keyed '<setting>|<level> <path>'."""
    import numpy as np
    arrs = {}
    for r in results:
        for k, (x, fs_in, fs_out) in r.raw.items():
            arrs[f"{r.ionos_setting}|{k}"] = np.asarray(x, dtype=np.float32)
            arrs[f"{r.ionos_setting}|{k}|fs"] = np.array([fs_in, fs_out])
    np.savez_compressed(path, **arrs)


def _listen_per_run(audio, series, ptt, campaign: Path, energy_sender: int | None) -> None:
    """Measured S:N for every run of a campaign, each over its own time window and
    against its own IONOS setting (a sweep mixes settings in one recording).

    Transmissions are found from the audio energy (any modem); in a one-way run the
    long bursts are the sender's data. Where ARDOP's PTT log is in the recording it
    is shown as a cross-check. ARDOP's PTT record can have gaps (oneway28r-0003,
    around midnight, made its noise floor read 18 dB high), so energy is the default."""
    from datetime import datetime

    man = mf.build_manifest(mx.read_runsheet(campaign / RUNSHEET), mf.read_events(campaign / EVENTS))
    print(f"{'run':<22} {'setting':>7} {'payload':<10} {'data S:N (n)':>15} {'control S:N':>12} {'ARDOP-PTT data':>15}")
    for r in man:
        if not r.get("end_utc"):
            continue
        a = datetime.fromisoformat(r["start_utc"]).timestamp()
        b = datetime.fromisoformat(r["end_utc"]).timestamp()
        ser = {k: [x for x in v if a <= x[0] < b] for k, v in series.items()}
        if not any(ser.values()):
            print(f"{r['run_id']:<22} {r['snr_db']:>7} {r['payload_file']:<10} {'not recorded':>15}")
            continue
        sender = energy_sender or 2
        e = audio.analyze_listen(ser, audio.ptt_one_way(audio.bursts_from_energy(ser.get(3 - sender, [])),
                                                        sender=sender), float(r["snr_db"]))
        def pick(res, kind, snd=None):
            ds = [d for d in res["directions"] if d["kind"] == kind and (snd is None or d["sender"] == snd)]
            return max(ds, key=lambda d: d["n"]) if ds else None
        cell = lambda d: f"{d['snr_median_db']:.1f} dB ({d['n']})" if d else "none"
        p = {k: [x for x in v if a <= x[0] and x[1] < b] for k, v in ptt.items()}
        cross = ""
        if any(p.values()):
            d = pick(audio.analyze_listen(ser, p, float(r["snr_db"])), "data", sender)
            cross = cell(d)
        ctl = pick(e, "control")
        ctl_txt = f"{ctl['snr_median_db']:.1f} dB" if ctl else "none"
        print(f"{r['run_id']:<22} {r['snr_db']:>7} {r['payload_file']:<10} {cell(pick(e, 'data', sender)):>15} "
              f"{ctl_txt:>12} {cross:>15}")


def cmd_audio(args):
    import json

    from . import audio

    if args.acmd == "report":
        from dataclasses import asdict as _asdict
        saved = json.loads(Path(args.json_in).read_text())
        res = [audio.evaluate(r["ionos_setting"], r["floor_dbfs_3k"], r["paths"], r.get("devices"))
               for r in saved]
        for r in res:
            print(audio.format_result(r) + "\n")
        _noise_summary(audio, res)
        return

    if args.acmd in ("listen", "listen-report"):
        from . import logparse as lp

        if args.acmd == "listen":
            stations = (audio.station_from_ardop_ini(1, args.s1), audio.station_from_ardop_ini(2, args.s2))
            series = audio.record_band_power(stations, args.minutes * 60)
            t0 = min(t for v in series.values() for t, _ in v) if any(series.values()) else 0
            t1 = max(t for v in series.values() for t, _ in v) if any(series.values()) else 0
            ptt = {}
            for st, d in ((1, args.s1), (2, args.s2)):
                logs = sorted(Path(d, "Logs").glob("ARDOP_WinTNC_Debug_*.log"))[-2:]
                ivs = [iv for p in logs for iv in lp.parse_ardop_ptt(p)]
                ptt[st] = [(a.timestamp(), b.timestamp()) for a, b in ivs
                           if t0 <= a.timestamp() <= t1]
            saved = {"setting_snr": args.setting, "series": {str(k): v for k, v in series.items()},
                     "ptt": {str(k): v for k, v in ptt.items()}}
            if args.json:
                Path(args.json).write_text(json.dumps(saved))
        else:
            saved = {"series": {}, "ptt": {}, "setting_snr": None}
            for f in args.json_in:                 # several back-to-back recordings are merged
                one = json.loads(Path(f).read_text())
                for key in ("series", "ptt"):
                    for k, v in one[key].items():
                        saved[key].setdefault(k, []).extend(v)
                saved["setting_snr"] = saved["setting_snr"] if saved["setting_snr"] is not None else one.get("setting_snr")
        series = {int(k): sorted(tuple(x) for x in v) for k, v in saved["series"].items()}
        ptt = {int(k): sorted(tuple(x) for x in v) for k, v in saved["ptt"].items()}
        if args.acmd == "listen-report" and args.runs:
            _listen_per_run(audio, series, ptt, Path(args.runs), args.energy)
            return
        if args.acmd == "listen-report" and (args.t_from or args.t_to):
            from datetime import datetime
            a = datetime.fromisoformat(args.t_from).timestamp() if args.t_from else float("-inf")
            b = datetime.fromisoformat(args.t_to).timestamp() if args.t_to else float("inf")
            series = {k: [x for x in v if a <= x[0] < b] for k, v in series.items()}
            ptt = {k: [x for x in v if a <= x[0] and x[1] < b] for k, v in ptt.items()}
        if args.acmd == "listen-report" and args.energy:
            mic = 3 - args.energy
            ptt = audio.ptt_one_way(audio.bursts_from_energy(series.get(mic, [])), sender=args.energy)
            print(f"(transmissions found from the audio energy; data bursts assigned to station {args.energy})")
        setting = args.setting if getattr(args, "setting", None) is not None else saved.get("setting_snr")
        print(f"bursts keyed: station 1 {len(ptt.get(1, []))}, station 2 {len(ptt.get(2, []))}; "
              f"blocks recorded: {', '.join(f'mic {k} {len(v)}' for k, v in sorted(series.items()))}")
        print(audio.format_listen(audio.analyze_listen(series, ptt, setting)))
        if args.acmd == "listen" and args.json:
            print(f"\nsaved {args.json}")
        return

    if args.acmd == "qam":
        from . import qamtest

        stations = (audio.station_from_ardop_ini(1, args.s1), audio.station_from_ardop_ini(2, args.s2))
        for s in stations:
            print(f"station {s.number}: play '{s.playback}', record '{s.capture}'")
        io = None
        if args.port:
            from .ionos import Ionos

            io = Ionos.open(args.port)
        saved = []
        try:
            for snr in args.snr:
                setting = f"WGN:{snr}"
                if io is not None:
                    io.apply(f"{IONOS_RESET}; {setting}")
                    print(f"\nIONOS set to WGN, S:N {snr} dB (add-ons off)")
                else:
                    print(f"\nSet the IONOS to WGN, S:N {snr} dB by hand (no --port given).")
                r = qamtest.run_qam(stations, n_sym=args.symbols, ionos_setting=setting if io else "")
                print(qamtest.format_qam(r))
                saved.append(r)
        finally:
            if io is not None:
                io.close()
        if args.json:
            Path(args.json).write_text(json.dumps([_asdict_qam(r) for r in saved], indent=1))
            print(f"\nsaved {args.json}")
        if args.raw:
            _save_raw_qam(args.raw, saved)
            print(f"saved {args.raw}")
        return

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
    _noise_summary(audio, results)
    if args.json:
        from dataclasses import asdict
        Path(args.json).write_text(json.dumps([asdict(r) for r in results], indent=2, default=str))
        print(f"\nsaved {args.json}")


def cmd_payload_make(args):
    digest = pl.make_payload(args.path, args.bytes, args.seed)
    print(f"{args.path}: {args.bytes} bytes, seed {args.seed}\n"
          f"sha256 = {digest}\nzlib ratio = {pl.compress_ratio(args.path):.3f}")


def cmd_payload_derive(args):
    digest, per = pl.derive_prefix_set(args.src, args.dst, args.bytes)
    print(f"{args.dst}: first {args.bytes} bytes of each of {len(per)} files in {args.src}\nset sha256 = {digest}")


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

    s = with_dir(sub.add_parser("results", help="per-message and per-run results from both stations' Winlink logs"))
    s.add_argument("--s1", default=r"C:\RMS Express", help="station 1 install, or a folder of its copied logs")
    s.add_argument("--s2", default=r"C:\RMS Express 2", help="station 2 install, or a folder of its copied logs")
    s.add_argument("-o", "--out", help="output folder for messages.csv and runs.csv (default: the campaign folder)")
    s.add_argument("--verify", metavar="PAYLOAD_DIR",
                   help="compare every delivered attachment (receiver's <MID>.mime) with this payload set; "
                        "needs --s1/--s2 to be the Winlink installs")
    s.set_defaults(func=cmd_results)

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
    s.add_argument("--automate", action="store_true",
                   help="queue messages by import and start/abort sessions in Winlink Express (desktop session)")
    s.add_argument("--winlink-dir2", default=r"C:\RMS Express 2", help="station 2 Winlink install")
    s.add_argument("--auto-continue", type=float, metavar="SECONDS",
                   help="start the next run after this pause instead of waiting for Enter")
    s.add_argument("--recover", action="store_true",
                   help="with --automate: after a failed run, clear both Outboxes, restart both Winlink "
                        "Express instances and their Ardop P2P sessions, then continue")
    s.set_defaults(func=cmd_run)

    s = with_dir(sub.add_parser("recover", help="reset the bench now as after a failed run (desktop session)"))
    s.add_argument("run_id", help="run the reset follows (partials go to quarantine/<run_id>)")
    s.add_argument("--winlink-dir", default=r"C:\RMS Express")
    s.add_argument("--winlink-dir2", default=r"C:\RMS Express 2")
    s.set_defaults(func=cmd_recover)

    s = with_dir(sub.add_parser("messages", help="build the campaign's message templates (once)"))
    s.add_argument("action", choices=["build"])
    s.add_argument("--payloads", default="payloads/Text_50KB")
    s.add_argument("--s1-call", required=True, help="station 1 callsign (sends the first half of the set)")
    s.add_argument("--s2-call", required=True)
    s.add_argument("--per-station", type=int, default=5, help="messages each station sends (default 5 + 5)")
    s.add_argument("--s1-messages", type=int, help="station 1's count, overriding --per-station (e.g. 10)")
    s.add_argument("--s2-messages", type=int, help="station 2's count, overriding --per-station (0 = one-way)")
    s.set_defaults(func=cmd_messages)

    au = sub.add_parser("audio", help="tone-based level check (run on the Windows desktop)").add_subparsers(dest="acmd", required=True)
    s = au.add_parser("devices", help="list sound devices")
    s.set_defaults(func=cmd_audio)
    s = au.add_parser("listen", help="measure true per-direction S:N of real modem traffic (ARDOP)")
    s.add_argument("--minutes", type=float, default=10.0, help="how long to record (Ctrl+C stops early)")
    s.add_argument("--setting", type=float, help="IONOS WGN S:N setting during the session, for the offset")
    s.add_argument("--s1", default=r"C:\RMS Express")
    s.add_argument("--s2", default=r"C:\RMS Express 2")
    s.add_argument("--json", help="save the recording summary (band power + PTT) for re-analysis")
    s.set_defaults(func=cmd_audio)
    s = au.add_parser("listen-report", help="re-analyze saved listen --json file(s)")
    s.add_argument("json_in", nargs="+", help="one or more listen JSON files (back-to-back recordings are merged)")
    s.add_argument("--setting", type=float)
    s.add_argument("--from", dest="t_from", help="only from this time (ISO, e.g. 2026-11-13T16:28:00+00:00)")
    s.add_argument("--to", dest="t_to", help="only up to this time (ISO)")
    s.add_argument("--energy", type=int, choices=(1, 2), metavar="SENDER",
                   help="find transmissions from the audio instead of ARDOP's log (any modem); "
                        "one-way runs: long bursts are SENDER's data")
    s.add_argument("--runs", metavar="CAMPAIGN_DIR",
                   help="one line per run of this campaign, each over its own time and IONOS setting")
    s.set_defaults(func=cmd_audio)
    s = au.add_parser("qam", help="16QAM path test: MER of an ARDOP-like signal on all four paths")
    s.add_argument("--s1", default=r"C:\RMS Express", help="station 1 install (reads ARDOP_Win TNC.ini)")
    s.add_argument("--s2", default=r"C:\RMS Express 2", help="station 2 install")
    s.add_argument("--port", default="COM3", help="IONOS port; '' to set WGN by hand")
    s.add_argument("--snr", type=int, nargs="+", default=[40, 25],
                   help="IONOS WGN settings (default 40 = near noise-free, 25 = as wgn25a)")
    s.add_argument("--symbols", type=int, default=800, help="16QAM symbols per transmission (100 per second)")
    s.add_argument("--json", help="save results to this file")
    s.add_argument("--raw", help="save every recording to this .npz, for offline analysis")
    s.set_defaults(func=cmd_audio)
    s = au.add_parser("report", help="re-analyze a saved --json result (plays nothing)")
    s.add_argument("json_in")
    s.set_defaults(func=cmd_audio)
    s = au.add_parser("check", help="measure transmit/receive mismatch, S:N and distortion per path")
    s.add_argument("--s1", default=r"C:\RMS Express", help="station 1 install (reads ARDOP_Win TNC.ini)")
    s.add_argument("--s2", default=r"C:\RMS Express 2", help="station 2 install")
    s.add_argument("--port", default="COM3", help="IONOS port; '' to set WGN by hand")
    s.add_argument("--snr", type=int, nargs="+", default=[20],
                   help="IONOS WGN S:N settings to measure at (default 20: high settings bias the "
                        "transmit offsets once device noise is within ~10 dB; add 40 to estimate device noise)")
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
    s = pay.add_parser("derive", help="smaller set from the first N bytes of each file (Text_5KB from Text_50KB)")
    s.add_argument("src")
    s.add_argument("dst")
    s.add_argument("--bytes", type=int, required=True)
    s.set_defaults(func=cmd_payload_derive)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except (mx.MatrixError, mf.ManifestError) as e:
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    main()
