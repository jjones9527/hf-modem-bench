"""IONOS SIM USB serial control (manual rev 2.03, section 6 and Fig. 10).

Each command is acknowledged with "OK" or "?" before the next one is sent.
Serial commands mimic turning the knobs. There is no serial "save" command;
EEPROM is written only by pushing the right knob [manual Fig. 9], so
anything set over serial lasts until power-off. At power-on the unit returns
to WGN at S:N +40 with the saved gains.
Observed on firmware 2.03 (10 Nov 2026): the unit ignores lines ending in a
bare CR, although the manual says CR. A line ending in LF or CR+LF works, so
we send CR+LF. Replies end in CR+LF. The baud rate is irrelevant (USB CDC).
"""

from __future__ import annotations

import time
from dataclasses import dataclass


class IonosError(RuntimeError):
    pass


# Commands hfbench never sends unless explicitly allowed:
#  - BUSY switches the unit into its experimental busy-detector mode (manual
#    sections 6 and 8) and is "normally not used with the Simulator".
#  - CH1/CH2 IN/OUT change the audio gains you set by hand and saved to EEPROM;
#    a wrong value can clip a sound card input or blast a monitor earphone.
NEVER = ("BUSY",)
GAIN = ("CH1 IN", "CH2 IN", "CH1 OUT", "CH2 OUT")


def check_allowed(command: str, *, allow_gains: bool = False) -> None:
    name = command.split(":")[0].strip().upper()
    if name in NEVER:
        raise IonosError(f"refusing to send {command!r}: switches the IONOS into busy-detect mode")
    if name in GAIN and not allow_gains:
        raise IonosError(f"refusing to send {command!r}: gain changes need allow_gains / --allow-gains")


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

    def __init__(self, ser, *, retries: int = 1, allow_gains: bool = False):
        self.ser = ser
        self.retries = retries
        self.allow_gains = allow_gains

    @classmethod
    def open(cls, port: str, *, timeout: float = 2.0) -> "Ionos":
        import serial  # pyserial; only needed on the bench machine

        return cls(serial.Serial(port, 115200, timeout=timeout))

    def close(self) -> None:
        self.ser.close()

    def send(self, command: str) -> Ack:
        check_allowed(command, allow_gains=self.allow_gains)
        for attempt in range(self.retries + 1):
            self.ser.reset_input_buffer()
            self.ser.write(command.encode("ascii") + b"\r\n")
            reply = self.ser.readline().decode("ascii", errors="replace").strip()
            if reply:
                return Ack(command, reply)
            time.sleep(0.2 * (attempt + 1))
        raise IonosError(f"no reply from IONOS to {command!r}")

    def apply(self, commands: str | list[str]) -> list[Ack]:
        """Send a command sequence; stop and raise at the first rejected one.
        Every command is checked before anything is sent."""
        cmds = split_commands(commands) if isinstance(commands, str) else commands
        for c in cmds:
            check_allowed(c, allow_gains=self.allow_gains)
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
