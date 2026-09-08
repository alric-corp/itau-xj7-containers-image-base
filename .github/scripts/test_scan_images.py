import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scan_images import scan_images


REMOTE = "example.invalid/image-base-test@sha256:" + "a" * 64


class ScanTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.previous = Path.cwd()
        os.chdir(self.directory.name)
        self.addCleanup(self.directory.cleanup)
        self.addCleanup(os.chdir, self.previous)

    def test_both_remote_platforms_use_the_same_digest(self):
        with patch("scan_images.subprocess.run", return_value=subprocess.CompletedProcess([], 0)) as run:
            self.assertEqual(scan_images("remote", REMOTE), 0)
        self.assertEqual(run.call_count, 2)
        for arch, call in zip(("amd64", "arm64"), run.call_args_list):
            command = call.args[0]
            self.assertEqual(command[command.index("--platform") + 1], f"linux/{arch}")
            self.assertEqual(command[command.index("--image-src") + 1], "remote")
            self.assertEqual(command[-1], REMOTE)
            self.assertIn("--ignore-unfixed", command)
            self.assertEqual(command[command.index("--exit-code") + 1], "1")
            evidence = json.loads(Path(f"reports/evidence-{arch}.json").read_text())
            self.assertEqual(evidence["target"], REMOTE)
            self.assertEqual(evidence["exit_code"], 0)

    def test_failure_on_either_platform_blocks_release_and_still_scans_both(self):
        for codes in ((1, 0), (0, 1), (1, 1), (2, 0)):
            with self.subTest(codes=codes), patch(
                "scan_images.subprocess.run",
                side_effect=[subprocess.CompletedProcess([], code) for code in codes],
            ) as run:
                self.assertEqual(scan_images("remote", REMOTE), 1)
                self.assertEqual(run.call_count, 2)
                for arch, code in zip(("amd64", "arm64"), codes):
                    evidence = json.loads(Path(f"reports/evidence-{arch}.json").read_text())
                    self.assertEqual(evidence["exit_code"], code)

    def test_missing_scanner_fails_closed_and_records_errors(self):
        with patch("scan_images.subprocess.run", side_effect=FileNotFoundError("trivy missing")):
            self.assertEqual(scan_images("remote", REMOTE), 1)
        for arch in ("amd64", "arm64"):
            self.assertIn("error", json.loads(Path(f"reports/evidence-{arch}.json").read_text()))

    def test_oci_scan_rejects_report_for_the_wrong_architecture(self):
        def scanner(command, **kwargs):
            output = Path(command[command.index("--output") + 1])
            output.write_text(json.dumps({"Metadata": {"ImageConfig": {"architecture": "amd64"}}}))
            return subprocess.CompletedProcess(command, 0)
        metadata = {"digest": "sha256:index", "platforms": {
            "linux/amd64": "sha256:amd64", "linux/arm64": "sha256:arm64"}}
        with patch("scan_images.verify", return_value=metadata), patch("scan_images.platform_view"), \
             patch("scan_images.subprocess.run", side_effect=scanner) as run:
            self.assertEqual(scan_images("oci", "image.oci"), 1)
            self.assertEqual(run.call_count, 2)
        evidence = json.loads(Path("reports/evidence-arm64.json").read_text())
        self.assertIn("esperado arm64", evidence["error"])

    def test_local_scan_records_hash_of_each_archive(self):
        for arch in ("amd64", "arm64"):
            Path(f"nodejs24-{arch}.tar").write_bytes(arch.encode())
        with patch("scan_images.subprocess.run", return_value=subprocess.CompletedProcess([], 0)) as run:
            self.assertEqual(scan_images("local", "nodejs24"), 0)
        for arch, call in zip(("amd64", "arm64"), run.call_args_list):
            self.assertEqual(call.args[0][-2:], ["--input", f"nodejs24-{arch}.tar"])
            evidence = json.loads(Path(f"reports/evidence-{arch}.json").read_text())
            self.assertEqual(evidence["archive_sha256"], hashlib.sha256(arch.encode()).hexdigest())

    def test_missing_local_archive_does_not_skip_other_architecture(self):
        Path("nodejs24-arm64.tar").write_bytes(b"arm64")
        with patch("scan_images.subprocess.run", return_value=subprocess.CompletedProcess([], 0)) as run:
            self.assertEqual(scan_images("local", "nodejs24"), 1)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0][-1], "nodejs24-arm64.tar")
        self.assertIn("error", json.loads(Path("reports/evidence-amd64.json").read_text()))

    def test_mutable_remote_references_are_rejected_before_scanning(self):
        for target in ("example.invalid/test:stable", "example.invalid/test@sha256:bad",
                       REMOTE + "\n", "--help"):
            with self.subTest(target=target), patch("scan_images.subprocess.run") as run:
                with self.assertRaises(ValueError):
                    scan_images("remote", target)
                run.assert_not_called()

    def test_local_framework_cannot_escape_working_directory(self):
        for target in ("../nodejs24", "nodejs24\nINJECT=value", "nodejs24;false"):
            with self.subTest(target=target), patch("scan_images.subprocess.run") as run:
                with self.assertRaises(ValueError):
                    scan_images("local", target)
                run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
