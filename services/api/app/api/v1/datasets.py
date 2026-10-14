import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.domains.canonical_financial.models import (
    CostUsage,
    Dataset,
    DatasetOverlapFlag,
    ImportRowRejection,
)
from app.schemas.datasets import DatasetQualityResponse, DatasetSummary, DuplicateCandidate

router = APIRouter(prefix="/api/v1/datasets", tags=["datasets"])


@router.get("", response_model=list[DatasetSummary])
def list_datasets(session: Session = Depends(get_session)) -> list[DatasetSummary]:
    datasets = session.execute(select(Dataset)).scalars().all()
    return [
        DatasetSummary(
            id=str(d.id),
            provider=d.provider,
            scope_key=d.scope_key,
            period_start=d.period_start.isoformat(),
            period_end=d.period_end.isoformat(),
            currency_set=d.currency_set,
            row_count=d.row_count,
            granularity=d.granularity,
            granularity_source=d.granularity_source,
            ingestion_version=d.ingestion_version,
        )
        for d in datasets
    ]


@router.get("/{dataset_id}/quality", response_model=DatasetQualityResponse)
def dataset_quality(dataset_id: uuid.UUID, session: Session = Depends(get_session)) -> DatasetQualityResponse:
    dataset = session.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="dataset não encontrado")

    severity_counts = dict(
        session.execute(
            select(ImportRowRejection.severity, func.count())
            .where(ImportRowRejection.import_batch_id == dataset.import_batch_id)
            .group_by(ImportRowRejection.severity)
        ).all()
    )

    return DatasetQualityResponse(
        dataset_id=str(dataset.id),
        import_batch_id=str(dataset.import_batch_id),
        row_count=dataset.row_count,
        rejections_by_severity=severity_counts,
    )


@router.get("/{dataset_id}/overlap/{flag_id}/candidates", response_model=list[DuplicateCandidate])
def overlap_candidates(
    dataset_id: uuid.UUID, flag_id: uuid.UUID, session: Session = Depends(get_session)
) -> list[DuplicateCandidate]:
    """Terceira identidade (lançamento financeiro potencialmente duplicado, ajuste 2 do GO
    condicional) — só leitura, nenhuma ação de exclusão ou merge em F1."""
    flag = session.get(DatasetOverlapFlag, flag_id)
    if flag is None:
        raise HTTPException(status_code=404, detail="dataset_overlap_flag não encontrado")

    other_dataset_id = flag.overlapping_dataset_id
    this_hashes = select(CostUsage.natural_key_hash).where(CostUsage.dataset_id == dataset_id)
    other_rows = session.execute(
        select(CostUsage).where(
            CostUsage.dataset_id == other_dataset_id, CostUsage.natural_key_hash.in_(this_hashes)
        )
    ).scalars().all()

    return [
        DuplicateCandidate(
            cost_usage_id=str(row.id),
            natural_key_hash=row.natural_key_hash,
            service=row.service,
            resource_id=row.resource_id,
            billing_start=row.billing_start.isoformat(),
            billing_end=row.billing_end.isoformat(),
            billed_cost=str(row.billed_cost),
            currency=row.currency,
        )
        for row in other_rows
    ]
