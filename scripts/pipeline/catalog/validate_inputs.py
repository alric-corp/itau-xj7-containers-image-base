"""Reject invalid workflow inputs before builds or AWS authentication."""
import json
import math
import os
from pathlib import Path
import re

NAME = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')
DIGEST = re.compile(r'sha256:[0-9a-f]{64}')


def validate(frameworks, catalog, soak=None, digest=None):
    names = json.loads(frameworks)
    if not isinstance(names, list) or not names or len(names) > len(catalog):
        raise ValueError('frameworks must be a nonempty array within the catalog size')
    seen = set()
    for name in names:
        if (not isinstance(name, str) or not NAME.fullmatch(name)
                or name not in catalog or name in seen):
            raise ValueError('frameworks must contain unique names from the catalog')
        seen.add(name)
    if soak is not None:
        hours = float(soak)
        if not math.isfinite(hours) or hours < 0:
            raise ValueError('soak-hours must be finite and nonnegative')
    if digest is not None and not (isinstance(digest, str) and DIGEST.fullmatch(digest)):
        raise ValueError('digest must be sha256 followed by 64 lowercase hex characters')
    return names


def main():
    try:
        catalog = {p.stem for p in Path('frameworks').glob('*.yaml') if p.is_file()}
        # Recuperação passa um framework só (FRAMEWORK); build/validação/promoção
        # passam o array do lote (FRAMEWORKS). Mesma regra de catálogo nos dois.
        single = os.environ.get('FRAMEWORK')
        frameworks = json.dumps([single]) if single is not None else os.environ['FRAMEWORKS']
        validate(frameworks, catalog, os.environ.get('SOAK_HOURS'), os.environ.get('DIGEST'))
    except (ValueError, TypeError, KeyError):
        # Mensagem fixa: o input rejeitado não é ecoado de volta no log.
        print('Invalid workflow inputs: use unique framework names from the '
              'catalog, a finite nonnegative soak and a sha256:<64 hex> digest.', file=os.sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
