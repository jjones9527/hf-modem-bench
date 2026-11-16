#!/usr/bin/env python3
"""Export the bench data for public audit, redacted.

    python scripts/export_audit_data.py            # -> data/ (in git) and dist/bench-data-<date>.tar.gz

Reads logs/archive/ (made by scripts/archive-bench.sh) and writes:

1. data/ (committed): every campaign's run sheet, manifest, events, per-run and
   per-message results, measured S:N, console output, relay state and the pre-campaign
   tone/16QAM checks; plus data/partials/*.txt, the byte-level comparison of every kept
   partial file with what was sent (scripts/check_partial.py).
2. dist/bench-data-<date>.tar.gz (attached to a GitHub release, too big for git): the
   raw logs: both stations' Winlink session logs, ARDOP session/debug logs, Mercury
   engine logs, bench-relay logs, S:N recordings (listen-*.json), path checks.

Redaction: private strings are replaced in every exported file. They are read from
redact.local (git-ignored, one "private=public" pair per line, e.g. a grid square to
AA00AA, the bench computer's name to BENCH-PC), so the private values never appear in
this repository. The export fails if any private string survives. The raw partial
files are not exported: their message headers carry the station's position inside
the compressed data, which can't be redacted without breaking them.
"""
from __future__ import annotations

import datetime as dt
import io
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "logs" / "archive"
DATA = ROOT / "data"
DIST = ROOT / "dist"
SMALL = ("runsheet.csv", "manifest.csv", "events.jsonl", "runs.csv", "messages.csv", "snr.csv",
         "relay.txt", "levels-tonecheck.json", "qam-precheck.json")
RAW_DIRS = ("winlink", "mercury", "relay", "listen", "qam", "levels", "mercury-bringup", "reports")


def load_redactions() -> list[tuple[bytes, bytes]]:
    f = ROOT / "redact.local"
    if not f.exists():
        sys.exit("redact.local missing: one 'private=public' pair per line (see the docstring)")
    pairs = []
    for line in f.read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            a, b = line.split("=", 1)
            pairs.append((a.strip().encode(), b.strip().encode()))
    return pairs


def redact(data: bytes, pairs) -> bytes:
    for a, b in pairs:
        data = data.replace(a, b)
    data = re.sub(rb"192\.168\.\d{1,3}\.\d{1,3}", b"BENCH-IP", data)
    return data


def check(data: bytes, pairs, name: str) -> None:
    for a, _ in pairs:
        if a.lower() in data.lower():
            sys.exit(f"private string survived redaction in {name}")
    if re.search(rb"192\.168\.\d{1,3}\.\d{1,3}", data):
        sys.exit(f"private address survived redaction in {name}")


def campaigns() -> list[Path]:
    return sorted(p for p in ARCHIVE.iterdir() if p.is_dir() and (p / "runsheet.csv").exists())


def export_small(pairs) -> int:
    for d in ("campaigns", "partials"):          # data/README.md is kept
        if (DATA / d).exists():
            shutil.rmtree(DATA / d)
    n = 0
    for c in campaigns():
        for f in sorted(c.iterdir()):
            if f.name in SMALL or (f.name.startswith("console-") and f.suffix == ".txt"):
                out = DATA / "campaigns" / c.name / f.name
                out.parent.mkdir(parents=True, exist_ok=True)
                b = redact(f.read_bytes(), pairs)
                check(b, pairs, str(out))
                out.write_bytes(b)
                n += 1
    part = ARCHIVE / "partials"
    if part.exists():
        for f in sorted(part.glob("*.bin")):
            payload = ROOT / "payloads" / "Text_50KB"
            r = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_partial.py"), str(f), str(payload)],
                               capture_output=True)
            text = b"\n".join(l for l in r.stdout.splitlines()
                              if not l.startswith((b"X-Location", b"Mbo:")))
            b = redact(text + b"\n", pairs)
            check(b, pairs, f.name)
            out = DATA / "partials" / (f.stem + ".txt")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b)
            n += 1
    return n


def export_raw(pairs) -> Path:
    DIST.mkdir(exist_ok=True)
    out = DIST / f"bench-data-{dt.datetime.now(dt.timezone.utc):%Y%m%d}.tar.gz"
    with tarfile.open(out, "w:gz", compresslevel=6) as tar:
        for d in RAW_DIRS:
            base = ARCHIVE / d
            if not base.exists():
                continue
            for f in sorted(p for p in base.rglob("*") if p.is_file()):
                b = redact(f.read_bytes(), pairs)
                check(b, pairs, str(f))
                info = tarfile.TarInfo(f"bench-data/{f.relative_to(ARCHIVE)}")
                info.size, info.mtime = len(b), int(f.stat().st_mtime)
                tar.addfile(info, io.BytesIO(b))
        for c in campaigns():        # large per-campaign extras (Mercury/relay logs kept with a campaign)
            for f in sorted(c.iterdir()):
                if f.is_file() and f.suffix == ".log":
                    b = redact(f.read_bytes(), pairs)
                    check(b, pairs, str(f))
                    info = tarfile.TarInfo(f"bench-data/{f.relative_to(ARCHIVE)}")
                    info.size, info.mtime = len(b), int(f.stat().st_mtime)
                    tar.addfile(info, io.BytesIO(b))
    return out


if __name__ == "__main__":
    pairs = load_redactions()
    n = export_small(pairs)
    print(f"data/: {n} files")
    if "--small-only" not in sys.argv:
        t = export_raw(pairs)
        print(f"{t.relative_to(ROOT)}: {t.stat().st_size / 1e6:.0f} MB")
