"""f1_initial_schema

Revision ID: e1e379fd92f9
Revises:
Create Date: 2026-10-14

Esquema F1: import_batch, dataset, cost_usage (DATA_CONTRACTS.md, sem alteração de forma) +
import_job, import_field_mapping, dataset_overlap_flag, scope_lock (com fencing_token),
import_row_rejection (propostas novas documentadas em docs/PLANO_EXECUCAO_F1.md).
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

from alembic import op

revision = "e1e379fd92f9"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "import_batch",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_name", sa.String(64), nullable=False),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("format", sa.String(16), nullable=False),
        sa.Column("schema_version", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="uploaded"),
        sa.Column("errors_summary", pg.JSONB(), nullable=True),
        sa.CheckConstraint(
            "status in ('uploaded','detected','validated','staged','committed','rejected')",
            name="ck_import_batch_status",
        ),
    )
    op.create_index("ix_import_batch_sha256", "import_batch", ["sha256"])

    op.create_table(
        "dataset",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("import_batch_id", pg.UUID(as_uuid=True), sa.ForeignKey("import_batch.id"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("scope_key", sa.String(256), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("currency_set", pg.JSONB(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quality_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("ingestion_version", sa.String(32), nullable=False),
        sa.Column("granularity", sa.String(16), nullable=False, server_default="unknown"),
        sa.Column("granularity_source", sa.String(32), nullable=False, server_default="usage_period"),
        sa.CheckConstraint(
            "granularity in ('daily','monthly','mixed','unknown')", name="ck_dataset_granularity"
        ),
        sa.CheckConstraint(
            "granularity_source in ('usage_period','billing_period_fallback','insufficient_evidence')",
            name="ck_dataset_granularity_source",
        ),
    )
    op.create_index("ix_dataset_import_batch_id", "dataset", ["import_batch_id"])
    op.create_index("ix_dataset_scope_key", "dataset", ["scope_key"])

    op.create_table(
        "cost_usage",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("dataset_id", pg.UUID(as_uuid=True), sa.ForeignKey("dataset.id"), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("billing_account", sa.String(128), nullable=False),
        sa.Column("sub_account", sa.String(128), nullable=True),
        sa.Column("resource_id", sa.String(512), nullable=True),
        sa.Column("service", sa.String(128), nullable=False),
        sa.Column("region", sa.String(64), nullable=True),
        sa.Column("charge_category", sa.String(32), nullable=False),
        sa.Column("billing_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("billing_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usage_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("usage_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pricing_qty", sa.Numeric(20, 6), nullable=True),
        sa.Column("pricing_unit", sa.String(32), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("billed_cost", sa.Numeric(20, 6), nullable=False),
        sa.Column("effective_cost", sa.Numeric(20, 6), nullable=True),
        sa.Column("list_cost", sa.Numeric(20, 6), nullable=True),
        sa.Column("contracted_cost", sa.Numeric(20, 6), nullable=True),
        sa.Column("raw_ref", sa.String(256), nullable=False),
        sa.Column("natural_key_hash", sa.String(64), nullable=False),
        sa.CheckConstraint(
            "charge_category in ('Usage','Purchase','Tax','Credit','Adjustment')",
            name="ck_cost_usage_charge_category",
        ),
    )
    op.create_index("ix_cost_usage_dataset_id", "cost_usage", ["dataset_id"])
    op.create_index("ix_cost_usage_natural_key_hash", "cost_usage", ["natural_key_hash"])

    op.create_table(
        "import_job",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("import_batch_id", pg.UUID(as_uuid=True), sa.ForeignKey("import_batch.id"), nullable=False),
        sa.Column("state", sa.String(24), nullable=False, server_default="queued"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_detail", sa.String(2048), nullable=True),
        sa.Column("failure_class", sa.String(16), nullable=True),
        sa.Column("checkpoint_row_offset", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("held_fencing_token", sa.Integer(), nullable=True),
        sa.Column("manual_retry_requested_by", sa.String(128), nullable=True),
        sa.Column("manual_retry_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "state in ('queued','running','succeeded','failed','orphaned_requeued')",
            name="ck_import_job_state",
        ),
        sa.CheckConstraint(
            "failure_class is null or failure_class in ('transient','permanent')",
            name="ck_import_job_failure_class",
        ),
    )
    op.create_index("ix_import_job_import_batch_id", "import_job", ["import_batch_id"])
    op.create_index("ix_import_job_state_heartbeat", "import_job", ["state", "heartbeat_at"])

    op.create_table(
        "import_field_mapping",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("import_batch_id", pg.UUID(as_uuid=True), sa.ForeignKey("import_batch.id"), nullable=False),
        sa.Column("source_field", sa.String(128), nullable=False),
        sa.Column("canonical_field", sa.String(128), nullable=False),
        sa.Column("transform_applied", sa.String(64), nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("is_manual_override", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_import_field_mapping_batch_id", "import_field_mapping", ["import_batch_id"])

    op.create_table(
        "dataset_overlap_flag",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("dataset_id", pg.UUID(as_uuid=True), sa.ForeignKey("dataset.id"), nullable=True),
        sa.Column("pending_import_batch_id", pg.UUID(as_uuid=True), sa.ForeignKey("import_batch.id"), nullable=True),
        sa.Column("overlapping_dataset_id", pg.UUID(as_uuid=True), sa.ForeignKey("dataset.id"), nullable=False),
        sa.Column("scope_key", sa.String(256), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolution", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("resolved_by", sa.String(128), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "resolution in ('pending','replace_approved','kept_both_as_correction','rejected')",
            name="ck_overlap_resolution",
        ),
        sa.CheckConstraint(
            "dataset_id is not null or pending_import_batch_id is not null",
            name="ck_overlap_has_dataset_or_pending_batch",
        ),
    )
    op.create_index("ix_overlap_dataset_id", "dataset_overlap_flag", ["dataset_id"])
    op.create_index("ix_overlap_pending_batch_id", "dataset_overlap_flag", ["pending_import_batch_id"])
    op.create_index("ix_overlap_scope_key", "dataset_overlap_flag", ["scope_key"])

    # Sequence dedicada do fencing token: monotônica por aquisição de lock, nunca por linha
    # (ver docs/PLANO_EXECUCAO_F1.md seção 7-ter).
    op.execute("CREATE SEQUENCE scope_lock_fencing_token_seq START WITH 1 INCREMENT BY 1")

    op.create_table(
        "scope_lock",
        sa.Column("scope_key", sa.String(256), primary_key=True),
        sa.Column("held_by_job_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("fencing_token", sa.Integer(), nullable=False),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "import_row_rejection",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("import_batch_id", pg.UUID(as_uuid=True), sa.ForeignKey("import_batch.id"), nullable=False),
        sa.Column("row_offset", sa.Integer(), nullable=False),
        sa.Column("raw_excerpt_ref", sa.String(256), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("reason_code", sa.String(64), nullable=False),
        sa.Column("field", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("severity in ('info','warning','error')", name="ck_rejection_severity"),
        sa.UniqueConstraint(
            "import_batch_id", "row_offset", "reason_code", name="uq_rejection_row_reason"
        ),
    )
    op.create_index("ix_rejection_batch_id", "import_row_rejection", ["import_batch_id"])
    op.create_index("ix_rejection_severity", "import_row_rejection", ["severity"])


def downgrade() -> None:
    op.drop_table("import_row_rejection")
    op.drop_table("scope_lock")
    op.execute("DROP SEQUENCE scope_lock_fencing_token_seq")
    op.drop_table("dataset_overlap_flag")
    op.drop_table("import_field_mapping")
    op.drop_table("import_job")
    op.drop_table("cost_usage")
    op.drop_table("dataset")
    op.drop_table("import_batch")
