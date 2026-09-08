#!/usr/bin/env python3
"""Escaneia ambas as arquiteturas e preserva evidências mesmo se uma falhar."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
from oci_artifact import platform_view, verify
from image_reference import require_digest_reference

SCAN_ERRORS = (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError)


def scan_images(mode: str, target: str, reports: Path = Path("reports")) -> int:
    if mode not in {"remote", "oci"}:
        raise ValueError("modo deve ser oci ou remote")
    if mode == "remote":
        require_digest_reference(target)

    reports.mkdir(parents=True, exist_ok=True)
    oci, validation_error = None, None
    try:
        oci = verify(target) if mode == "oci" else None
    except SCAN_ERRORS as error:
        validation_error = str(error)
    failed = False
    for arch in ("amd64", "arm64"):
        view = None
        evidence = {"platform": f"linux/{arch}", "target": target, "mode": mode}
        command = [
            "trivy", "image", "--platform", f"linux/{arch}",
            "--format", "json", "--output", str(reports / f"trivy-{arch}.json"),
            "--severity", "CRITICAL,HIGH,MEDIUM,LOW", "--ignore-unfixed",
            "--exit-code", "1", "--scanners", "vuln,secret",
        ]
        try:
            report_path = reports / f"trivy-{arch}.json"
            report_path.unlink(missing_ok=True)
            if validation_error is not None:
                raise ValueError(f"validação OCI falhou: {validation_error}")
            if mode == "oci":
                evidence.update(index_digest=oci["digest"], manifest_digest=oci["platforms"][f"linux/{arch}"])
                view = tempfile.TemporaryDirectory(prefix="oci-scan-")
                platform_view(target, arch, view.name)
                command += ["--input", view.name]
            else:
                command += ["--image-src", "remote", target]
            result = subprocess.run(command, check=False)
            evidence["exit_code"] = result.returncode
            failed |= result.returncode != 0
            report = json.loads(report_path.read_text())
            scanned_arch = report["Metadata"]["ImageConfig"]["architecture"]
            evidence["scanned_architecture"] = scanned_arch
            if scanned_arch != arch:
                raise ValueError(f"scanner analisou {scanned_arch}, esperado {arch}")
        except SCAN_ERRORS as error:
            evidence["error"] = str(error)
            failed = True
        finally:
            if view is not None:
                view.cleanup()
        (reports / f"evidence-{arch}.json").write_text(json.dumps(evidence, indent=2) + "\n")
    return int(failed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("remote", "oci"))
    parser.add_argument("target", help="layout OCI ou imagem@sha256:digest remoto")
    args = parser.parse_args()
    raise SystemExit(scan_images(args.mode, args.target))
