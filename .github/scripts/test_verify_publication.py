import copy
import hashlib
import json
import unittest

from oci_artifact import INDEX, MANIFEST
from verify_publication import verify_publication


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.index = {'schemaVersion': 2, 'mediaType': INDEX, 'manifests': [
            {'mediaType': MANIFEST, 'digest': 'sha256:' + digit * 64,
             'platform': {'os': 'linux', 'architecture': arch}}
            for digit, arch in [('1', 'amd64'), ('2', 'arm64')]
        ]}
        self.raw = json.dumps(self.index).encode()
        self.digest = 'sha256:' + hashlib.sha256(self.raw).hexdigest()
        self.expected = {'digest': self.digest, 'platforms': {
            'linux/amd64': 'sha256:' + '1' * 64,
            'linux/arm64': 'sha256:' + '2' * 64,
        }}
        self.ref = 'example.invalid/image@' + self.digest

    def test_preserved_index_and_platform_manifests(self):
        evidence = verify_publication(self.expected, self.digest, self.raw, self.ref)
        self.assertEqual(evidence['remote_digest'], self.digest)
        self.assertEqual(evidence['platforms'], self.expected['platforms'])

    def test_copy_result_mismatch(self):
        with self.assertRaises(ValueError):
            verify_publication(self.expected, 'sha256:' + '0' * 64, self.raw, self.ref)

    def test_remote_bytes_mismatch_even_if_semantically_equal(self):
        with self.assertRaises(ValueError):
            verify_publication(self.expected, self.digest, self.raw + b'\n', self.ref)

    def test_scanned_platform_evidence_mismatch(self):
        expected = copy.deepcopy(self.expected)
        expected['platforms']['linux/arm64'] = 'sha256:' + '3' * 64
        with self.assertRaises(ValueError):
            verify_publication(expected, self.digest, self.raw, self.ref)

    def test_wrong_reference(self):
        for ref in ('example.invalid/image:latest', 'example.invalid/image@sha256:' + '0' * 64):
            with self.subTest(ref=ref), self.assertRaises(ValueError):
                verify_publication(self.expected, self.digest, self.raw, ref)

    def test_duplicate_or_missing_platforms(self):
        for manifests in ([self.index['manifests'][0]],
                          [self.index['manifests'][0], self.index['manifests'][0]]):
            remote = {**self.index, 'manifests': manifests}
            raw = json.dumps(remote).encode()
            digest = 'sha256:' + hashlib.sha256(raw).hexdigest()
            expected = {**self.expected, 'digest': digest}
            with self.subTest(manifests=manifests), self.assertRaises(ValueError):
                verify_publication(expected, digest, raw, 'example.invalid/image@' + digest)


if __name__ == '__main__':
    unittest.main()
