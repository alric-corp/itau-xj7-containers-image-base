#!/usr/bin/env python3
"""Encontra, num repositório ECR, o build imutável mais recente que já
passou da janela de soak e ainda não é a tag "stable" — usado pelo
workflow promote-stable.yml (canário automático).

Uso:
    python3 find_promotion_candidate.py <images.json> <soak_hours> <registry> <repo> [quarantine.json] [--evidence <arquivo>]

<images.json> é a saída de `aws ecr describe-images --repository-name <repo>
--output json`. Escreve o resultado no arquivo apontado por $GITHUB_OUTPUT
(skip, tag, digest, image).

[quarantine.json] é opcional (ver M15/policies/release/promotion-quarantine.json):
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
import pathlib
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


def skip_reason(details: list, soak_hours: float, now: datetime.datetime,
                quarantined: frozenset) -> str:
    """Por que não há candidato: M11 exige o motivo, não só o resultado.

    Reconstrói a decisão a partir dos mesmos dados de `select_candidate`, sem
    alterar a seleção — a tabela do run precisa distinguir "nada novo para
    promover" de "o único candidato está em quarentena" ou "ainda no soak".
    """
    indexes = [img for img in details
               if img.get("imageManifestMediaType") in IMAGE_INDEX_TYPES
               and any(is_build_tag(tag) for tag in img.get("imageTags", []))]
    if not indexes:
        return "nenhum índice multi-arquitetura com tag de build no repositório"
    stable = [img for img in details if "stable" in img.get("imageTags", [])]
    stable_digests = {img["imageDigest"] for img in stable}
    stable_time = max((pushed_at(img) for img in stable), default=None)
    newer = [img for img in indexes if img["imageDigest"] not in stable_digests]
    if not newer:
        return "o build mais recente já é o stable atual"
    if all(img["imageDigest"] in quarantined for img in newer):
        return "todos os builds mais novos estão em quarentena (M15)"
    cutoff = now - datetime.timedelta(hours=soak_hours)
    outside = [img for img in newer if img["imageDigest"] not in quarantined
               and pushed_at(img) <= cutoff]
    if not outside:
        return f"nenhum build novo completou a janela de soak de {soak_hours}h"
    if stable_time is not None and all(pushed_at(img) <= stable_time for img in outside):
        return "os builds elegíveis são anteriores ao stable atual (sem regressão)"
    return "nenhum candidato elegível"


def stable_state(details: list, now: datetime.datetime) -> dict:
    """Idade real da tag stable, medida pelo push no ECR."""
    stable = [img for img in details if "stable" in img.get("imageTags", [])]
    if not stable:
        return {"stable_digest": None, "stable_pushed_at": None, "stable_age_hours": None}
    newest = max(stable, key=pushed_at)
    return {"stable_digest": newest["imageDigest"],
            "stable_pushed_at": newest["imagePushedAt"],
            "stable_age_hours": round((now - pushed_at(newest)).total_seconds() / 3600, 2)}


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
    arguments = [value for value in sys.argv[1:] if not value.startswith("--")]
    evidence_path = None
    for index, value in enumerate(sys.argv[1:]):
        if value == "--evidence":
            evidence_path = sys.argv[index + 2]
    images_path, soak_hours_s, registry, repo = arguments[:4]
    quarantine_path = arguments[4] if len(arguments) > 4 else None
    soak_hours = float(soak_hours_s)

    with open(images_path) as f:
        details = json.load(f)["imageDetails"]

    quarantined = load_quarantined_digests(quarantine_path, repo) if quarantine_path else frozenset()

    now = datetime.datetime.now(datetime.timezone.utc)
    candidate = select_candidate(details, soak_hours, now, quarantined)
    evidence = dict(stable_state(details, now), repository=repo, soak_hours=soak_hours,
                    evaluated_at=now.isoformat(), promoted=False, candidate_digest=None,
                    stable_digest_observed=None, read_back_status='not_run')

    if candidate is None:
        reason = skip_reason(details, soak_hours, now, quarantined)
        print(f"{repo}: nenhum build elegível mais novo que stable, nada a promover ({reason})")
        emit("skip", "true")
        emit("reason", reason)
        evidence["reason"] = reason
        write_evidence(evidence_path, evidence)
        return

    _, tag, digest = candidate
    print(f"{repo}: build {tag} passou da janela de soak, candidato à promoção")
    emit("skip", "false")
    emit("reason", "candidato elegível")
    emit("tag", tag)
    emit("digest", digest)
    emit("image", f"{registry}/{repo}")
    # `promoted` continua falso até o workflow confirmar a escrita e o read-back.
    evidence.update(reason="candidato elegível", tag=tag, digest=digest, candidate_digest=digest,
                    image=f"{registry}/{repo}")
    write_evidence(evidence_path, evidence)


def write_evidence(path, evidence: dict) -> None:
    if not path:
        return
    target = pathlib.Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(evidence, indent=2) + "\n")


if __name__ == "__main__":
    main()
