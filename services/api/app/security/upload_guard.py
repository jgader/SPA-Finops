"""Limite de upload, streaming, validação de formato por magic bytes e limite de
descompactação (seção 8 do plano). Nada aqui lê o arquivo inteiro em memória de uma vez."""

import gzip
import os

from app.config.settings import settings

CHUNK_SIZE = 1024 * 1024

_MAGIC_PARQUET = b"PAR1"
_MAGIC_GZIP = b"\x1f\x8b"
_BINARY_SIGNATURES_INCOMPATIBLE_WITH_CSV = [b"\x7fELF", b"MZ", _MAGIC_GZIP, _MAGIC_PARQUET]


class UploadRejected(Exception):
    pass


class UploadTooLarge(UploadRejected):
    pass


class UnsupportedFormat(UploadRejected):
    pass


class DecompressionLimitExceeded(UploadRejected):
    pass


def validate_extension(filename: str) -> str:
    lowered = filename.lower()
    for ext in settings.allowed_extensions_list:
        if lowered.endswith(ext):
            return ext
    raise UnsupportedFormat(f"extensão não permitida: {filename}")


def save_upload_stream(file_like, destination_path: str, max_bytes: int | None = None) -> int:
    """Grava em chunks, abortando (e removendo o arquivo parcial) se exceder max_bytes —
    nunca lê o conteúdo integral em memória antes de decidir."""
    limit = max_bytes if max_bytes is not None else settings.upload_max_bytes
    total = 0
    with open(destination_path, "wb") as out:
        while True:
            chunk = file_like.read(CHUNK_SIZE)
            if not chunk:
                break
            total += len(chunk)
            if total > limit:
                out.close()
                os.remove(destination_path)
                raise UploadTooLarge(f"upload excede o limite de {limit} bytes")
            out.write(chunk)
    return total


def validate_magic_bytes(file_path: str, extension: str) -> None:
    with open(file_path, "rb") as handle:
        head = handle.read(8)

    if extension == ".parquet":
        if not head.startswith(_MAGIC_PARQUET):
            raise UnsupportedFormat("conteúdo não corresponde a Parquet (magic bytes ausentes)")
        return

    if extension == ".csv.gz":
        if not head.startswith(_MAGIC_GZIP):
            raise UnsupportedFormat("conteúdo não corresponde a gzip (magic bytes ausentes)")
        return

    # .csv: rejeita se o conteúdo na verdade é um binário conhecido disfarçado de .csv
    for signature in _BINARY_SIGNATURES_INCOMPATIBLE_WITH_CSV:
        if head.startswith(signature):
            raise UnsupportedFormat("conteúdo binário incompatível com extensão .csv declarada")


def decompress_gzip_with_limit(compressed_path: str, destination_path: str) -> int:
    """Protege contra zip bomb: aborta se o volume descomprimido exceder o teto absoluto
    ou a razão configurada em relação ao tamanho comprimido — o menor dos dois vence."""
    compressed_size = os.path.getsize(compressed_path)
    ratio_limit = compressed_size * settings.upload_decompression_max_ratio
    absolute_limit = settings.upload_decompression_max_bytes
    limit = min(ratio_limit, absolute_limit)

    total = 0
    with gzip.open(compressed_path, "rb") as src, open(destination_path, "wb") as dst:
        while True:
            chunk = src.read(CHUNK_SIZE)
            if not chunk:
                break
            total += len(chunk)
            if total > limit:
                dst.close()
                os.remove(destination_path)
                raise DecompressionLimitExceeded(
                    f"conteúdo descomprimido excede o limite de {limit} bytes (comprimido={compressed_size})"
                )
            dst.write(chunk)
    return total


def redact_for_log(message: str) -> str:
    """Nunca usado para aprovar dado a ser logado — é só um fallback defensivo; a regra real
    é os módulos de domínio nunca colocarem valor financeiro em string de log (ver
    docs/PLANO_EXECUCAO_F1.md seção 8). Mantido simples: não há PII/custo aqui para redigir
    além do que já é responsabilidade do chamador não logar."""
    return message
