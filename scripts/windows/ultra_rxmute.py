"""Receiver muting during transmit for ULTRA on the single-IONOS bench (19 Nov 2026).

One IONOS in half-duplex mode mixes both stations onto both outputs, so each station hears
its own transmission (the tone check's 1->1 / 2->2 paths). ARDOP, VARA HF, Mercury and Data2G
ignore their own signal; ULTRA 0.6.2 does not: it took its own PONG for a PING and answered
it every 3 s indefinitely, and so never heard the other station. A real transceiver mutes its
receiver while it transmits, which this emulates: it follows each station's ultra_tnc log
("tnc->host: PTT ON" / "PTT OFF") and mutes that station's Windows microphone from PTT ON
until TAIL seconds after PTT OFF (the echo still in the sound card buffers and the IONOS).

Run in the desktop session (hfbench_start_rxmute.ps1). Writes hfbench\\ultra\\rxmute.log.
Unmutes both microphones on start and on exit, and never leaves one muted for more than
MAX_MUTED seconds (a lost PTT OFF).
    python ultra_rxmute.py [--tail 0.6]
"""
import argparse
import os
import time

from pycaw.pycaw import AudioUtilities   # pip install pycaw (Windows Core Audio)

HOME = os.path.join(os.environ["USERPROFILE"], "hfbench", "ultra")
STATIONS = {  # station: (ultra_tnc log, microphone's Windows name)
    1: (os.path.join(HOME, "station1_tnc.log"), "Microphone (C-Media USB Audio Device"),
    2: (os.path.join(HOME, "station2_tnc.log"), "Microphone (3- USB Audio Device)"),
}
MAX_MUTED = 60.0
LOG = os.path.join(HOME, "rxmute.log")


def microphone(name: str):
    """The endpoint volume control of the active capture device whose name starts with name."""
    hits = [d for d in AudioUtilities.GetAllDevices()
            if (d.FriendlyName or "").startswith(name) and str(d.state).endswith("Active")
            and d.id.startswith("{0.0.1.")]
    if len(hits) != 1:
        raise RuntimeError(f"{name!r}: {len(hits)} active capture devices match")
    return hits[0], hits[0].EndpointVolume


def say(msg: str) -> None:
    line = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()) + f".{int(time.time() * 1000) % 1000:03d} UTC {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tail", type=float, default=0.6, help="seconds kept muted after PTT OFF")
    a = ap.parse_args()
    vol, names, files, muted, unmute_at = {}, {}, {}, {}, {}
    for st, (path, name) in STATIONS.items():
        dev, vol[st] = microphone(name)
        names[st] = f"{dev.FriendlyName} {dev.id}"
        vol[st].SetMute(False, None)
        f = open(path, "r", encoding="utf-8", errors="replace")
        f.seek(0, os.SEEK_END)
        files[st], muted[st], unmute_at[st] = f, 0.0, None
    say(f"started: tail {a.tail} s; station 1 mic {names[1]}; station 2 mic {names[2]}")

    def set_mute(st, on, why):
        vol[st].SetMute(bool(on), None)
        muted[st] = time.time() if on else 0.0
        say(f"station {st}: {'MUTE' if on else 'unmute'} ({why})")

    try:
        while True:
            now = time.time()
            for st, f in files.items():
                if os.path.getsize(STATIONS[st][0]) < f.tell():   # log replaced: start over
                    f.seek(0)
                for line in f.readlines():
                    if "tnc->host: PTT ON" in line:
                        unmute_at[st] = None
                        if not muted[st]:
                            set_mute(st, True, "PTT ON")
                    elif "tnc->host: PTT OFF" in line and muted[st]:
                        unmute_at[st] = now + a.tail
                if muted[st] and unmute_at[st] and now >= unmute_at[st]:
                    unmute_at[st] = None
                    set_mute(st, False, f"PTT OFF + {a.tail} s")
                if muted[st] and now - muted[st] > MAX_MUTED:
                    unmute_at[st] = None
                    set_mute(st, False, f"muted over {MAX_MUTED:.0f} s: PTT OFF lost?")
            time.sleep(0.01)
    finally:
        for st in vol:
            vol[st].SetMute(False, None)
        say("stopped: both microphones unmuted")


if __name__ == "__main__":
    main()
