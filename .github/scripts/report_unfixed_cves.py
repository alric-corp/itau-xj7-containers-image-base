#!/usr/bin/env python3
"""Reporta CVEs sem correção disponível, sem bloquear o pipeline (M11).

O gate de scan (scan_images.py) usa `--ignore-unfixed`: uma CVE sem
correção disponível no Wolfi nunca aparece no relatório que bloqueia a
promoção — nem no JSON, nem em lugar nenhum. Isso é a decisão de design
certa pro gate (bloquear por algo que ninguém pode corrigir ainda não
ajuda), mas deixa essas CVEs completamente invisíveis, mesmo pra quem só
quer saber que elas existem. Este script roda um scan separado, SEM
`--ignore-unfixed` e sem `--exit-code`, e escreve um resumo só das CVEs
sem correção — nunca falha o processo que o chama; é puramente
informativo.

Uso:
    python3 report_unfixed_cves.py <mode> <target> [reports_dir]

<mode> é "oci" ou "remote", mesmo contrato de scan_images.py.
"""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
from oci_artifact import platform_view, verify
from image_reference import require_digest_reference

SCAN_ERRORS = (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError)


def extract_unfixed(report: dict) -> list:
    unfixed = []
    for result in report.get("Results") or []:
        for vuln in result.get("Vulnerabilities") or []:
            if vuln.get("FixedVersion"):
                continue
            unfixed.append({
                "id": vuln.get("VulnerabilityID"),
                "package": vuln.get("PkgName"),
                "installed_version": vuln.get("InstalledVersion"),
                "severity": vuln.get("Severity"),
                "target": result.get("Target"),
            })
    return unfixed


def report_unfixed_cves(mode: str, target: str, reports: Path = Path("reports")) -> dict:
    if mode not in {"remote", "oci"}:
        raise ValueError("modo deve ser oci ou remote")
    if mode == "remote":
        require_digest_reference(target)

    reports.mkdir(parents=True, exist_ok=True)
    oci = verify(target) if mode == "oci" else None

    summary = {"target": target, "mode": mode, "architectures": {}}
    for arch in ("amd64", "arm64"):
        view = None
        report_path = reports / f"unfixed-{arch}.json"
        report_path.unlink(missing_ok=True)
        command = [
            "trivy", "image", "--platform", f"linux/{arch}",
            "--format", "json", "--output", str(report_path),
            "--severity", "CRITICAL,HIGH,MEDIUM,LOW", "--scanners", "vuln",
        ]
        try:
            if mode == "oci":
                view = tempfile.TemporaryDirectory(prefix="oci-unfixed-")
                platform_view(target, arch, view.name)
                command += ["--input", view.name]
            else:
                command += ["--image-src", "remote", target]
            # Sem check=True e sem --exit-code: este scan nunca falha o
            # processo, mesmo com achados — é só visibilidade.
            subprocess.run(command, check=False)
            report = json.loads(report_path.read_text())
            summary["architectures"][arch] = extract_unfixed(report)
        except SCAN_ERRORS as error:
            summary["architectures"][arch] = {"error": str(error)}
        finally:
            if view is not None:
                view.cleanup()

    (reports / "unfixed-cves-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def print_summary(summary: dict) -> None:
    for arch, entries in summary["architectures"].items():
        if isinstance(entries, dict) and "error" in entries:
            print(f"{arch}: erro ao escanear ({entries['error']}) — visibilidade indisponível, não bloqueia")
            continue
        if not entries:
            print(f"{arch}: nenhuma CVE sem correção conhecida")
            continue
        print(f"{arch}: {len(entries)} CVE(s) sem correção disponível")
        for entry in entries:
            print(f"  {entry['id']} ({entry['severity']}) — {entry['package']} {entry['installed_version']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("remote", "oci"))
    parser.add_argument("target", help="layout OCI ou imagem@sha256:digest remoto")
    parser.add_argument("reports", nargs="?", default="reports")
    args = parser.parse_args()
    try:
        summary = report_unfixed_cves(args.mode, args.target, Path(args.reports))
    except SCAN_ERRORS as error:
        # Falha ao coletar visibilidade é reportada, mas não é o gate de
        # segurança — nunca retorna código de erro pro chamador.
        print(f"aviso: não foi possível coletar CVEs sem correção: {error}")
        return 0
    print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
