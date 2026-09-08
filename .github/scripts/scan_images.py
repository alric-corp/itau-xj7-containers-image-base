#!/usr/bin/env python3
"""Escaneia ambas as arquiteturas e preserva evidências mesmo se uma falhar."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
from oci_artifact import platform_view, verify


def scan_images(mode: str, target: str, reports: Path = Path("reports")) -> int:
    if mode not in {"local", "remote", "oci"}:
        raise ValueError("modo deve ser local, oci ou remote")
    if mode == "local" and not re.fullmatch(r"[a-z0-9][a-z0-9-]*", target):
        raise ValueError("framework inválido")
    if mode == "remote" and not re.fullmatch(r"[^\s@]+@sha256:[0-9a-f]{64}", target):
        raise ValueError("scan remoto exige referência por digest SHA-256")

    reports.mkdir(parents=True, exist_ok=True)
    oci = verify(target) if mode == "oci" else None
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
            if mode == "local":
                archive = Path(f"{target}-{arch}.tar")
                digest = hashlib.sha256()
                with archive.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(chunk)
                evidence.update(archive=str(archive), archive_sha256=digest.hexdigest())
                command += ["--input", str(archive)]
            elif mode == "oci":
                evidence.update(index_digest=oci["digest"], manifest_digest=oci["platforms"][f"linux/{arch}"])
                view = tempfile.TemporaryDirectory(prefix="oci-scan-")
                platform_view(target, arch, view.name)
                command += ["--input", view.name]
            else:
                command += ["--image-src", "remote", target]
            result = subprocess.run(command, check=False)
            evidence["exit_code"] = result.returncode
            failed |= result.returncode != 0
            if mode == "oci":
                report = json.loads((reports / f"trivy-{arch}.json").read_text())
                scanned_arch = report["Metadata"]["ImageConfig"]["architecture"]
                if scanned_arch != arch:
                    raise ValueError(f"scanner analisou {scanned_arch}, esperado {arch}")
        except (OSError, ValueError, KeyError) as error:
            evidence["error"] = str(error)
            failed = True
        finally:
            if view is not None:
                view.cleanup()
        (reports / f"evidence-{arch}.json").write_text(json.dumps(evidence, indent=2) + "\n")
    return int(failed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("local", "remote", "oci"))
    parser.add_argument("target", help="framework local ou imagem@sha256:digest remoto")
    args = parser.parse_args()
    raise SystemExit(scan_images(args.mode, args.target))
