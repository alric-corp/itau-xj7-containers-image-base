#!/usr/bin/env python3
"""Encontra, num repositório ECR, o build imutável mais recente que já
passou da janela de soak e ainda não é a tag "stable" — usado pelo
workflow promote-stable.yml (canário automático).

Uso:
    python3 find_promotion_candidate.py <images.json> <soak_hours> <registry> <repo> [quarantine.json]

<images.json> é a saída de `aws ecr describe-images --repository-name <repo>
--output json`. Escreve o resultado no arquivo apontado por $GITHUB_OUTPUT
(skip, tag, digest, image).

[quarantine.json] é opcional (ver M15/.github/promotion-quarantine.json):
um digest retirado de `stable` por `recover-stable.yml` continua sendo o
build mais recente por timestamp — sem essa lista, o próximo ciclo de
promoção o selecionaria de novo, desfazendo a recuperação. Formato:
{"<repo>": [{"digest": "sha256:...", ...}, ...]}. Arquivo ausente ou sem
entrada para o repo não exclui nada (comportamento anterior preservado).
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


def build_tag_order(tag):
    parts = tag.split("-")
    return (datetime.datetime.strptime("-".join(parts[:2]), "%d%m%y-%H%M"),
            int(parts[2][1:]) if len(parts) > 2 else 0,
            int(parts[3][1:]) if len(parts) > 3 else 0)


def select_candidate(details: list, soak_hours: float, now: datetime.datetime,
                      quarantined_digests: frozenset = frozenset()):
    """Seleciona um índice elegível sem regredir em relação ao stable atual.

    O tipo do manifest filtra artefatos auxiliares; não substitui a verificação
    remota de plataformas, assinatura e provenance antes da promoção.

    `quarantined_digests` exclui explicitamente builds retirados de `stable`
    por `recover-stable.yml` (M15) — sem isso, um build mais novo que o
    `stable` restaurado continuaria elegível por timestamp e o próximo ciclo
    de promoção desfaria a recuperação.
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
        if img["imageDigest"] in quarantined_digests:
            continue
        if img.get("imageManifestMediaType") not in IMAGE_INDEX_TYPES:
            continue
        build_tags = [tag for tag in img.get("imageTags", []) if is_build_tag(tag)]
        if not build_tags:
            continue
        timestamp = pushed_at(img)
        if timestamp > cutoff or (stable_time is not None and timestamp <= stable_time):
            continue
        # O rótulo mais recente é informativo; a elegibilidade usa o push ECR.
        tag = max(build_tags, key=build_tag_order)
        candidates.append((timestamp, tag, img["imageDigest"]))

    return max(candidates, default=None)


def emit(key: str, value: str) -> None:
    with open(os.environ["GITHUB_OUTPUT"], "a") as fh:
        fh.write(f"{key}={value}\n")


def load_quarantined_digests(quarantine_path: str, repo: str) -> frozenset:
    try:
        with open(quarantine_path) as f:
            data = json.load(f)
    except FileNotFoundError:
        return frozenset()
    entries = data.get(repo, [])
    return frozenset(entry["digest"] for entry in entries)


def main() -> None:
    images_path, soak_hours_s, registry, repo = sys.argv[1:5]
    quarantine_path = sys.argv[5] if len(sys.argv) > 5 else None
    soak_hours = float(soak_hours_s)

    with open(images_path) as f:
        details = json.load(f)["imageDetails"]

    quarantined = load_quarantined_digests(quarantine_path, repo) if quarantine_path else frozenset()

    now = datetime.datetime.now(datetime.timezone.utc)
    candidate = select_candidate(details, soak_hours, now, quarantined)

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
