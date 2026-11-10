"""Test matrix definition (TOML) -> ordered run sheet (CSV).

The matrix describes *what* to test; the run sheet is the concrete, ordered
list of runs the bench operator works through. Run IDs are assigned after
ordering so the sheet reads top to bottom.

Channel settings are modelled on the Teensy IONOS simulator (firmware 2.03):
fixed Watterson presets, S:N in the simulator's 3 kHz bandwidth, and WGN-only
add-ons (offset, flat fade, FM drift). Each run carries the exact IONOS serial
command sequence that sets it up, so settings are explicit and never inherited
from the previous run.
"""

from __future__ import annotations

import csv
import itertools
import random
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

# IONOS SIM rev 2.03 presets: name -> (Doppler spread Hz, differential delay ms).
# Source: IONOS manual rev 2.03, specifications page. MPG/MPM/MPP match CCIR 520-2
# Good/Moderate/Poor (= ITU-R F.1487 mid-latitude quiet/moderate/disturbed).
IONOS_PRESETS = {
    "WGN": (0.0, 0.0),
    "MPG": (0.1, 0.5),
    "MPM": (0.5, 1.0),
    "MPP": (1.0, 2.0),
    "MPD": (2.0, 4.0),
}
MULTIPATH_PRESETS = {"MPG", "MPM", "MPP", "MPD"}

_LOG_RATE = {0, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20}
_LOG_DEV = {0, 1, 2, 5, 10, 20, 50, 100, 200}

# WGN-only add-ons: command -> validator. All are reset to 0 at the start of
# every run unless the impairment sets them.
WGN_ADDONS = {
    "OFFSET": lambda v: -200 <= v <= 200 and v % 10 == 0,
    "FADE DEPTH": lambda v: 0 <= v <= 40 and float(v).is_integer(),
    "FADE FREQ": lambda v: v in _LOG_RATE,
    "FM DEVIATION": lambda v: v in _LOG_DEV,
    "FM RATE": lambda v: v in _LOG_RATE,
}

RUNSHEET_FIELDS = [
    "run_id",
    "campaign",
    "stage",
    "seq",
    "modem",
    "modem_version",
    "modem_bandwidth_hz",
    "profile",
    "doppler_hz",
    "delay_ms",
    "multipaths",
    "sim_bandwidth_hz",
    "snr_db",
    "impairment",
    "impairment_notes",
    "ionos_commands",
    "replicate",
    "payload_file",
    "payload_bytes",
    "payload_sha256",
    "payload_messages",
    "abort_minutes",
    "abort_retries",
]


class MatrixError(ValueError):
    pass


@dataclass(frozen=True)
class Modem:
    name: str
    version: str
    bandwidth_hz: int | None = None


@dataclass(frozen=True)
class Impairment:
    name: str
    settings: tuple[tuple[str, float], ...] = ()  # IONOS add-on commands
    notes: str = ""  # free text, e.g. "SNR step 20->5 dB at 3 min via serial"


@dataclass
class Matrix:
    campaign: str
    stage: str
    replicates: int
    snr_db: list[int]
    profiles: list[str]
    modems: list[Modem]
    impairments: list[Impairment]
    payload_file: str
    payload_bytes: int
    payload_sha256: str
    payload_messages: int = 1
    sim_bandwidth_hz: int = 3000
    multipaths: int = 2
    order: str = "blocked-random"
    order_seed: int = 0
    abort_minutes: int = 30
    abort_retries: int = 3
    # Optional per-profile SNR override for targeted (knee-refinement) passes.
    snr_by_profile: dict[str, list[int]] = field(default_factory=dict)


def _req(table: dict, key: str, where: str):
    if key not in table:
        raise MatrixError(f"missing '{key}' in [{where}]")
    return table[key]


def _snr(x) -> int:
    if not float(x).is_integer():
        raise MatrixError(f"IONOS S:N is set in 1 dB steps; got {x}")
    return int(x)


def load_matrix(path: str | Path) -> Matrix:
    with open(path, "rb") as f:
        doc = tomllib.load(f)

    c = _req(doc, "campaign", "top level")
    p = _req(doc, "payload", "top level")
    sim = doc.get("ionos", {})

    modems = [
        Modem(_req(m, "name", "modems"), str(_req(m, "version", "modems")), m.get("bandwidth_hz"))
        for m in _req(doc, "modems", "top level")
    ]
    impairments = []
    for x in doc.get("impairments", [{"name": "none"}]):
        settings = tuple((k.upper(), v) for k, v in x.get("settings", {}).items())
        impairments.append(Impairment(_req(x, "name", "impairments"), settings, str(x.get("notes", ""))))

    m = Matrix(
        campaign=_req(c, "name", "campaign"),
        stage=c.get("stage", "coarse"),
        replicates=int(c.get("replicates", 3)),
        snr_db=[_snr(s) for s in _req(c, "snr_db", "campaign")],
        profiles=[str(s).upper() for s in _req(c, "profiles", "campaign")],
        modems=modems,
        impairments=impairments,
        payload_file=_req(p, "file", "payload"),
        payload_bytes=int(_req(p, "bytes", "payload")),
        payload_sha256=_req(p, "sha256", "payload").lower(),
        payload_messages=int(p.get("messages", 1)),
        sim_bandwidth_hz=int(sim.get("bandwidth_hz", 3000)),
        multipaths=int(sim.get("multipaths", 2)),
        order=c.get("order", "blocked-random"),
        order_seed=int(c.get("order_seed", 0)),
        abort_minutes=int(c.get("abort_minutes", 30)),
        abort_retries=int(c.get("abort_retries", 3)),
        snr_by_profile={k.upper(): [_snr(s) for s in v] for k, v in c.get("snr_by_profile", {}).items()},
    )
    validate(m)
    return m


def validate(m: Matrix) -> None:
    if m.replicates < 1:
        raise MatrixError("replicates must be >= 1")
    if m.order not in ("blocked-random", "sequential"):
        raise MatrixError(f"unknown order '{m.order}' (use blocked-random or sequential)")
    if m.payload_messages < 1:
        raise MatrixError("payload.messages must be >= 1")
    if len(m.payload_sha256) != 64:
        raise MatrixError("payload.sha256 must be a 64-char hex SHA-256 (use `hfbench payload hash`)")
    if m.sim_bandwidth_hz not in (3000, 6000):
        raise MatrixError("ionos.bandwidth_hz must be 3000 or 6000")
    if m.multipaths not in (2, 4):
        raise MatrixError("ionos.multipaths must be 2 or 4")
    bad = [p for p in m.profiles if p not in IONOS_PRESETS]
    if bad:
        raise MatrixError(f"unknown IONOS profile(s) {bad}; available: {sorted(IONOS_PRESETS)}")
    for snrs in [m.snr_db, *m.snr_by_profile.values()]:
        if any(not -40 <= s <= 40 for s in snrs):
            raise MatrixError("IONOS S:N range is -40 to +40 dB")
    unknown = set(m.snr_by_profile) - set(m.profiles)
    if unknown:
        raise MatrixError(f"snr_by_profile names profiles not in campaign.profiles: {sorted(unknown)}")
    for kind, names in (("modem", [x.name for x in m.modems]), ("profile", m.profiles),
                        ("impairment", [x.name for x in m.impairments])):
        if len(set(names)) != len(names):
            raise MatrixError(f"duplicate {kind} names: {names}")
    for imp in m.impairments:
        for cmd, val in imp.settings:
            if cmd not in WGN_ADDONS:
                raise MatrixError(f"impairment {imp.name!r}: unknown IONOS setting {cmd!r}; "
                                  f"supported: {sorted(WGN_ADDONS)}")
            if not WGN_ADDONS[cmd](val):
                raise MatrixError(f"impairment {imp.name!r}: {cmd} value {val} out of IONOS range")
        if imp.settings and any(p in MULTIPATH_PRESETS for p in m.profiles):
            # IONOS ignores offset/fade/FM on multipath modes ("no FM or Offset!").
            raise MatrixError(f"impairment {imp.name!r} uses WGN-only settings but the matrix "
                              f"includes multipath profiles; put it in a WGN-only matrix")


def _fmt_num(x) -> str:
    return str(int(x)) if float(x).is_integer() else str(x)


def ionos_commands(m: Matrix, profile: str, snr: int, imp: Impairment) -> str:
    """Serial command sequence (manual: Fig. 10) that fully sets up one run.

    Add-ons are reset explicitly so nothing carries over from the previous run.
    The mode command goes last because it also sets S:N.
    """
    addons = {k: 0 for k in WGN_ADDONS}
    addons.update(dict(imp.settings))
    cmds = [f"BANDWIDTH:{m.sim_bandwidth_hz}", f"MULTIPATH:{m.multipaths}"]
    cmds += [f"{k}:{_fmt_num(v)}" for k, v in addons.items()]
    cmds.append(f"{profile}:{snr}")
    return "; ".join(cmds)


def build_runs(m: Matrix) -> list[dict]:
    """Expand the matrix into ordered run rows with run IDs assigned."""
    points = []
    for modem in m.modems:
        for prof, imp in itertools.product(m.profiles, m.impairments):
            for snr in m.snr_by_profile.get(prof, m.snr_db):
                for rep in range(1, m.replicates + 1):
                    points.append((modem, prof, snr, imp, rep))

    if m.order == "blocked-random":
        # Block by modem (switching modems is slow and error-prone), but
        # randomise both the modem order and the order within each block so
        # slow drift (temperature, levels) doesn't line up with SNR or profile.
        rng = random.Random(m.order_seed)
        modem_order = list(m.modems)
        rng.shuffle(modem_order)
        ordered = []
        for modem in modem_order:
            block = [p for p in points if p[0] == modem]
            rng.shuffle(block)
            ordered.extend(block)
        points = ordered

    rows = []
    for seq, (modem, prof, snr, imp, rep) in enumerate(points, start=1):
        doppler, delay = IONOS_PRESETS[prof]
        rows.append({
            "run_id": f"{m.campaign}-{seq:04d}",
            "campaign": m.campaign,
            "stage": m.stage,
            "seq": seq,
            "modem": modem.name,
            "modem_version": modem.version,
            "modem_bandwidth_hz": modem.bandwidth_hz if modem.bandwidth_hz is not None else "",
            "profile": prof,
            "doppler_hz": doppler,
            "delay_ms": delay,
            "multipaths": m.multipaths if prof in MULTIPATH_PRESETS else 1,
            "sim_bandwidth_hz": m.sim_bandwidth_hz,
            "snr_db": snr,
            "impairment": imp.name,
            "impairment_notes": imp.notes,
            "ionos_commands": ionos_commands(m, prof, snr, imp),
            "replicate": rep,
            "payload_file": m.payload_file,
            "payload_bytes": m.payload_bytes,
            "payload_sha256": m.payload_sha256,
            "payload_messages": m.payload_messages,
            "abort_minutes": m.abort_minutes,
            "abort_retries": m.abort_retries,
        })
    return rows


def write_runsheet(rows: list[dict], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=RUNSHEET_FIELDS)
        w.writeheader()
        w.writerows(rows)


def read_runsheet(path: str | Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))
