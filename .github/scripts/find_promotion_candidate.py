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
import json
import os
import sys
import time


def emit(key: str, value: str) -> None:
    with open(os.environ["GITHUB_OUTPUT"], "a") as fh:
        fh.write(f"{key}={value}\n")


def main() -> None:
    images_path, soak_hours_s, registry, repo = sys.argv[1:5]
    soak_hours = float(soak_hours_s)

    with open(images_path) as f:
        details = json.load(f)["imageDetails"]

    cutoff = time.time() - soak_hours * 3600

    # Builds imutáveis (qualquer tag != "stable"), mais recente primeiro.
    candidates = []
    for img in details:
        tags = img.get("imageTags", [])
        immutable_tags = [t for t in tags if t != "stable"]
        if not immutable_tags:
            continue
        candidates.append((img["imagePushedAt"], immutable_tags[0], img["imageDigest"]))
    candidates.sort(key=lambda c: c[0], reverse=True)

    if not candidates:
        print(f"{repo}: nenhum build imutável encontrado, nada a promover")
        emit("skip", "true")
        return

    pushed_at, tag, digest = candidates[0]
    if pushed_at > cutoff:
        remaining_h = (pushed_at - cutoff) / 3600
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
