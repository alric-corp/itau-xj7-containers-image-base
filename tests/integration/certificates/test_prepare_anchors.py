import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.certificates.prepare_anchors import stage, verify


class AnchorTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def certificate(self, name, ca=True):
        pem = self.root / (name + '.pem')
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                        '-days', '1', '-keyout', str(self.root / (name + '.key')),
                        '-out', str(pem), '-subj', '/CN=' + name,
                        '-addext', 'basicConstraints=critical,CA:' + ('TRUE' if ca else 'FALSE')],
                       check=True, capture_output=True)
        return pem

    def test_bundle_is_split_and_deduplicated_before_apko(self):
        one, two = self.certificate('one'), self.certificate('two')
        bundle = self.root / 'internal.pem'
        bundle.write_text(one.read_text() + two.read_text() + one.read_text())
        destination = self.root / 'staged'
        result = stage(bundle, destination)
        self.assertEqual(len(result['certificates']), 2)
        self.assertEqual(verify(destination), result)
        for anchor in (destination / 'anchors').glob('*.crt'):
            self.assertEqual(anchor.read_text().count('BEGIN CERTIFICATE'), 1)

    def test_leaf_and_private_key_fail_without_partial_staging(self):
        leaf = self.certificate('leaf', ca=False)
        with self.assertRaisesRegex(ValueError, 'not a CA'):
            stage(leaf, self.root / 'rejected')
        self.assertFalse((self.root / 'rejected').exists())
        root = self.certificate('root')
        root.write_text(root.read_text() + (self.root / 'root.key').read_text())
        with self.assertRaisesRegex(ValueError, 'no keys'):
            stage(root, self.root / 'rejected')

    def test_mock_profile_cannot_enter_release(self):
        pem = self.certificate('MOCK-company-ca')
        with self.assertRaisesRegex(ValueError, 'test/mock'):
            stage(pem, self.root / 'staged')
        stage(pem, self.root / 'staged', allow_test=True)
        verify(self.root / 'staged', allow_test=True)
        with self.assertRaisesRegex(ValueError, 'unapproved'):
            verify(self.root / 'staged')

    def test_tampered_anchor_and_multicertificate_file_are_rejected(self):
        pem = self.certificate('root')
        destination = self.root / 'staged'
        stage(pem, destination)
        anchor = next((destination / 'anchors').glob('*.crt'))
        anchor.write_text(pem.read_text() * 2)
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            verify(destination)
        anchor.write_text(self.certificate('replacement').read_text())
        with self.assertRaisesRegex(ValueError, 'DER SHA-256'):
            verify(destination)
