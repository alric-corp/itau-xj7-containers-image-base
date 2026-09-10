"""Compatibility adapter; implementation lives in scripts/pipeline/."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if __name__ == '__main__':
    import runpy

    runpy.run_module('scripts.pipeline.artifacts.oci_artifact', run_name='__main__')
