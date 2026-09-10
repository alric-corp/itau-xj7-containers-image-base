import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from scripts.pipeline.catalog.validate_inputs import validate

ROOT = pathlib.Path(__file__).resolve().parents[4]
SCRIPT = ROOT / 'scripts/pipeline/catalog/validate_inputs.py'


class InputTests(unittest.TestCase):
    def test_catalog_and_zero_soak(self):
        self.assertEqual(validate('["go1-26","java21"]', {'go1-26', 'java21'}, '0'), ['go1-26', 'java21'])

    def test_malformed_unknown_duplicate_and_injection(self):
        for raw in ('null', '{}', '[]', '"go1-26"', 'invalid', '[1]',
                    '["../go1-26"]', '["go1-26\\n"]', '["$(id)"]',
                    '["go1-26","go1-26"]', '["unknown"]'):
            with self.subTest(raw=raw), self.assertRaises((ValueError, TypeError)):
                validate(raw, {'go1-26', 'java21'})

    def test_invalid_soak(self):
        for soak in ('-1', 'nan', 'inf', '1e999', 'false', '$(id)', ''):
            with self.subTest(soak=soak), self.assertRaises(ValueError):
                validate('["go1-26"]', {'go1-26'}, soak)

    def test_valid_digest(self):
        digest = 'sha256:' + '0a' * 32
        self.assertEqual(validate('["go1-26"]', {'go1-26'}, None, digest), ['go1-26'])

    def test_invalid_digest(self):
        for digest in ('', 'sha256:', 'sha256:abc', 'sha512:' + '0a' * 32,
                       'sha256:' + '0A' * 32, 'sha256:' + '0a' * 32 + 'a',
                       'sha256:' + '0a' * 32 + ' && id', ' sha256:' + '0a' * 32,
                       'stable', 42):
            with self.subTest(digest=digest), self.assertRaises(ValueError):
                validate('["go1-26"]', {'go1-26'}, None, digest)


class CliTests(unittest.TestCase):
    """O guard roda como script antes dos passos AWS: o contrato é o exit code."""

    def run_cli(self, **env):
        with tempfile.TemporaryDirectory() as workdir:
            catalog = pathlib.Path(workdir, 'frameworks')
            catalog.mkdir()
            (catalog / 'go1-26.yaml').write_text('')
            return subprocess.run(
                [sys.executable, '-B', pathlib.Path(SCRIPT).resolve()],
                cwd=workdir, capture_output=True, text=True,
                env={'PATH': os.environ['PATH'], **env})

    def test_single_framework_accepted(self):
        self.assertEqual(self.run_cli(FRAMEWORK='go1-26').returncode, 0)

    def test_single_framework_outside_catalog_rejected(self):
        result = self.run_cli(FRAMEWORK='../frameworks/go1-26')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Invalid workflow inputs', result.stderr)

    def test_rejected_input_is_not_echoed_back(self):
        result = self.run_cli(FRAMEWORK='go1-26', DIGEST='sha256:$(id)')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('$(id)', result.stdout + result.stderr)

    def test_missing_frameworks_rejected(self):
        self.assertNotEqual(self.run_cli().returncode, 0)
