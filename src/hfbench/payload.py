"""Fixed, incompressible test payload.

Winlink B2F compresses messages, so a compressible payload would make timing
depend on content. Seeded pseudo-random bytes don't compress and can be
regenerated bit-for-bit from (size, seed); the SHA-256 goes in the matrix.
"""

from __future__ import annotations

import hashlib
import random
import zlib
from pathlib import Path


def make_payload(path: str | Path, size: int, seed: int) -> str:
    data = random.Random(seed).randbytes(size)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_set(directory: str | Path) -> tuple[str, dict[str, str]]:
    """Hash of a payload *set* (a folder of attachment files): SHA-256 over the
    sorted lines '<sha256>  <name>', the same format sha256sum prints. Adding,
    removing, renaming or changing any file changes it."""
    # sort by exact name (code-point order): WindowsPath sorting is case-insensitive
    files = sorted((p for p in Path(directory).iterdir() if p.is_file()), key=lambda p: p.name)
    per = {p.name: sha256_file(p) for p in files}
    listing = "".join(f"{h}  {n}\n" for n, h in per.items())
    return hashlib.sha256(listing.encode()).hexdigest(), per


def derive_join_set(src: str | Path, dst: str | Path) -> tuple[str, dict[str, str]]:
    """A set of double-length files, same names: each file of `src` followed by the
    next one in name order (the last by the first). Text_100KB = derive_join_set(
    'Text_50KB', 'Text_100KB'): the same text, no repeat closer than one file apart, so
    B2F's compression sees it as it sees Text_50KB, and a message takes twice as long."""
    files = sorted((p for p in Path(src).iterdir() if p.is_file()), key=lambda p: p.name)
    out = Path(dst)
    out.mkdir(parents=True, exist_ok=True)
    for i, f in enumerate(files):
        (out / f.name).write_bytes(f.read_bytes() + files[(i + 1) % len(files)].read_bytes())
    return sha256_set(out)


def compress_ratio(path: str | Path) -> float:
    """zlib-compressed size / original size. ~1.0 means incompressible."""
    data = Path(path).read_bytes()
    return len(zlib.compress(data, 9)) / max(len(data), 1)


def derive_prefix_set(src: str | Path, dst: str | Path, size: int) -> tuple[str, dict[str, str]]:
    """A smaller set made of the first `size` bytes of every file in `src`, same
    names. Text_5KB = derive_prefix_set('Text_50KB', 'Text_5KB', 5120): same files,
    same character statistics, so the two sets differ only in length."""
    out = Path(dst)
    out.mkdir(parents=True, exist_ok=True)
    for f in sorted((p for p in Path(src).iterdir() if p.is_file()), key=lambda p: p.name):
        data = f.read_bytes()
        if len(data) < size:
            raise ValueError(f"{f.name} has only {len(data)} bytes")
        (out / f.name).write_bytes(data[:size])
    return sha256_set(out)
