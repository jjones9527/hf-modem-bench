"""IONOS SIM USB serial control (manual rev 2.03, section 6 and Fig. 10).

Each command is acknowledged with "OK" or "?" before the next one is sent.
Observed on firmware 2.03 (10 Nov 2026): the unit ignores lines ending in a
bare CR, although the manual says CR. A line ending in LF or CR+LF works, so
we send CR+LF. Replies end in CR+LF. The baud rate is irrelevant (USB CDC).
"""

from __future__ import annotations

import time
from dataclasses import dataclass


class IonosError(RuntimeError):
    pass


@dataclass
class Ack:
    command: str
    reply: str

    @property
    def ok(self) -> bool:
        return self.reply.upper() == "OK"


def split_commands(commands: str) -> list[str]:
    """'A:1; B:2' -> ['A:1', 'B:2'] (the run-sheet ionos_commands format)."""
    return [c.strip() for c in commands.split(";") if c.strip()]


class Ionos:
    """Thin client around a pyserial-like object (write/readline/reset_input_buffer)."""

    def __init__(self, ser, *, retries: int = 1):
        self.ser = ser
        self.retries = retries

    @classmethod
    def open(cls, port: str, *, timeout: float = 2.0) -> "Ionos":
        import serial  # pyserial; only needed on the bench machine

        return cls(serial.Serial(port, 115200, timeout=timeout))

    def close(self) -> None:
        self.ser.close()

    def send(self, command: str) -> Ack:
        for attempt in range(self.retries + 1):
            self.ser.reset_input_buffer()
            self.ser.write(command.encode("ascii") + b"\r\n")
            reply = self.ser.readline().decode("ascii", errors="replace").strip()
            if reply:
                return Ack(command, reply)
            time.sleep(0.2 * (attempt + 1))
        raise IonosError(f"no reply from IONOS to {command!r}")

    def apply(self, commands: str | list[str]) -> list[Ack]:
        """Send a command sequence; stop and raise at the first rejected one."""
        cmds = split_commands(commands) if isinstance(commands, str) else commands
        acks = []
        for c in cmds:
            a = self.send(c)
            acks.append(a)
            if not a.ok:
                raise IonosError(f"IONOS rejected {c!r} (reply {a.reply!r}); "
                                 f"accepted so far: {[x.command for x in acks[:-1]]}")
        return acks

    def probe(self) -> bool:
        """True if the unit answers. Sends an invalid command, which changes nothing."""
        return self.send("HFBENCH_PROBE").reply == "?"
