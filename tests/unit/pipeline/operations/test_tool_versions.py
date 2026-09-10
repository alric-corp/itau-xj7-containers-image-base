import subprocess
import unittest
from unittest.mock import Mock, patch
from scripts.pipeline.operations.tool_versions import collect


class VersionTests(unittest.TestCase):
    def test_records_versions_without_secrets(self):
        run = Mock(return_value=subprocess.CompletedProcess([], 0, 'version 1', ''))
        with patch.dict('os.environ', {'AWS_SECRET_ACCESS_KEY': 'do-not-record', 'GITHUB_SHA': 'abc'}):
            result = collect('promotion', run)
        self.assertEqual(result['commit'], 'abc')
        self.assertNotIn('do-not-record', str(result))
        self.assertEqual(set(result['versions']),
                         {'cosign', 'trivy', 'aws', 'gh', 'buildx', 'python3', 'git'})
        self.assertTrue(all('shell' not in c.kwargs for c in run.call_args_list))

    def test_records_runner_image_and_pinned_skopeo_without_other_variables(self):
        # M09: a versão da imagem do runner muda sem passar por pin nenhum
        # deste repositório, e o digest do Skopeo efetivamente usado pertence
        # à evidência da etapa. Nada além dos campos em allowlist entra.
        run = Mock(return_value=subprocess.CompletedProcess([], 0, 'version 1', ''))
        environment = {'GITHUB_SHA': 'abc', 'RUNNER_OS': 'Linux', 'RUNNER_ARCH': 'X64',
                       'ImageOS': 'ubuntu24', 'ImageVersion': '20260901.1',
                       'SKOPEO_IMAGE': 'quay.io/skopeo/stable@sha256:' + 'b' * 64,
                       'AWS_SESSION_TOKEN': 'do-not-record', 'HOME': '/home/runner'}
        result = collect('publication', run, environment)
        self.assertEqual(result['runner'], {'RUNNER_OS': 'Linux', 'RUNNER_ARCH': 'X64',
                                            'ImageOS': 'ubuntu24',
                                            'ImageVersion': '20260901.1'})
        self.assertEqual(result['pinned_images']['skopeo'], environment['SKOPEO_IMAGE'])
        self.assertNotIn('do-not-record', str(result))
        self.assertNotIn('/home/runner', str(result))

    def test_missing_or_failing_tool_blocks_evidence(self):
        for error in (FileNotFoundError(), subprocess.CalledProcessError(1, ['trivy']),
                      subprocess.TimeoutExpired(['trivy'], 30)):
            with self.subTest(error=error), self.assertRaises(type(error)):
                collect('validation', Mock(side_effect=error))
