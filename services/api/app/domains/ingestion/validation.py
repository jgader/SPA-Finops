"""Orquestra o adapter sobre as linhas do arquivo. Taxonomia de severidade e bloqueio de
commit: docs/PLANO_EXECUCAO_F1.md seção 7-bis — qualquer 'error' bloqueia o batch inteiro,
sem limiar percentual (ajuste explícito do GO condicional, revertendo a v2.0)."""

from dataclasses import dataclass

from app.domains.ingestion.adapters.base import MappedRow, ProviderAdapter, RowIssue
from app.domains.ingestion.sniffing import iter_rows


@dataclass
class ValidationResult:
    rows: list[MappedRow]
    issues: list[RowIssue]

    @property
    def has_blocking_errors(self) -> bool:
        return any(issue.severity == "error" for issue in self.issues)


def validate_file(file_path: str, encoding: str, delimiter: str, adapter: ProviderAdapter, sha256: str) -> ValidationResult:
    rows: list[MappedRow] = []
    issues: list[RowIssue] = []

    for row_offset, raw in iter_rows(file_path, encoding, delimiter):
        raw_ref = f"{sha256}:{row_offset}"
        result = adapter.map_row(raw, row_offset, raw_ref)
        issues.extend(result.issues)
        if result.row is not None:
            rows.append(result.row)

    return ValidationResult(rows=rows, issues=issues)
