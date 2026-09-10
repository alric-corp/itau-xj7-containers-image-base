import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts.pipeline.release.report_unfixed_cves import (
    extract_unfixed, main, report_unfixed_cves)


REMOTE = "example.invalid/image-base-test@sha256:" + "a" * 64

SAMPLE_REPORT = {
    "Results": [
        {
            "Target": "test (wolfi 20230201)",
            "Vulnerabilities": [
                {"VulnerabilityID": "CVE-FIXED-1", "PkgName": "libfoo",
                 "InstalledVersion": "1.0", "Severity": "HIGH", "FixedVersion": "1.1"},
                {"VulnerabilityID": "CVE-UNFIXED-1", "PkgName": "libbar",
                 "InstalledVersion": "2.0", "Severity": "CRITICAL"},
                {"VulnerabilityID": "CVE-UNFIXED-2", "PkgName": "libbaz",
                 "InstalledVersion": "3.0", "Severity": "MEDIUM", "FixedVersion": ""},
            ],
        }
    ]
}


def scanner_factory(report):
    def scanner(command, **kwargs):
        Path(command[command.index("--output") + 1]).write_text(json.dumps(report))
        return subprocess.CompletedProcess(command, 0)
    return scanner


class ExtractUnfixedTests(unittest.TestCase):
    def test_only_entries_without_fixed_version_are_kept(self):
        unfixed = extract_unfixed(SAMPLE_REPORT)
        self.assertEqual([entry["id"] for entry in unfixed], ["CVE-UNFIXED-1", "CVE-UNFIXED-2"])

    def test_missing_results_or_vulnerabilities_yields_empty_list(self):
        for report in ({}, {"Results": None}, {"Results": [{}]}, {"Results": [{"Vulnerabilities": None}]}):
            with self.subTest(report=report):
                self.assertEqual(extract_unfixed(report), [])


class ReportUnfixedCvesTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.previous = Path.cwd()
        os.chdir(self.directory.name)
        self.addCleanup(self.directory.cleanup)
        self.addCleanup(os.chdir, self.previous)

    def test_never_uses_ignore_unfixed_or_exit_code(self):
        with patch("scripts.pipeline.release.report_unfixed_cves.subprocess.run",
                   side_effect=scanner_factory(SAMPLE_REPORT)) as run:
            report_unfixed_cves("remote", REMOTE)
        self.assertEqual(run.call_count, 2)
        for call in run.call_args_list:
            command = call.args[0]
            self.assertNotIn("--ignore-unfixed", command)
            self.assertNotIn("--exit-code", command)

    def test_summary_contains_unfixed_cves_per_architecture(self):
        with patch("scripts.pipeline.release.report_unfixed_cves.subprocess.run",
                   side_effect=scanner_factory(SAMPLE_REPORT)):
            summary = report_unfixed_cves("remote", REMOTE)
        for arch in ("amd64", "arm64"):
            ids = [entry["id"] for entry in summary["architectures"][arch]]
            self.assertEqual(ids, ["CVE-UNFIXED-1", "CVE-UNFIXED-2"])
        self.assertTrue(Path("reports/unfixed-cves-summary.json").exists())

    def test_clean_image_produces_empty_lists_not_errors(self):
        clean = {"Results": [{"Target": "x", "Vulnerabilities": []}]}
        with patch("scripts.pipeline.release.report_unfixed_cves.subprocess.run", side_effect=scanner_factory(clean)):
            summary = report_unfixed_cves("remote", REMOTE)
        self.assertEqual(summary["architectures"]["amd64"], [])
        self.assertEqual(summary["architectures"]["arm64"], [])

    def test_scanner_failure_is_captured_per_architecture_not_raised(self):
        with patch("scripts.pipeline.release.report_unfixed_cves.subprocess.run", side_effect=FileNotFoundError("trivy missing")):
            summary = report_unfixed_cves("remote", REMOTE)
        for arch in ("amd64", "arm64"):
            self.assertIn("error", summary["architectures"][arch])

    def test_main_never_returns_nonzero_even_on_hard_failure(self):
        with patch("scripts.pipeline.release.report_unfixed_cves.report_unfixed_cves", side_effect=ValueError("boom")), \
             patch("sys.argv", ["report_unfixed_cves.py", "remote", REMOTE]):
            self.assertEqual(main(), 0)

    def test_main_succeeds_end_to_end(self):
        with patch("scripts.pipeline.release.report_unfixed_cves.subprocess.run",
                   side_effect=scanner_factory(SAMPLE_REPORT)), \
             patch("sys.argv", ["report_unfixed_cves.py", "remote", REMOTE]):
            self.assertEqual(main(), 0)

    def test_invalid_remote_reference_does_not_raise_out_of_main(self):
        with patch("sys.argv", ["report_unfixed_cves.py", "remote", "example.invalid/test:stable"]):
            self.assertEqual(main(), 0)


if __name__ == "__main__":
    unittest.main()
