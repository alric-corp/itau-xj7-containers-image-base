import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import runtime_images as runtime


class RuntimeContractTests(unittest.TestCase):
    def test_unsupported_framework_fails_explicitly(self):
        for framework in ('dotnet8', 'nodejs999', '../nodejs24', 'nodejs24;id'):
            with self.subTest(framework=framework), self.assertRaises(ValueError):
                runtime.runtime(framework)

    def test_native_and_emulated_are_distinct(self):
        self.assertEqual(runtime.execution_mode('aarch64', 'arm64'), 'native')
        self.assertEqual(runtime.execution_mode('aarch64', 'amd64'), 'emulated')
        self.assertEqual(runtime.execution_mode('x86_64', 'amd64'), 'native')
        with self.assertRaises(ValueError):
            runtime.execution_mode('unknown', 'amd64')

    def test_missing_checks_and_root_are_rejected(self):
        result = dict(uid=10000, gid=10000, readonly=True, tmpfs=True,
                      bundle_parse=True, tls_trusted=True, tls_untrusted_rejected=True)
        self.assertEqual(runtime.validate_result(json.dumps(result)), result)
        for key in result:
            changed = dict(result)
            changed[key] = 0 if key in ('uid', 'gid') else False
            with self.subTest(key=key), self.assertRaises(ValueError):
                runtime.validate_result(json.dumps(changed))

    def test_invalid_oci_overwrites_stale_success_for_both_architectures(self):
        with tempfile.TemporaryDirectory() as temporary:
            reports = Path(temporary)
            for arch in ('amd64', 'arm64'):
                (reports / f'runtime-nodejs24-{arch}.json').write_text('{"status":"passed"}')
            with patch.object(runtime, 'verify', side_effect=ValueError('tampered blob')), \
                    patch.object(runtime, 'command') as command:
                self.assertEqual(runtime.run('/missing', 'nodejs24', reports), 1)
            command.assert_not_called()
            for path in reports.glob('*.json'):
                result = json.loads(path.read_text())
                self.assertEqual(result['status'], 'failed')
                self.assertIn('tampered blob', result['error'])

    def test_one_platform_failure_does_not_skip_other_platform(self):
        from contextlib import nullcontext
        verified = {'digest': 'index', 'platforms': {'linux/amd64': 'amd', 'linux/arm64': 'arm'}}
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / 'validated-index.json').write_text(json.dumps(verified))
            with patch.object(runtime, 'verify', return_value=verified), \
                    patch.object(runtime, 'command', return_value='aarch64'), \
                    patch.object(runtime, 'tls_server', side_effect=lambda *_: nullcontext(('url', 'ca'))), \
                    patch.object(runtime, 'run_platform', side_effect=[RuntimeError('bad TLS'), {'ok': True}]) as run:
                self.assertEqual(runtime.run(directory, 'nodejs24', directory), 1)
            self.assertEqual(run.call_count, 2)
            self.assertEqual(json.loads((directory / 'runtime-nodejs24-amd64.json').read_text())['status'], 'failed')
            self.assertEqual(json.loads((directory / 'runtime-nodejs24-arm64.json').read_text())['status'], 'passed')

    def test_config_digest_comes_from_archive_bytes(self):
        import hashlib
        config = b'{"architecture":"arm64","rootfs":{"diff_ids":["sha256:test"]}}'
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / 'docker.tar'
            with tarfile.open(archive, 'w') as output:
                for name, content in [('manifest.json', b'[{"Config":"config.json"}]'),
                                      ('config.json', config)]:
                    info = tarfile.TarInfo(name)
                    info.size = len(content)
                    output.addfile(info, io.BytesIO(content))
            self.assertEqual(runtime.archive_config(archive), 'sha256:' + hashlib.sha256(config).hexdigest())


if __name__ == '__main__':
    unittest.main()
