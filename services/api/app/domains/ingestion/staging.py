"""Orquestra sniff → adapter → validação → persistência de mapping/rejeições → status.
Não grava nenhuma linha de cost_usage (isso só acontece em commit.py, dentro da
transação protegida por scope_lock+fencing token)."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.domains.canonical_financial.models import ImportBatch, ImportRowRejection
from app.domains.ingestion.adapters import find_adapter
from app.domains.ingestion.adapters.base import ProviderAdapter
from app.domains.ingestion.errors import SchemaNotRecognized
from app.domains.ingestion.field_mapping import persist_mapping
from app.domains.ingestion.sniffing import UnsniffableFile, read_header, sniff_sample
from app.domains.ingestion.validation import ValidationResult, validate_file


@dataclass
class StagingOutcome:
    status: str  # staged | rejected
    adapter: ProviderAdapter
    encoding: str
    delimiter: str
    validation: ValidationResult


def stage_import_batch(session: Session, batch: ImportBatch, file_path: str) -> StagingOutcome:
    try:
        encoding, delimiter = sniff_sample(file_path)
        header = read_header(file_path, encoding, delimiter)
    except UnsniffableFile as exc:
        raise SchemaNotRecognized(str(exc)) from exc

    adapter = find_adapter(header)
    if adapter is None:
        raise SchemaNotRecognized("no_adapter_identified_header")

    batch.provider = adapter.provider
    batch.schema_version = adapter.schema_version

    validation = validate_file(file_path, encoding, delimiter, adapter, batch.sha256)
    persist_mapping(session, batch.id, adapter.field_mapping())
    _persist_rejections(session, batch.id, validation)

    batch.status = "rejected" if validation.has_blocking_errors else "staged"
    return StagingOutcome(
        status=batch.status, adapter=adapter, encoding=encoding, delimiter=delimiter, validation=validation
    )


def _persist_rejections(session: Session, import_batch_id: uuid.UUID, validation: ValidationResult) -> None:
    now = datetime.now(timezone.utc)
    seen: set[tuple[int, str]] = set()
    for issue in validation.issues:
        key = (issue.row_offset, issue.reason_code)
        if key in seen:
            continue
        seen.add(key)
        session.add(
            ImportRowRejection(
                import_batch_id=import_batch_id,
                row_offset=issue.row_offset,
                raw_excerpt_ref=f"{import_batch_id}:{issue.row_offset}",
                severity=issue.severity,
                reason_code=issue.reason_code,
                field=issue.field,
                created_at=now,
            )
        )
