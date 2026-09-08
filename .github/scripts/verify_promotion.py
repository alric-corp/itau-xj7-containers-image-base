#!/usr/bin/env python3
"""Exige plataformas, assinatura e provenance da main antes da promoção."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from image_reference import require_digest_reference


def verify_promotion(image, repository, reports=Path("reports")):
    require_digest_reference(image)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("repositório de origem inválido")
    reports.mkdir(parents=True, exist_ok=True)
    raw = subprocess.run(["docker", "buildx", "imagetools", "inspect", "--raw", image],
                         check=True, capture_output=True, text=True).stdout
    index = json.loads(raw)
    if index.get("mediaType") not in {
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
    }:
        raise ValueError("candidato não é índice multi-arquitetura")
    platforms = [f"{entry['platform']['os']}/{entry['platform']['architecture']}"
                 for entry in index["manifests"]]
    if sorted(platforms) != ["linux/amd64", "linux/arm64"]:
        raise ValueError("índice deve conter exatamente amd64 e arm64")
    (reports / "candidate-index.json").write_text(raw)
    workflow = f"{repository}/.github/workflows/build-base-images.yml"
    commands = {
        "signature": ["cosign", "verify", "--certificate-identity",
                      f"https://github.com/{workflow}@refs/heads/main",
                      "--certificate-oidc-issuer", "https://token.actions.githubusercontent.com", image],
        "provenance": ["gh", "attestation", "verify", f"oci://{image}", "--repo", repository,
                       "--signer-workflow", workflow, "--source-ref", "refs/heads/main", "--format", "json"],
    }
    for name, command in commands.items():
        output = subprocess.run(command, check=True, capture_output=True, text=True).stdout
        if not json.loads(output):
            raise ValueError(f"nenhuma evidência verificada: {name}")
        (reports / f"{name}.json").write_text(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image")
    parser.add_argument("repository")
    args = parser.parse_args()
    try:
        verify_promotion(args.image, args.repository)
    except subprocess.CalledProcessError as error:
        print(error.stderr or str(error), file=sys.stderr)
        return error.returncode
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        print(f"verificação da promoção falhou: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
