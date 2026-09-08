#!/usr/bin/env python3
"""Prepara e verifica um layout OCI multi-arquitetura para cópia por digest."""
import argparse
import hashlib
import json
from pathlib import Path
import re

INDEX = "application/vnd.oci.image.index.v1+json"
MANIFEST = "application/vnd.oci.image.manifest.v1+json"


def blob(layout, descriptor):
    digest = descriptor["digest"]
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise ValueError("digest OCI inválido")
    path = layout / "blobs" / "sha256" / digest.split(":")[1]
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    if path.stat().st_size != descriptor["size"] or h.hexdigest() != digest.split(":")[1]:
        raise ValueError(f"blob OCI alterado: {digest}")
    return path


def verify(layout):
    layout = Path(layout)
    entries = json.loads((layout / "index.json").read_text())["manifests"]
    if len(entries) != 1 or entries[0]["mediaType"] != INDEX:
        raise ValueError("layout deve conter um único índice multi-arquitetura")
    index = json.loads(blob(layout, entries[0]).read_text())
    platforms = {}
    for entry in index["manifests"]:
        platform = entry["platform"]
        name = f"{platform['os']}/{platform['architecture']}"
        if name not in {"linux/amd64", "linux/arm64"} or name in platforms:
            raise ValueError("plataforma ausente, inesperada ou duplicada")
        if entry["mediaType"] != MANIFEST:
            raise ValueError("entrada não é manifest de imagem OCI")
        manifest = json.loads(blob(layout, entry).read_text())
        config = json.loads(blob(layout, manifest["config"]).read_text())
        if config["architecture"] != platform["architecture"] or config["os"] != platform["os"]:
            raise ValueError("plataforma do config diverge do índice")
        for layer in manifest["layers"]:
            blob(layout, layer)
        platforms[name] = entry["digest"]
    if set(platforms) != {"linux/amd64", "linux/arm64"}:
        raise ValueError("índice deve conter amd64 e arm64")
    return {"digest": entries[0]["digest"], "platforms": platforms}


def prepare(layout):
    layout = Path(layout)
    raw = (layout / "index.json").read_bytes()
    index = json.loads(raw)
    if index["mediaType"] != INDEX:
        raise ValueError("saída apko não é índice OCI")
    digest = hashlib.sha256(raw).hexdigest()
    (layout / "blobs" / "sha256" / digest).write_bytes(raw)
    wrapper = {"schemaVersion": 2, "mediaType": INDEX, "manifests": [{
        "mediaType": INDEX, "size": len(raw), "digest": f"sha256:{digest}",
        "annotations": {"org.opencontainers.image.ref.name": "image"},
    }]}
    (layout / "index.json").write_text(json.dumps(wrapper))
    evidence = verify(layout)
    (layout / "validated-index.json").write_text(json.dumps(evidence, indent=2) + "\n")
    return evidence


def platform_view(layout, architecture, destination):
    """Expõe um único manifest ao scanner, reutilizando os blobs originais."""
    layout, destination = Path(layout).resolve(), Path(destination)
    root = json.loads((layout / "index.json").read_text())["manifests"][0]
    index = json.loads(blob(layout, root).read_text())
    entries = [entry for entry in index["manifests"]
               if entry["platform"] == {"os": "linux", "architecture": architecture}]
    if len(entries) != 1:
        raise ValueError("plataforma não encontrada ou ambígua")
    (destination / "index.json").write_text(json.dumps({"schemaVersion": 2, "mediaType": INDEX,
                                                      "manifests": entries}))
    (destination / "oci-layout").write_text('{"imageLayoutVersion":"1.0.0"}')
    (destination / "blobs").symlink_to(layout / "blobs", target_is_directory=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "verify"))
    parser.add_argument("layout")
    args = parser.parse_args()
    result = prepare(args.layout) if args.command == "prepare" else verify(args.layout)
    if args.command == "verify":
        expected = json.loads((Path(args.layout) / "validated-index.json").read_text())
        if result != expected:
            raise ValueError("índice diverge da evidência de validação")
    print(result["digest"])
