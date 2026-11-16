"""Logging relay for a VARA-style TNC host interface (control + data port pair).

Sits between a host (Winlink Express) and a modem (Mercury, Data2G, VARA) and passes
every byte through unchanged, logging what crosses:
  control port: every CR-terminated line, both directions, UTC time to the ms
  data port:    each chunk's size and direction (contents are not logged)

    python vara_relay.py --listen 8320 --target 8310 --log relay.log

The host connects to --listen (control) and --listen+1 (data); the relay connects to
--target and --target+1 on 127.0.0.1. Ctrl+C or closing the window stops it. Used on
15 Nov 2026 to see whether Mercury's BUFFER reports reach Winlink Express, whose
P2P session gives up after 5 min of "inactivity" during long sends.

--hold-timeout-disconnect: Winlink Express sends DISCONNECT when it has written
nothing to the data port for 5 min, even while the modem is still sending the
message it was given (its P2P inactivity timer). VARA and Mercury then end the
link once the message is through, before the receiver's receipt can come back. With
this option the relay answers such a DISCONNECT with OK itself and does not pass it
on, when the host's last data-port write was at least --idle-s seconds ago. Any
other DISCONNECT (the real end of a session comes seconds after the host's last
write, its FQ) is passed through; Abort sends ABORT, which is never held.
(15 Nov: the first version also required the modem's BUFFER to be above zero, and
let through a timer DISCONNECT that came 0.6 s after BUFFER 0, before the receipt:
sweep-mercury-50k-0003.)
This changes the system under test; record it with every result.
"""
from __future__ import annotations

import argparse
import asyncio
import re
import time
from datetime import datetime, timezone


class State:
    """What the relay knows about the link, for --hold-timeout-disconnect."""
    def __init__(self, hold: bool, idle_s: float):
        self.hold, self.idle_s = hold, idle_s
        self.last_host_data = time.monotonic()
        self.buffer = 0


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


class Log:
    def __init__(self, path: str):
        self.f = open(path, "a", encoding="utf-8", buffering=1)

    def write(self, port: str, direction: str, text: str) -> None:
        self.f.write(f"{now()} {port} {direction} {text}\n")


async def pump(reader, writer, log: Log, port: str, direction: str, lines: bool,
               st: State, back=None) -> None:
    """back: the writer towards the host, for answering a held DISCONNECT."""
    pending = b""
    try:
        while data := await reader.read(65536):
            if not lines:
                if direction == "host>modem":
                    st.last_host_data = time.monotonic()
                writer.write(data)
                await writer.drain()
                log.write(port, direction, f"{len(data)} bytes")
                continue
            pending += data
            *done, pending = pending.split(b"\r")
            for raw in done:
                ln = raw.decode("latin-1").strip()
                if direction == "modem>host" and (m := re.match(r"BUFFER (\d+)$", ln)):
                    st.buffer = int(m.group(1))
                idle = time.monotonic() - st.last_host_data
                if (direction == "host>modem" and ln == "DISCONNECT" and st.hold
                        and idle >= st.idle_s and back is not None):
                    back.write(b"OK\r")
                    await back.drain()
                    log.write(port, direction, f"DISCONNECT [HELD: host idle {idle:.0f} s, modem BUFFER "
                                               f"{st.buffer}; answered OK, not passed on]")
                    continue
                writer.write(raw + b"\r")
                await writer.drain()
                log.write(port, direction, ln)
    except (ConnectionError, OSError) as e:
        log.write(port, direction, f"[error {e!r}]")
    finally:
        if pending:
            log.write(port, direction, pending.decode("latin-1").strip() + " [no CR]")
        log.write(port, direction, "[closed]")
        try:
            writer.close()
        except Exception:
            pass


def handler(target: int, log: Log, port: str, lines: bool, st: State):
    async def handle(host_r, host_w):
        log.write(port, "--", f"host connected from {host_w.get_extra_info('peername')}")
        try:
            tnc_r, tnc_w = await asyncio.open_connection("127.0.0.1", target)
        except OSError as e:
            log.write(port, "--", f"[cannot reach modem on {target}: {e!r}]")
            host_w.close()
            return
        log.write(port, "--", f"connected to modem port {target}")
        await asyncio.gather(pump(host_r, tnc_w, log, port, "host>modem", lines, st, back=host_w),
                             pump(tnc_r, host_w, log, port, "modem>host", lines, st))
    return handle


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--listen", type=int, required=True, help="control port the host connects to (data = +1)")
    ap.add_argument("--target", type=int, required=True, help="modem's control port (data = +1)")
    ap.add_argument("--log", required=True)
    ap.add_argument("--hold-timeout-disconnect", action="store_true")
    ap.add_argument("--idle-s", type=float, default=240.0,
                    help="host data-port silence that marks a DISCONNECT as the 5-min timer's (default 240)")
    a = ap.parse_args()
    log = Log(a.log)
    st = State(a.hold_timeout_disconnect, a.idle_s)
    log.write("--", "--", f"relay start: {a.listen}/{a.listen + 1} -> {a.target}/{a.target + 1}"
                          + (f", holding timer DISCONNECTs (idle >= {a.idle_s:.0f} s)" if st.hold else ""))
    ctl = await asyncio.start_server(handler(a.target, log, "CTL", True, st), "127.0.0.1", a.listen)
    dat = await asyncio.start_server(handler(a.target + 1, log, "DAT", False, st), "127.0.0.1", a.listen + 1)
    print(f"relay {a.listen}/{a.listen + 1} -> {a.target}/{a.target + 1}, logging to {a.log}", flush=True)
    async with ctl, dat:
        await asyncio.gather(ctl.serve_forever(), dat.serve_forever())


if __name__ == "__main__":
    asyncio.run(main())
