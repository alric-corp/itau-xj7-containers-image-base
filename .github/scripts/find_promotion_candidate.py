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
import os
import sys


def emit(key: str, value: str) -> None:
    with open(os.environ["GITHUB_OUTPUT"], "a") as fh:
        fh.write(f"{key}={value}\n")


def main() -> None:
    images_path, soak_hours_s, registry, repo = sys.argv[1:5]
    soak_hours = float(soak_hours_s)

    with open(images_path) as f:
        details = json.load(f)["imageDetails"]

    # `aws ecr describe-images --output json` serializa imagePushedAt como
    # string ISO 8601 (ex.: "2026-09-07T22:57:53.682000-03:00"), não como
    # epoch numérico — fromisoformat entende esse formato (com offset e
    # microssegundos) diretamente.
    now = datetime.datetime.now(datetime.timezone.utc)
    cutoff = now - datetime.timedelta(hours=soak_hours)

    # Builds imutáveis (qualquer tag != "stable"), mais recente primeiro.
    candidates = []
    for img in details:
        tags = img.get("imageTags", [])
        immutable_tags = [t for t in tags if t != "stable"]
        if not immutable_tags:
            continue
        pushed_at = datetime.datetime.fromisoformat(img["imagePushedAt"])
        candidates.append((pushed_at, immutable_tags[0], img["imageDigest"]))
    candidates.sort(key=lambda c: c[0], reverse=True)

    if not candidates:
        print(f"{repo}: nenhum build imutável encontrado, nada a promover")
        emit("skip", "true")
        return

    pushed_at, tag, digest = candidates[0]
    if pushed_at > cutoff:
        remaining = pushed_at - cutoff
        remaining_h = remaining.total_seconds() / 3600
        print(f"{repo}: build {tag} ainda dentro da janela de soak (~{remaining_h:.1f}h restantes)")
        emit("skip", "true")
        return

    print(f"{repo}: build {tag} passou da janela de soak, candidato à promoção")
    emit("skip", "false")
    emit("tag", tag)
    emit("digest", digest)
    emit("image", f"{registry}/{repo}")


if __name__ == "__main__":
    main()
