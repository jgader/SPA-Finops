"""Persistência auditável do mapeamento de campos (critério 2 — lacuna nova do plano v2.0).
Cada registro é imutável; uma correção manual é um INSERT novo, nunca um UPDATE."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.domains.canonical_financial.models import ImportFieldMapping
from app.domains.ingestion.adapters.base import FieldMappingEntry


def persist_mapping(session: Session, import_batch_id: uuid.UUID, entries: list[FieldMappingEntry]) -> None:
    now = datetime.now(timezone.utc)
    for entry in entries:
        session.add(
            ImportFieldMapping(
                import_batch_id=import_batch_id,
                source_field=entry.source_field,
                canonical_field=entry.canonical_field,
                transform_applied=entry.transform_applied,
                confidence=entry.confidence,
                is_manual_override=False,
                created_at=now,
            )
        )


def apply_manual_override(
    session: Session, import_batch_id: uuid.UUID, source_field: str, canonical_field: str
) -> ImportFieldMapping:
    """Correção manual: novo registro, nunca sobrescreve o anterior."""
    entry = ImportFieldMapping(
        import_batch_id=import_batch_id,
        source_field=source_field,
        canonical_field=canonical_field,
        transform_applied="manual_override",
        confidence=1,
        is_manual_override=True,
        created_at=datetime.now(timezone.utc),
    )
    session.add(entry)
    return entry
