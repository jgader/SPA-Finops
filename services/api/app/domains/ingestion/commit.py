"""Commit transacional, idempotente, protegido por scope_lock + fencing token (seção 7/7-ter
do plano). Duas transações deliberadamente separadas — aquisição do lock e escrita final —
porque é exatamente essa janela que permite a um worker antigo "despertar" com um token
obsoleto; sem a separação, o cenário de teste da seção 7-ter não existiria para testar."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.domains.canonical_financial.models import (
    CostUsage,
    Dataset,
    ImportBatch,
    ScopeLock,
)
from app.domains.ingestion import dedup, overlap
from app.domains.ingestion.adapters import find_adapter
from app.domains.ingestion.errors import (
    FencingTokenMismatch,
    NoValidRows,
    ScopeLockHeld,
)
from app.domains.ingestion.granularity import compute_granularity
from app.domains.ingestion.identity import natural_key_hash, scope_key_for
from app.domains.ingestion.sniffing import read_header, sniff_sample
from app.domains.ingestion.validation import validate_file

DEFAULT_LEASE_SECONDS = 60


@dataclass
class CommitOutcome:
    status: str
    dataset_id: uuid.UUID | None = None
    existing_batch_id: uuid.UUID | None = None
    blocking_overlap_dataset_ids: list[uuid.UUID] = field(default_factory=list)


def acquire_scope_lock(session: Session, scope_key: str, job_id: uuid.UUID, lease_seconds: int = DEFAULT_LEASE_SECONDS) -> int:
    """Transação própria, confirmada (commitada) antes de retornar — deliberado, ver docstring
    do módulo. Levanta ScopeLockHeld (transitória) se outro job ainda detém o lock vigente."""
    now = datetime.now(timezone.utc)
    existing = session.execute(
        select(ScopeLock).where(ScopeLock.scope_key == scope_key).with_for_update()
    ).scalar_one_or_none()

    if existing is not None and existing.expires_at > now and existing.held_by_job_id != job_id:
        raise ScopeLockHeld(f"scope_key={scope_key} held by {existing.held_by_job_id} until {existing.expires_at}")

    new_token = session.execute(select(_next_fencing_token())).scalar_one()

    if existing is None:
        session.add(
            ScopeLock(
                scope_key=scope_key,
                held_by_job_id=job_id,
                fencing_token=new_token,
                acquired_at=now,
                expires_at=now + timedelta(seconds=lease_seconds),
            )
        )
    else:
        existing.held_by_job_id = job_id
        existing.fencing_token = new_token
        existing.acquired_at = now
        existing.expires_at = now + timedelta(seconds=lease_seconds)

    session.commit()
    return new_token


def _next_fencing_token():
    from sqlalchemy import func

    return func.nextval("scope_lock_fencing_token_seq")


def force_expire_lock_for_test(session: Session, scope_key: str) -> None:
    """Usado apenas pelo teste de concorrência (tests/failure/test_fencing_token.py) para
    simular a passagem do tempo sem precisar de um sleep real de 30s."""
    session.execute(
        ScopeLock.__table__.update().where(ScopeLock.scope_key == scope_key).values(
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)
        )
    )
    session.commit()


def release_scope_lock(session: Session, scope_key: str) -> None:
    session.execute(delete(ScopeLock).where(ScopeLock.scope_key == scope_key))
    session.commit()


def commit_import_batch(
    session: Session, batch: ImportBatch, job_id: uuid.UUID, file_path: str, held_token: int | None = None
) -> CommitOutcome:
    if batch.status == "committed":
        return CommitOutcome(status="already_committed")

    if batch.status == "rejected":
        return CommitOutcome(status="blocked_by_validation_errors")

    if batch.status != "staged":
        raise ValueError(f"import_batch {batch.id} não está em 'staged' (status={batch.status})")

    duplicate = dedup.find_committed_duplicate(session, batch.sha256)
    if duplicate is not None and duplicate.id != batch.id:
        batch.status = "committed"
        session.commit()
        return CommitOutcome(status="no_op_duplicate", existing_batch_id=duplicate.id)

    encoding, delimiter = sniff_sample(file_path)
    header = read_header(file_path, encoding, delimiter)
    adapter = find_adapter(header)
    validation = validate_file(file_path, encoding, delimiter, adapter, batch.sha256)
    if validation.has_blocking_errors or not validation.rows:
        batch.status = "rejected"
        session.commit()
        if not validation.rows:
            raise NoValidRows("nenhuma linha válida para comitar")
        return CommitOutcome(status="blocked_by_validation_errors")

    rows = validation.rows
    billing_account = rows[0].billing_account  # limitação conhecida: 1 billing_account por batch em F1
    scope_key = scope_key_for(batch.provider, billing_account, kind="cost_and_usage")
    period_start = min(r.billing_start for r in rows)
    period_end = max(r.billing_end for r in rows)

    token = held_token if held_token is not None else acquire_scope_lock(session, scope_key, job_id)

    # Fencing token verificado ANTES de qualquer outra leitura/escrita de domínio — um worker
    # com lease obsoleto não deve nem conseguir abrir flags de sobreposição, muito menos
    # inserir dados (seção 7-ter: o gate vale para toda a operação, não só para o insert final).
    current_token = session.execute(
        select(ScopeLock.fencing_token).where(ScopeLock.scope_key == scope_key).with_for_update()
    ).scalar_one_or_none()
    if current_token != token:
        session.rollback()
        raise FencingTokenMismatch(
            f"scope_key={scope_key}: token usado={token}, token vigente={current_token}"
        )

    overlapping = [
        d
        for d in overlap.find_overlapping_datasets(session, batch.provider, scope_key, period_start, period_end)
        if d.import_batch_id != batch.id
    ]
    blocking: list[Dataset] = []
    acknowledged: list[tuple[Dataset, object]] = []

    for existing_dataset in overlapping:
        flag = overlap.ensure_pending_flag(session, batch.id, existing_dataset, scope_key, period_start, period_end)
        if flag.resolution == "pending":
            blocking.append(existing_dataset)
        elif flag.resolution == "rejected":
            batch.status = "rejected"
            session.commit()
            release_scope_lock(session, scope_key)
            return CommitOutcome(status="overlap_rejected_by_user")
        elif flag.resolution == "replace_approved":
            # Supersessão de dataset não implementada em F1 (sem versionamento no schema
            # mínimo) — tratado como bloqueante até F2/F3, nunca como exclusão silenciosa.
            blocking.append(existing_dataset)
        elif flag.resolution == "kept_both_as_correction":
            acknowledged.append((existing_dataset, flag))

    if blocking:
        session.commit()
        release_scope_lock(session, scope_key)
        return CommitOutcome(
            status="overlap_pending", blocking_overlap_dataset_ids=[d.id for d in blocking]
        )

    granularity, granularity_source = compute_granularity(rows)
    currency_set = sorted({r.currency for r in rows})

    dataset = Dataset(
        import_batch_id=batch.id,
        kind="cost_and_usage",
        scope_key=scope_key,
        period_start=period_start,
        period_end=period_end,
        provider=batch.provider,
        currency_set=currency_set,
        row_count=len(rows),
        quality_score=None,
        ingestion_version=adapter.schema_version,
        granularity=granularity,
        granularity_source=granularity_source,
    )
    session.add(dataset)
    session.flush()

    # Bulk insert (Core, não ORM por linha) — relevante para a meta de performance de 100k
    # linhas em <=60s (seção 13 do plano); mesma transação, mesma garantia de atomicidade.
    cost_usage_rows = [
        {
            "id": uuid.uuid4(),
            "dataset_id": dataset.id,
            "provider": row.provider,
            "billing_account": row.billing_account,
            "sub_account": row.sub_account,
            "resource_id": row.resource_id,
            "service": row.service,
            "region": row.region,
            "charge_category": row.charge_category,
            "billing_start": row.billing_start,
            "billing_end": row.billing_end,
            "usage_start": row.usage_start,
            "usage_end": row.usage_end,
            "pricing_qty": row.pricing_qty,
            "pricing_unit": row.pricing_unit,
            "currency": row.currency,
            "billed_cost": row.billed_cost,
            "effective_cost": row.effective_cost,
            "list_cost": row.list_cost,
            "contracted_cost": row.contracted_cost,
            "raw_ref": row.raw_ref,
            "natural_key_hash": natural_key_hash(row),
        }
        for row in rows
    ]
    if cost_usage_rows:
        session.execute(CostUsage.__table__.insert(), cost_usage_rows)

    for existing_dataset, flag in acknowledged:
        flag.dataset_id = dataset.id

    batch.status = "committed"
    session.commit()
    release_scope_lock(session, scope_key)
    return CommitOutcome(status="committed", dataset_id=dataset.id)
