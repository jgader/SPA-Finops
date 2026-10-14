"""Sniff de delimitador, encoding e cabeçalho — nunca assume formato, detecta."""

import csv
import io


class UnsniffableFile(Exception):
    pass


def sniff_encoding(sample_bytes: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            sample_bytes.decode(encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    raise UnsniffableFile("encoding_not_detected")


def sniff_delimiter(sample_text: str) -> str:
    try:
        dialect = csv.Sniffer().sniff(sample_text, delimiters=",;\t|")
        return dialect.delimiter
    except csv.Error:
        return ","


def read_header(file_path: str, encoding: str, delimiter: str) -> list[str]:
    with open(file_path, encoding=encoding, newline="") as handle:
        reader = csv.reader(handle, delimiter=delimiter)
        try:
            return next(reader)
        except StopIteration:
            raise UnsniffableFile("empty_file")


def iter_rows(file_path: str, encoding: str, delimiter: str):
    """Gera (row_offset, dict_da_linha) a partir do offset 1 (0 é o cabeçalho)."""
    with open(file_path, encoding=encoding, newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        for offset, row in enumerate(reader, start=1):
            yield offset, row


def sniff_sample(file_path: str, sample_size: int = 65536) -> tuple[str, str]:
    with open(file_path, "rb") as handle:
        sample_bytes = handle.read(sample_size)
    encoding = sniff_encoding(sample_bytes)
    sample_text = sample_bytes.decode(encoding)
    delimiter = sniff_delimiter(sample_text)
    return encoding, delimiter


def line_count_estimate(file_path: str, encoding: str) -> int:
    with open(file_path, encoding=encoding, newline="") as handle:
        return sum(1 for _ in handle) - 1
