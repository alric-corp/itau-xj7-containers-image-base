import hashlib
from pathlib import Path
import tempfile
import unittest
from scripts.pipeline.governance.verify_cache_integrity import (
    CacheIntegrityError, parse_lockfile, verify_checksums)


def lockfile_for(directory, *names):
    lines = []
    for name in names:
        digest = hashlib.sha256((directory / name).read_bytes()).hexdigest()
        lines.append(f'{digest}  {name}')
    return '\n'.join(lines) + '\n'


class ParseLockfileTests(unittest.TestCase):
    def test_valid_lines(self):
        text = ('a' * 64) + '  file.txt\n' + ('b' * 64) + '  other/file.bin\n'
        self.assertEqual(parse_lockfile(text), {'file.txt': 'a' * 64, 'other/file.bin': 'b' * 64})

    def test_malformed_lines_fail_closed(self):
        for bad in ('not-a-checksum  file.txt', ('a' * 63) + '  file.txt',
                    ('A' * 64) + '  file.txt', ('a' * 64) + ' file.txt',
                    ('a' * 64), 'file.txt'):
            with self.subTest(bad=bad), self.assertRaises(CacheIntegrityError):
                parse_lockfile(bad)

    def test_empty_lockfile_rejected(self):
        with self.assertRaises(CacheIntegrityError):
            parse_lockfile('\n\n')


class VerifyChecksumsTests(unittest.TestCase):
    def test_matching_content_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'a.txt').write_bytes(b'hello')
            (path / 'b.txt').write_bytes(b'world')
            verify_checksums(path, lockfile_for(path, 'a.txt', 'b.txt'))  # must not raise

    def test_tampered_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'a.txt').write_bytes(b'hello')
            lock = lockfile_for(path, 'a.txt')
            (path / 'a.txt').write_bytes(b'tampered')  # restored cache "changed after being pinned"
            with self.assertRaises(CacheIntegrityError) as caught:
                verify_checksums(path, lock)
            self.assertIn('a.txt', str(caught.exception))

    def test_missing_file_from_a_partial_restore_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'a.txt').write_bytes(b'hello')
            lock = lockfile_for(path, 'a.txt')
            (path / 'a.txt').unlink()
            with self.assertRaises(CacheIntegrityError):
                verify_checksums(path, lock)

    def test_absent_cache_is_a_caller_decision_not_this_function(self):
        # A missing cache dir entirely still permits a correct build --
        # the caller decides to fall back to a full download/build, this
        # function only ever runs when there IS a restore to check.
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(CacheIntegrityError):
                verify_checksums(Path(directory) / 'does-not-exist', ('a' * 64) + '  missing.txt\n')
