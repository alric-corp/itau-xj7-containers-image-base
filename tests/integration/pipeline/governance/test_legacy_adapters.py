"""Exercise the entry points still used by published reusable workflows."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[4]
MODULES = {
    'oci_artifact': 'artifacts', 'scan_images': 'artifacts',
    'tool_versions': 'operations', 'report_unfixed_cves': 'release',
    'runtime_images': 'runtime',
}


class LegacyAdapterTests(unittest.TestCase):
    def test_legacy_commands_match_package_cli_without_pythonpath(self):
        environment = {key: value for key, value in os.environ.items() if key != 'PYTHONPATH'}
        for name, domain in MODULES.items():
            with self.subTest(adapter=name), tempfile.TemporaryDirectory() as directory:
                legacy = subprocess.run(
                    [sys.executable, '-B', str(ROOT / f'.github/scripts/{name}.py'), '--help'],
                    cwd=directory, env=environment, capture_output=True, text=True, timeout=10)
                canonical = subprocess.run(
                    [sys.executable, '-B', '-m', f'scripts.pipeline.{domain}.{name}', '--help'],
                    cwd=ROOT, env=environment, capture_output=True, text=True, timeout=10)
                self.assertEqual(legacy.returncode, 0, legacy.stderr)
                self.assertEqual(canonical.returncode, 0, canonical.stderr)
                self.assertEqual(legacy.stdout, canonical.stdout)

    def test_runtime_import_preserves_the_published_workflow_api(self):
        code = '''import sys
sys.path.insert(0, sys.argv[1])
import runtime_images
assert runtime_images.runtime('nodejs24') == ('/usr/bin/node', 'probe.cjs')
assert runtime_images.supported('go1-26') == 'compiled'
assert runtime_images.project('go1-26')[1] == 'go1-26-dev'
assert runtime_images.runtime.__module__ == 'scripts.pipeline.runtime.runtime_images'
'''
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, '-B', '-c', code, str(ROOT / '.github/scripts')],
                cwd=directory, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_input_adapter_preserves_fail_closed_exit_codes(self):
        with tempfile.TemporaryDirectory() as directory:
            catalog = Path(directory) / 'frameworks'
            catalog.mkdir()
            (catalog / 'go1-26.yaml').write_text('')
            for value, code in (('["go1-26"]', 0), ('["../go1-26"]', 1)):
                with self.subTest(frameworks=value):
                    result = subprocess.run(
                        [sys.executable, '-B', str(ROOT / '.github/scripts/validate_inputs.py')],
                        cwd=directory, env={'PATH': os.environ['PATH'], 'FRAMEWORKS': value},
                        capture_output=True, text=True, timeout=10)
                    self.assertEqual(result.returncode, code, result.stderr)
