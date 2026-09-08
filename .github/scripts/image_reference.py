"""Validação compartilhada de referências imutáveis usadas pelos subprocessos."""
import re


def require_digest_reference(image):
    if not isinstance(image, str) or not re.fullmatch(r"[^\s@]+@sha256:[0-9a-f]{64}", image) or image.startswith("-"):
        raise ValueError("imagem deve ser referenciada por digest SHA-256")
