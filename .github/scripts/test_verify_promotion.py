import json
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from contextlib import redirect_stderr

from verify_promotion import main, verify_promotion


IMAGE = "example.invalid/test@sha256:" + "a" * 64
REPO = "owner/repository"


def index(arches=("amd64", "arm64")):
    return json.dumps({"mediaType": "application/vnd.oci.image.index.v1+json",
                       "manifests": [{"platform": {"os": "linux", "architecture": arch}} for arch in arches]})


class VerificationTests(unittest.TestCase):
    def test_cli_expected_errors_are_clean_and_nonzero(self):
        for error in (ValueError("digest inválido"), KeyError("platform"),
                      TypeError("Metadata null"), FileNotFoundError("cosign"),
                      subprocess.CalledProcessError(10, ["cosign"], stderr="no signatures found")):
            with self.subTest(error=error), patch("sys.argv", ["verify_promotion.py", IMAGE, REPO]), \
                 patch("verify_promotion.verify_promotion", side_effect=error), \
                 redirect_stderr(io.StringIO()) as stderr:
                self.assertEqual(main(), 10 if isinstance(error, subprocess.CalledProcessError) else 1)
                self.assertTrue(stderr.getvalue().strip())
                self.assertNotIn("Traceback", stderr.getvalue())

    def test_both_verifiers_receive_digest_and_restricted_identity(self):
        with tempfile.TemporaryDirectory() as directory, patch("verify_promotion.subprocess.run", side_effect=[
            subprocess.CompletedProcess([], 0, stdout=output) for output in (index(), '[{"verified":true}]', '[{"verified":true}]')
        ]) as run:
            verify_promotion(IMAGE, REPO, Path(directory))
            signature = run.call_args_list[1].args[0]
            provenance = run.call_args_list[2].args[0]
            self.assertEqual(signature[-1], IMAGE)
            self.assertIn(f"https://github.com/{REPO}/.github/workflows/build-base-images.yml@refs/heads/main", signature)
            self.assertIn("refs/heads/main", provenance)
            self.assertIn(f"oci://{IMAGE}", provenance)
            self.assertEqual(len(list(Path(directory).glob("*.json"))), 3)

    def test_missing_or_duplicate_platform_blocks_verification(self):
        for arches in (("amd64",), ("amd64", "amd64"), ("amd64", "arm64", "unknown")):
            with self.subTest(arches=arches), tempfile.TemporaryDirectory() as directory, patch(
                "verify_promotion.subprocess.run", return_value=subprocess.CompletedProcess([], 0, stdout=index(arches))
            ) as run:
                with self.assertRaises(ValueError):
                    verify_promotion(IMAGE, REPO, Path(directory))
                self.assertEqual(run.call_count, 1)

    def test_failed_signature_or_provenance_blocks_promotion(self):
        for failure_at in (1, 2):
            results = [subprocess.CompletedProcess([], 0, stdout=index())]
            if failure_at == 2:
                results.append(subprocess.CompletedProcess([], 0, stdout='[{"verified":true}]'))
            results.append(subprocess.CalledProcessError(1, ["verifier"]))
            with self.subTest(failure_at=failure_at), tempfile.TemporaryDirectory() as directory, patch(
                "verify_promotion.subprocess.run", side_effect=results
            ) as run:
                with self.assertRaises(subprocess.CalledProcessError):
                    verify_promotion(IMAGE, REPO, Path(directory))
                self.assertEqual(run.call_count, failure_at + 1)

    def test_empty_verification_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as directory, patch("verify_promotion.subprocess.run", side_effect=[
            subprocess.CompletedProcess([], 0, stdout=index()), subprocess.CompletedProcess([], 0, stdout="[]")
        ]):
            with self.assertRaises(ValueError):
                verify_promotion(IMAGE, REPO, Path(directory))


if __name__ == "__main__":
    unittest.main()
