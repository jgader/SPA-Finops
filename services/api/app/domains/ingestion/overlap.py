"""Detecção de SOBREPOSIÇÃO FINANCEIRA — mecanismo (b) da seção 4 do plano. Isolado de
dedup.py por desenho: este módulo só lê/escreve Dataset e DatasetOverlapFlag, nunca
ImportBatch.sha256. Nunca resolve nada automaticamente — só sinaliza (dataset_overlap_flag
sempre nasce com resolution='pending'), e nunca exclui ou substitui uma linha ou dataset."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.canonical_financial.models import Dataset, DatasetOverlapFlag


def find_overlapping_datasets(
    session: Session, provider: str, scope_key: str, period_start: datetime, period_end: datetime
) -> list[Dataset]:
    """Pergunta (b) da seção 4: existe dataset committed do mesmo provider+scope cujo
    período se sobrepõe ao deste novo dataset? Só considera datasets já committed —
    um dataset nunca existe em outro estado nesta tabela."""
    stmt = select(Dataset).where(
        Dataset.provider == provider,
        Dataset.scope_key == scope_key,
        Dataset.period_start <= period_end,
        Dataset.period_end >= period_start,
    )
    return list(session.execute(stmt).scalars().all())


def existing_flag_for(
    session: Session, pending_import_batch_id: uuid.UUID, overlapping_dataset_id: uuid.UUID
) -> DatasetOverlapFlag | None:
    stmt = select(DatasetOverlapFlag).where(
        DatasetOverlapFlag.pending_import_batch_id == pending_import_batch_id,
        DatasetOverlapFlag.overlapping_dataset_id == overlapping_dataset_id,
    )
    return session.execute(stmt).scalar_one_or_none()


def ensure_pending_flag(
    session: Session,
    pending_import_batch_id: uuid.UUID,
    overlapping_dataset: Dataset,
    scope_key: str,
    period_start: datetime,
    period_end: datetime,
) -> DatasetOverlapFlag:
    """Nunca resolve nada automaticamente: cria (ou reaproveita) a sinalização,
    sempre nascendo/pendente até decisão humana explícita via resolve_overlap()."""
    flag = existing_flag_for(session, pending_import_batch_id, overlapping_dataset.id)
    if flag is not None:
        return flag
    flag = DatasetOverlapFlag(
        dataset_id=None,
        pending_import_batch_id=pending_import_batch_id,
        overlapping_dataset_id=overlapping_dataset.id,
        scope_key=scope_key,
        period_start=max(period_start, overlapping_dataset.period_start),
        period_end=min(period_end, overlapping_dataset.period_end),
        detected_at=datetime.now(timezone.utc),
        resolution="pending",
    )
    session.add(flag)
    session.flush()
    return flag


def resolve_overlap(
    session: Session, flag: DatasetOverlapFlag, resolution: str, resolved_by: str
) -> DatasetOverlapFlag:
    """Decisão humana explícita — nunca automática. 'replace_approved' não tem implementação
    de supersessão de dataset em F1 (exigiria versionamento que não existe no schema mínimo);
    aceitar a decisão aqui só registra a intenção, o commit continua bloqueado até F2/F3."""
    flag.resolution = resolution
    flag.resolved_by = resolved_by
    flag.resolved_at = datetime.now(timezone.utc)
    return flag
