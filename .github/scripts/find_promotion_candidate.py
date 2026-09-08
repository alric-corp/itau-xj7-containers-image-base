#!/usr/bin/env python3
"""Encontra, num repositório ECR, o build imutável mais recente que já
passou da janela de soak e ainda não é a tag "stable" — usado pelo
workflow promote-stable.yml (canário automático).

Uso:
    python3 find_promotion_candidate.py <images.json> <soak_hours> <registry> <repo>

<images.json> é a saída de `aws ecr describe-images --repository-name <repo>
--output json`. Escreve o resultado no arquivo apontado por $GITHUB_OUTPUT
(skip, tag, digest, image).
"""
import datetime
import json
import math
import os
import re
import sys


IMAGE_INDEX_TYPES = {
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
}


def pushed_at(image: dict) -> datetime.datetime:
    timestamp = datetime.datetime.fromisoformat(image["imagePushedAt"])
    if timestamp.tzinfo is None:
        raise ValueError("imagePushedAt deve incluir o fuso horário")
    return timestamp


def is_build_tag(tag: str) -> bool:
    # Mantém compatibilidade com builds anteriores à identificação por run.
    match = re.fullmatch(r"([0-9]{6}-[0-9]{4})(?:-r[1-9][0-9]*-a[1-9][0-9]*)?", tag)
    if not match:
        return False
    try:
        datetime.datetime.strptime(match[1], "%d%m%y-%H%M")
    except ValueError:
        return False
    return True


def select_candidate(details: list, soak_hours: float, now: datetime.datetime):
    """Seleciona um índice elegível sem regredir em relação ao stable atual.

    O tipo do manifest filtra artefatos auxiliares; não substitui a verificação
    remota de plataformas, assinatura e provenance antes da promoção.
    """
    if not math.isfinite(soak_hours) or soak_hours < 0:
        raise ValueError("soak-hours deve ser um número finito maior ou igual a zero")
    cutoff = now - datetime.timedelta(hours=soak_hours)
    stable_images = [img for img in details if "stable" in img.get("imageTags", [])]
    stable_digests = {img["imageDigest"] for img in stable_images}
    stable_time = max((pushed_at(img) for img in stable_images), default=None)

    candidates = []
    for img in details:
        if img["imageDigest"] in stable_digests:
            continue
        if img.get("imageManifestMediaType") not in IMAGE_INDEX_TYPES:
            continue
        build_tags = sorted(tag for tag in img.get("imageTags", []) if is_build_tag(tag))
        if not build_tags:
            continue
        timestamp = pushed_at(img)
        if timestamp > cutoff or (stable_time is not None and timestamp <= stable_time):
            continue
        candidates.append((timestamp, build_tags[0], img["imageDigest"]))

    return max(candidates, default=None)


def emit(key: str, value: str) -> None:
    with open(os.environ["GITHUB_OUTPUT"], "a") as fh:
        fh.write(f"{key}={value}\n")


def main() -> None:
    images_path, soak_hours_s, registry, repo = sys.argv[1:5]
    soak_hours = float(soak_hours_s)

    with open(images_path) as f:
        details = json.load(f)["imageDetails"]

    now = datetime.datetime.now(datetime.timezone.utc)
    candidate = select_candidate(details, soak_hours, now)

    if candidate is None:
        print(f"{repo}: nenhum build elegível mais novo que stable, nada a promover")
        emit("skip", "true")
        return

    _, tag, digest = candidate
    print(f"{repo}: build {tag} passou da janela de soak, candidato à promoção")
    emit("skip", "false")
    emit("tag", tag)
    emit("digest", digest)
    emit("image", f"{registry}/{repo}")


if __name__ == "__main__":
    main()
