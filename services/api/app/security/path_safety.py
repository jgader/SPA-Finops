"""Proteção contra manipulação de caminho (ajuste de segurança do GO condicional). O nome
original do arquivo do usuário NUNCA compõe um caminho em disco — todo caminho de escrita é
construído a partir de IDs internos (import_batch.id, sha256) e passa por safe_join(), que
resolve o caminho final e garante que ele está contido dentro do diretório base permitido."""

import os


class PathTraversalRejected(Exception):
    pass


def safe_join(base_dir: str, *parts: str) -> str:
    base_real = os.path.realpath(base_dir)
    candidate = os.path.realpath(os.path.join(base_real, *parts))
    if not (candidate == base_real or candidate.startswith(base_real + os.sep)):
        raise PathTraversalRejected(f"caminho resolvido fora do diretório base: {candidate}")
    return candidate


def sanitize_display_filename(original_filename: str) -> str:
    """Só para EXIBIÇÃO (metadado) — nunca usado para compor caminho em disco."""
    name = os.path.basename(original_filename.replace("\\", "/"))
    cleaned = "".join(ch if (ch.isalnum() or ch in "._- ") else "_" for ch in name)
    return cleaned[:255] or "arquivo_sem_nome"
