"""Processamento de um import_job: staging + tentativa de commit. Chamado tanto pelo loop
do worker quanto diretamente pelos testes (determinístico, sem I/O de rede)."""

import logging
import os
import uuid
from datetime import datetime, timezone

logger = logging.getLogger("finops_ai.worker.import_job")

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.domains.canonical_financial.models import ImportBatch, ImportJob
from app.domains.ingestion.commit import CommitOutcome, commit_import_batch
from app.domains.ingestion.errors import PermanentFailure, TransientFailure
from app.domains.ingestion.staging import StagingOutcome, stage_import_batch


def file_path_for(batch: ImportBatch) -> str:
    return os.path.join(settings.upload_staging_dir, str(batch.id), f"{batch.sha256}{_ext_for(batch)}")


def _ext_for(batch: ImportBatch) -> str:
    return {"csv": ".csv", "parquet": ".parquet"}.get(batch.format, ".csv")


def claim_next_queued_job(session: Session) -> ImportJob | None:
    """SELECT ... FOR UPDATE SKIP LOCKED — evita duas instâncias de worker pegarem o mesmo job."""
    from sqlalchemy import select

    stmt = (
        select(ImportJob)
        .where(ImportJob.state == "queued")
        .order_by(ImportJob.id)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    job = session.execute(stmt).scalar_one_or_none()
    if job is None:
        return None
    job.state = "running"
    job.attempt_count += 1
    job.started_at = datetime.now(timezone.utc)
    job.heartbeat_at = datetime.now(timezone.utc)
    session.commit()
    return job


def heartbeat(session: Session, job: ImportJob) -> None:
    job.heartbeat_at = datetime.now(timezone.utc)
    session.commit()


def manual_retry(session: Session, job: ImportJob, requested_by: str) -> ImportJob:
    """Reprocessamento manual controlado — distinto e auditável, separado do requeue
    automático do reaper (seção 7). Só aplicável a jobs em failed; reinicia o ciclo de
    tentativas (nova rodada deliberada, não uma continuação)."""
    if job.state != "failed":
        raise ValueError(f"job {job.id} não está em failed (state={job.state})")
    job.state = "queued"
    job.attempt_count = 0
    job.heartbeat_at = None
    job.error_detail = None
    job.failure_class = None
    job.finished_at = None
    job.manual_retry_requested_by = requested_by
    job.manual_retry_requested_at = datetime.now(timezone.utc)
    session.commit()
    return job


def run_job(session: Session, job: ImportJob) -> StagingOutcome | CommitOutcome:
    """Executa staging e, se staged com sucesso, tenta o commit imediatamente. Overlap
    pendente não é falha — é um resultado válido que aguarda decisão humana."""
    from sqlalchemy import select

    batch = session.execute(select(ImportBatch).where(ImportBatch.id == job.import_batch_id)).scalar_one()
    file_path = file_path_for(batch)

    # Logs só com IDs/contagens/códigos — nunca valor financeiro (seção 8 do plano).
    logger.info("job %s: iniciando processamento do import_batch %s", job.id, job.import_batch_id)

    try:
        staging_outcome = stage_import_batch(session, batch, file_path)
        session.commit()
        heartbeat(session, job)
        logger.info(
            "job %s: staging concluído, status=%s, issues=%d",
            job.id, staging_outcome.status, len(staging_outcome.validation.issues),
        )

        if staging_outcome.status == "rejected":
            job.state = "failed"
            job.failure_class = "permanent"
            job.error_detail = "validação encontrou linha(s) de severidade error; commit bloqueado (sem commit parcial em F1)"
            job.finished_at = datetime.now(timezone.utc)
            session.commit()
            logger.info("job %s: failed (permanent) — %s", job.id, job.error_detail)
            return staging_outcome

        commit_outcome = commit_import_batch(session, batch, job.id, file_path)
        job.state = "succeeded"
        job.finished_at = datetime.now(timezone.utc)
        session.commit()
        logger.info("job %s: succeeded, commit_status=%s", job.id, commit_outcome.status)
        return commit_outcome

    except PermanentFailure as exc:
        session.rollback()
        job.state = "failed"
        job.failure_class = "permanent"
        job.error_detail = str(exc)[:2048]
        job.finished_at = datetime.now(timezone.utc)
        session.commit()
        raise

    except TransientFailure as exc:
        session.rollback()
        job.error_detail = str(exc)[:2048]
        job.failure_class = "transient"
        session.commit()
        raise
