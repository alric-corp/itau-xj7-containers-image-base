import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scan_images import scan_images


REMOTE = "example.invalid/image-base-test@sha256:" + "a" * 64


def successful_scanner(command, **kwargs):
    arch = command[command.index("--platform") + 1].split("/")[1]
    Path(command[command.index("--output") + 1]).write_text(
        json.dumps({"Metadata": {"ImageConfig": {"architecture": arch}}}))
    return subprocess.CompletedProcess(command, 0)


class ScanTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.previous = Path.cwd()
        os.chdir(self.directory.name)
        self.addCleanup(self.directory.cleanup)
        self.addCleanup(os.chdir, self.previous)

    def test_both_remote_platforms_use_the_same_digest(self):
        with patch("scan_images.subprocess.run", side_effect=successful_scanner) as run:
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
            results = iter(codes)
            def scanner(command, **kwargs):
                successful_scanner(command)
                return subprocess.CompletedProcess(command, next(results))
            with self.subTest(codes=codes), patch(
                "scan_images.subprocess.run",
                side_effect=scanner,
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

    def test_corrupt_oci_writes_both_evidences_without_scanning(self):
        for error in (ValueError("blob alterado"), FileNotFoundError("index ausente"), TypeError("índice null")):
            with self.subTest(error=error), patch("scan_images.verify", side_effect=error), \
                 patch("scan_images.subprocess.run") as run:
                self.assertEqual(scan_images("oci", "broken.oci"), 1)
                run.assert_not_called()
                for arch in ("amd64", "arm64"):
                    evidence = json.loads(Path(f"reports/evidence-{arch}.json").read_text())
                    self.assertIn(str(error), evidence["error"])
                    self.assertEqual(evidence["platform"], f"linux/{arch}")

    def test_null_or_malformed_report_does_not_skip_second_platform(self):
        for report in ({"Metadata": None}, {"Metadata": {"ImageConfig": None}}, [], "invalid json"):
            def scanner(command, **kwargs):
                output = Path(command[command.index("--output") + 1])
                output.write_text(report if isinstance(report, str) else json.dumps(report))
                return subprocess.CompletedProcess(command, 0)
            with self.subTest(report=report), patch("scan_images.subprocess.run", side_effect=scanner) as run:
                self.assertEqual(scan_images("remote", REMOTE), 1)
                self.assertEqual(run.call_count, 2)
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

    def test_remote_scan_rejects_wrong_architecture(self):
        def wrong_scanner(command, **kwargs):
            successful_scanner(command)
            Path(command[command.index("--output") + 1]).write_text(
                json.dumps({"Metadata": {"ImageConfig": {"architecture": "amd64"}}}))
            return subprocess.CompletedProcess(command, 0)
        with patch("scan_images.subprocess.run", side_effect=wrong_scanner) as run:
            self.assertEqual(scan_images("remote", REMOTE), 1)
            self.assertEqual(run.call_count, 2)
        evidence = json.loads(Path("reports/evidence-arm64.json").read_text())
        self.assertIn("esperado arm64", evidence["error"])

    def test_remote_scan_cannot_reuse_stale_reports(self):
        Path("reports").mkdir()
        for arch in ("amd64", "arm64"):
            Path(f"reports/trivy-{arch}.json").write_text(
                json.dumps({"Metadata": {"ImageConfig": {"architecture": arch}}}))
        with patch("scan_images.subprocess.run", return_value=subprocess.CompletedProcess([], 0)) as run:
            self.assertEqual(scan_images("remote", REMOTE), 1)
            self.assertEqual(run.call_count, 2)
        for arch in ("amd64", "arm64"):
            self.assertIn("error", json.loads(Path(f"reports/evidence-{arch}.json").read_text()))

    def test_mutable_remote_references_are_rejected_before_scanning(self):
        for target in ("example.invalid/test:stable", "example.invalid/test@sha256:bad",
                       REMOTE + "\n", "--help"):
            with self.subTest(target=target), patch("scan_images.subprocess.run") as run:
                with self.assertRaises(ValueError):
                    scan_images("remote", target)
                run.assert_not_called()



if __name__ == "__main__":
    unittest.main()
