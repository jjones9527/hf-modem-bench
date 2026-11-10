"""Test matrix definition (TOML) -> ordered run sheet (CSV).

The matrix describes *what* to test; the run sheet is the concrete, ordered
list of runs the bench operator works through. Run IDs are assigned after
ordering so the sheet reads top to bottom.
"""

from __future__ import annotations

import csv
import itertools
import random
import tomllib
from dataclasses import dataclass, field, asdict
from pathlib import Path

RUNSHEET_FIELDS = [
    "run_id",
    "campaign",
    "stage",
    "seq",
    "modem",
    "modem_version",
    "modem_bandwidth_hz",
    "profile",
    "delay_ms",
    "doppler_hz",
    "snr_db",
    "impairment",
    "impairment_params",
    "replicate",
    "channel_seed",
    "payload_file",
    "payload_bytes",
    "payload_sha256",
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
class Profile:
    name: str
    delay_ms: float
    doppler_hz: float


@dataclass(frozen=True)
class Impairment:
    name: str
    params: str = ""  # free text, e.g. "offset_hz=+30"; recorded verbatim


@dataclass
class Matrix:
    campaign: str
    stage: str
    replicates: int
    snr_db: list[float]
    modems: list[Modem]
    profiles: list[Profile]
    impairments: list[Impairment]
    payload_file: str
    payload_bytes: int
    payload_sha256: str
    order: str = "blocked-random"
    order_seed: int = 0
    seed_mode: str = "fixed"
    channel_seed: int | None = None
    abort_minutes: int = 30
    abort_retries: int = 3
    # Optional per-profile SNR override for targeted (knee-refinement) passes.
    snr_by_profile: dict[str, list[float]] = field(default_factory=dict)


def _req(table: dict, key: str, where: str):
    if key not in table:
        raise MatrixError(f"missing '{key}' in [{where}]")
    return table[key]


def load_matrix(path: str | Path) -> Matrix:
    with open(path, "rb") as f:
        doc = tomllib.load(f)

    c = _req(doc, "campaign", "top level")
    p = _req(doc, "payload", "top level")
    ch = doc.get("channel", {})

    modems = [
        Modem(_req(m, "name", "modems"), str(_req(m, "version", "modems")), m.get("bandwidth_hz"))
        for m in _req(doc, "modems", "top level")
    ]
    profiles = [
        Profile(_req(x, "name", "profiles"), float(x.get("delay_ms", 0)), float(x.get("doppler_hz", 0)))
        for x in _req(doc, "profiles", "top level")
    ]
    impairments = [
        Impairment(_req(x, "name", "impairments"), str(x.get("params", "")))
        for x in doc.get("impairments", [{"name": "none"}])
    ]

    m = Matrix(
        campaign=_req(c, "name", "campaign"),
        stage=c.get("stage", "coarse"),
        replicates=int(c.get("replicates", 3)),
        snr_db=[float(s) for s in _req(c, "snr_db", "campaign")],
        modems=modems,
        profiles=profiles,
        impairments=impairments,
        payload_file=_req(p, "file", "payload"),
        payload_bytes=int(_req(p, "bytes", "payload")),
        payload_sha256=_req(p, "sha256", "payload").lower(),
        order=c.get("order", "blocked-random"),
        order_seed=int(c.get("order_seed", 0)),
        seed_mode=ch.get("seed_mode", "fixed"),
        channel_seed=ch.get("seed"),
        abort_minutes=int(c.get("abort_minutes", 30)),
        abort_retries=int(c.get("abort_retries", 3)),
        snr_by_profile={k: [float(s) for s in v] for k, v in c.get("snr_by_profile", {}).items()},
    )
    validate(m)
    return m


def validate(m: Matrix) -> None:
    if m.replicates < 1:
        raise MatrixError("replicates must be >= 1")
    if m.order not in ("blocked-random", "sequential"):
        raise MatrixError(f"unknown order '{m.order}' (use blocked-random or sequential)")
    if m.seed_mode not in ("fixed", "per-replicate", "none"):
        raise MatrixError(f"unknown seed_mode '{m.seed_mode}' (use fixed, per-replicate or none)")
    if m.seed_mode != "none" and m.channel_seed is None:
        raise MatrixError("channel.seed is required unless seed_mode = 'none'")
    if len(m.payload_sha256) != 64:
        raise MatrixError("payload.sha256 must be a 64-char hex SHA-256 (use `hfbench payload hash`)")
    for kind, items in (("modem", m.modems), ("profile", m.profiles), ("impairment", m.impairments)):
        names = [i.name for i in items]
        if len(set(names)) != len(names):
            raise MatrixError(f"duplicate {kind} names: {names}")
    unknown = set(m.snr_by_profile) - {p.name for p in m.profiles}
    if unknown:
        raise MatrixError(f"snr_by_profile names unknown profiles: {sorted(unknown)}")


def _seed_for(m: Matrix, replicate: int) -> str:
    # The same seed is used for every modem at a given point, so modems see
    # identical fading realisations (if the simulator honours the seed).
    if m.seed_mode == "none":
        return ""
    if m.seed_mode == "fixed":
        return str(m.channel_seed)
    return str(int(m.channel_seed) + replicate - 1)


def build_runs(m: Matrix) -> list[dict]:
    """Expand the matrix into ordered run rows with run IDs assigned."""
    points = []
    for modem in m.modems:
        for prof, imp in itertools.product(m.profiles, m.impairments):
            for snr in m.snr_by_profile.get(prof.name, m.snr_db):
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
        rows.append({
            "run_id": f"{m.campaign}-{seq:04d}",
            "campaign": m.campaign,
            "stage": m.stage,
            "seq": seq,
            "modem": modem.name,
            "modem_version": modem.version,
            "modem_bandwidth_hz": modem.bandwidth_hz if modem.bandwidth_hz is not None else "",
            "profile": prof.name,
            "delay_ms": prof.delay_ms,
            "doppler_hz": prof.doppler_hz,
            "snr_db": _fmt_num(snr),
            "impairment": imp.name,
            "impairment_params": imp.params,
            "replicate": rep,
            "channel_seed": _seed_for(m, rep),
            "payload_file": m.payload_file,
            "payload_bytes": m.payload_bytes,
            "payload_sha256": m.payload_sha256,
            "abort_minutes": m.abort_minutes,
            "abort_retries": m.abort_retries,
        })
    return rows


def _fmt_num(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else str(x)


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
