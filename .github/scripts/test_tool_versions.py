import subprocess
import unittest
from unittest.mock import Mock, patch
from tool_versions import collect


class VersionTests(unittest.TestCase):
    def test_records_versions_without_secrets(self):
        run = Mock(return_value=subprocess.CompletedProcess([], 0, 'version 1', ''))
        with patch.dict('os.environ', {'AWS_SECRET_ACCESS_KEY': 'do-not-record', 'GITHUB_SHA': 'abc'}):
            result = collect('promotion', run)
        self.assertEqual(result['commit'], 'abc')
        self.assertNotIn('do-not-record', str(result))
        self.assertEqual(set(result['versions']), {'cosign', 'trivy', 'aws', 'gh', 'buildx'})
        self.assertTrue(all('shell' not in c.kwargs for c in run.call_args_list))

    def test_missing_or_failing_tool_blocks_evidence(self):
        for error in (FileNotFoundError(), subprocess.CalledProcessError(1, ['trivy']),
                      subprocess.TimeoutExpired(['trivy'], 30)):
            with self.subTest(error=error), self.assertRaises(type(error)):
                collect('validation', Mock(side_effect=error))
