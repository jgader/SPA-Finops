"""Neutraliza payload de fórmula/CSV injection em qualquer valor exposto via preview/export
(nunca nos dados persistidos como cost_usage — só na camada de apresentação)."""

_DANGEROUS_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_cell(value: str) -> str:
    if value and value[0] in _DANGEROUS_PREFIXES:
        return "'" + value
    return value
