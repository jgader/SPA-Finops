import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class ImportBatch(Base):
    """Um upload. Identidade de arquivo: dedup acontece por sha256 (ver domains/ingestion/dedup.py)."""

    __tablename__ = "import_batch"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    source_name: Mapped[str] = mapped_column(String(64))
    original_filename: Mapped[str] = mapped_column(String(512))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    provider: Mapped[str] = mapped_column(String(32))
    format: Mapped[str] = mapped_column(String(16))
    schema_version: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="uploaded")
    errors_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status in ('uploaded','detected','validated','staged','committed','rejected')",
            name="ck_import_batch_status",
        ),
    )


class Dataset(Base):
    """Identidade de dataset: provider+scope+period+cost_basis. Distinta de identidade de arquivo
    (ImportBatch.sha256) e de lançamento financeiro individual (CostUsage.natural_key_hash)."""

    __tablename__ = "dataset"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    import_batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("import_batch.id"), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    scope_key: Mapped[str] = mapped_column(String(256), index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    provider: Mapped[str] = mapped_column(String(32))
    currency_set: Mapped[list[str]] = mapped_column(JSONB)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    quality_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    ingestion_version: Mapped[str] = mapped_column(String(32))
    granularity: Mapped[str] = mapped_column(String(16), default="unknown")
    granularity_source: Mapped[str] = mapped_column(String(32), default="usage_period")

    __table_args__ = (
        CheckConstraint(
            "granularity in ('daily','monthly','mixed','unknown')",
            name="ck_dataset_granularity",
        ),
        CheckConstraint(
            "granularity_source in ('usage_period','billing_period_fallback','insufficient_evidence')",
            name="ck_dataset_granularity_source",
        ),
    )


class CostUsage(Base):
    __tablename__ = "cost_usage"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("dataset.id"), index=True)
    provider: Mapped[str] = mapped_column(String(32))
    billing_account: Mapped[str] = mapped_column(String(128))
    sub_account: Mapped[str | None] = mapped_column(String(128), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    service: Mapped[str] = mapped_column(String(128))
    region: Mapped[str | None] = mapped_column(String(64), nullable=True)
    charge_category: Mapped[str] = mapped_column(String(32))
    billing_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    billing_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    usage_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    usage_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pricing_qty: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    pricing_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    currency: Mapped[str] = mapped_column(String(3))
    billed_cost: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    effective_cost: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    list_cost: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    contracted_cost: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    raw_ref: Mapped[str] = mapped_column(String(256))
    natural_key_hash: Mapped[str] = mapped_column(String(64), index=True)

    __table_args__ = (
        # Valores do FOCUS (categoria do lançamento, não confundir com cost basis:
        # billed/effective/list/contracted são as 4 colunas de custo lado a lado, seção 6 do plano).
        CheckConstraint(
            "charge_category in ('Usage','Purchase','Tax','Credit','Adjustment')",
            name="ck_cost_usage_charge_category",
        ),
    )


class ImportJob(Base):
    __tablename__ = "import_job"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    import_batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("import_batch.id"), index=True)
    state: Mapped[str] = mapped_column(String(24), default="queued")
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    failure_class: Mapped[str | None] = mapped_column(String(16), nullable=True)
    checkpoint_row_offset: Mapped[int] = mapped_column(Integer, default=0)
    held_fencing_token: Mapped[int | None] = mapped_column(Integer, nullable=True)
    manual_retry_requested_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    manual_retry_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "state in ('queued','running','succeeded','failed','orphaned_requeued')",
            name="ck_import_job_state",
        ),
        CheckConstraint(
            "failure_class is null or failure_class in ('transient','permanent')",
            name="ck_import_job_failure_class",
        ),
    )


class ImportFieldMapping(Base):
    """Cada decisão de mapeamento é imutável; correção manual gera novo registro (nunca UPDATE)."""

    __tablename__ = "import_field_mapping"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    import_batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("import_batch.id"), index=True)
    source_field: Mapped[str] = mapped_column(String(128))
    canonical_field: Mapped[str] = mapped_column(String(128))
    transform_applied: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3))
    is_manual_override: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DatasetOverlapFlag(Base):
    """Identidade de dataset sobreposta. Nunca resolvida automaticamente, nunca exclui nada.
    dataset_id é nullable porque a sobreposição é detectada ANTES do commit — quando ainda
    não existe um Dataset para o novo arquivo, usamos pending_import_batch_id; dataset_id é
    preenchido depois, só se/quando o commit de fato ocorrer (resolution='kept_both_as_correction')."""

    __tablename__ = "dataset_overlap_flag"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("dataset.id"), nullable=True, index=True)
    pending_import_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("import_batch.id"), nullable=True, index=True
    )
    overlapping_dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("dataset.id"), index=True)
    scope_key: Mapped[str] = mapped_column(String(256))
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolution: Mapped[str] = mapped_column(String(24), default="pending")
    resolved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "resolution in ('pending','replace_approved','kept_both_as_correction','rejected')",
            name="ck_overlap_resolution",
        ),
        CheckConstraint(
            "dataset_id is not null or pending_import_batch_id is not null",
            name="ck_overlap_has_dataset_or_pending_batch",
        ),
    )


class ScopeLock(Base):
    """Lease exclusivo por provider+scope+period. fencing_token vem de uma sequence monotônica,
    incrementado a cada aquisição (não a cada linha) — ver app/domains/ingestion/commit.py."""

    __tablename__ = "scope_lock"

    scope_key: Mapped[str] = mapped_column(String(256), primary_key=True)
    held_by_job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    fencing_token: Mapped[int] = mapped_column(Integer)
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ImportRowRejection(Base):
    """Nunca contém o valor financeiro bruto da linha — só a referência ao arquivo original
    (raw_excerpt_ref), para que os logs/relatórios nunca exponham dados financeiros sensíveis."""

    __tablename__ = "import_row_rejection"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    import_batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("import_batch.id"), index=True)
    row_offset: Mapped[int] = mapped_column(Integer)
    raw_excerpt_ref: Mapped[str] = mapped_column(String(256))
    severity: Mapped[str] = mapped_column(String(16))
    reason_code: Mapped[str] = mapped_column(String(64))
    field: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("severity in ('info','warning','error')", name="ck_rejection_severity"),
        UniqueConstraint("import_batch_id", "row_offset", "reason_code", name="uq_rejection_row_reason"),
    )
