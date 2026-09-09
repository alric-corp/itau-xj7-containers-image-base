"""Reject invalid workflow inputs before builds or AWS authentication."""
import json
import math
import os
from pathlib import Path
import re


def validate(frameworks, catalog, soak=None):
    names = json.loads(frameworks)
    if not isinstance(names, list) or not names or len(names) > len(catalog):
        raise ValueError('frameworks must be a nonempty array within the catalog size')
    seen = set()
    for name in names:
        if (not isinstance(name, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name)
                or name not in catalog or name in seen):
            raise ValueError('frameworks must contain unique names from the catalog')
        seen.add(name)
    if soak is not None:
        hours = float(soak)
        if not math.isfinite(hours) or hours < 0:
            raise ValueError('soak-hours must be finite and nonnegative')
    return names


if __name__ == '__main__':
    try:
        catalog = {p.stem for p in Path('frameworks').glob('*.yaml') if p.is_file()}
        validate(os.environ['FRAMEWORKS'], catalog, os.environ.get('SOAK_HOURS'))
    except (ValueError, TypeError, KeyError):
        raise SystemExit('Invalid workflow inputs: use unique framework names from the catalog and a finite, nonnegative soak.')
