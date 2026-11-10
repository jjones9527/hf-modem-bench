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
    files = sorted(p for p in Path(directory).iterdir() if p.is_file())
    per = {p.name: sha256_file(p) for p in files}
    listing = "".join(f"{h}  {n}\n" for n, h in per.items())
    return hashlib.sha256(listing.encode()).hexdigest(), per


def compress_ratio(path: str | Path) -> float:
    """zlib-compressed size / original size. ~1.0 means incompressible."""
    data = Path(path).read_bytes()
    return len(zlib.compress(data, 9)) / max(len(data), 1)
