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
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


class Log:
    def __init__(self, path: str):
        self.f = open(path, "a", encoding="utf-8", buffering=1)

    def write(self, port: str, direction: str, text: str) -> None:
        self.f.write(f"{now()} {port} {direction} {text}\n")


async def pump(reader, writer, log: Log, port: str, direction: str, lines: bool) -> None:
    pending = b""
    try:
        while data := await reader.read(65536):
            writer.write(data)
            await writer.drain()
            if lines:
                pending += data
                *done, pending = pending.split(b"\r")
                for ln in done:
                    log.write(port, direction, ln.decode("latin-1").strip())
            else:
                log.write(port, direction, f"{len(data)} bytes")
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


def handler(target: int, log: Log, port: str, lines: bool):
    async def handle(host_r, host_w):
        log.write(port, "--", f"host connected from {host_w.get_extra_info('peername')}")
        try:
            tnc_r, tnc_w = await asyncio.open_connection("127.0.0.1", target)
        except OSError as e:
            log.write(port, "--", f"[cannot reach modem on {target}: {e!r}]")
            host_w.close()
            return
        log.write(port, "--", f"connected to modem port {target}")
        await asyncio.gather(pump(host_r, tnc_w, log, port, "host>modem", lines),
                             pump(tnc_r, host_w, log, port, "modem>host", lines))
    return handle


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--listen", type=int, required=True, help="control port the host connects to (data = +1)")
    ap.add_argument("--target", type=int, required=True, help="modem's control port (data = +1)")
    ap.add_argument("--log", required=True)
    a = ap.parse_args()
    log = Log(a.log)
    log.write("--", "--", f"relay start: {a.listen}/{a.listen + 1} -> {a.target}/{a.target + 1}")
    ctl = await asyncio.start_server(handler(a.target, log, "CTL", True), "127.0.0.1", a.listen)
    dat = await asyncio.start_server(handler(a.target + 1, log, "DAT", False), "127.0.0.1", a.listen + 1)
    print(f"relay {a.listen}/{a.listen + 1} -> {a.target}/{a.target + 1}, logging to {a.log}", flush=True)
    async with ctl, dat:
        await asyncio.gather(ctl.serve_forever(), dat.serve_forever())


if __name__ == "__main__":
    asyncio.run(main())
