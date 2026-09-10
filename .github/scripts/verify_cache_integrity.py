"""Verify restored content against a pinned checksum lockfile before use.

Same trust model already used by scripts/certificados.sh for the corporate
CA bundle (lockfile committed to Git, content verified on every use, never
trusted just because it came from a fast/local source) -- generalized here
as a small, reusable primitive for any future `actions/cache` restore step
in the release path. A cache is a fast copy of something, never the
authorization to skip verifying it; this is what "validar downloads
restaurados antes de executá-los" means in practice.
"""
import hashlib
from pathlib import Path


class CacheIntegrityError(RuntimeError):
    """A restored file is missing, extra, or doesn't match its pinned hash."""


def parse_lockfile(text):
    """Parse `sha256sum`-style lines ("<64 hex>  <path>") strictly -- a
    malformed line fails closed instead of silently matching everything,
    same rule scripts/certificados.sh already enforces for the CA bundle."""
    entries = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split('  ', 1)
        if len(parts) != 2 or len(parts[0]) != 64 or not all(c in '0123456789abcdef' for c in parts[0]):
            raise CacheIntegrityError(f'malformed lockfile line: {line!r}')
        entries[parts[1]] = parts[0]
    if not entries:
        raise CacheIntegrityError('lockfile has no entries')
    return entries


def verify_checksums(directory, lockfile_text):
    """Raise CacheIntegrityError unless every file the lockfile names
    exists under `directory` with exactly the pinned sha256 -- and no
    unexpected file both isn't listed and isn't reported (this only
    checks what's promised, callers that need a closed set should also
    compare directory listings)."""
    directory = Path(directory)
    for relative_path, expected in parse_lockfile(lockfile_text).items():
        target = directory / relative_path
        if not target.is_file():
            raise CacheIntegrityError(f'restored cache is missing {relative_path}')
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != expected:
            raise CacheIntegrityError(
                f'restored {relative_path} does not match its pinned checksum '
                f'(expected {expected}, got {actual}) -- treat the cache as tampered, rebuild instead')
