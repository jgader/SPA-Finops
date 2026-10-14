"""Ponte fina entre a API e o domínio de execução do worker (services/worker), só para as
duas operações que precisam de identidade de job: commit explícito via endpoint e retry
manual. Em produção, API e worker são processos/imagens separados (docker-compose); em
desenvolvimento monorepo, este módulo resolve o import adicionando services/worker ao
sys.path uma única vez."""

import sys
import uuid
from pathlib import Path

_WORKER_ROOT = Path(__file__).resolve().parents[2] / "worker"
if str(_WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(_WORKER_ROOT))

from jobs.import_job import file_path_for, manual_retry  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.domains.canonical_financial.models import ImportBatch, ImportJob  # noqa: E402
from app.domains.ingestion.commit import CommitOutcome, commit_import_batch  # noqa: E402


def file_path_for_batch(batch: ImportBatch) -> str:
    return file_path_for(batch)


def commit_batch_via_job(session: Session, batch: ImportBatch, file_path: str) -> CommitOutcome:
    job = session.execute(
        select(ImportJob).where(ImportJob.import_batch_id == batch.id).order_by(ImportJob.id.desc()).limit(1)
    ).scalar_one_or_none()
    job_id = job.id if job is not None else uuid.uuid4()
    return commit_import_batch(session, batch, job_id, file_path)


def manual_retry_batch(session: Session, import_batch_id: uuid.UUID, requested_by: str) -> ImportJob:
    job = session.execute(
        select(ImportJob)
        .where(ImportJob.import_batch_id == import_batch_id)
        .order_by(ImportJob.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    if job is None:
        raise ValueError("nenhum job encontrado para este import_batch")
    return manual_retry(session, job, requested_by)
