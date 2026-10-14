"""Detecta jobs órfãos (heartbeat expirado) e decide: reenfileirar (transitória, dentro do
limite de tentativas) ou marcar failed definitivo (seção 7 do plano). Nunca reenfileira
falha permanente — essa nunca chega a ficar 'running' por heartbeat, vai direto a failed
em import_job.py."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.domains.canonical_financial.models import ImportJob


def sweep_orphaned_jobs(session: Session, now: datetime | None = None) -> list[ImportJob]:
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=settings.worker_orphan_timeout_seconds)

    stmt = select(ImportJob).where(ImportJob.state == "running", ImportJob.heartbeat_at < cutoff)
    orphans = list(session.execute(stmt).scalars().all())

    requeued = []
    for job in orphans:
        if job.attempt_count >= settings.worker_max_attempts:
            job.state = "failed"
            job.failure_class = "transient"
            job.error_detail = (
                f"esgotadas {settings.worker_max_attempts} tentativas (incluindo a primeira) após heartbeat expirado"
            )
            job.finished_at = now
        else:
            job.state = "orphaned_requeued"
            job.heartbeat_at = None
            requeued.append(job)

    session.commit()

    # orphaned_requeued -> queued, para que claim_next_queued_job os pegue de novo
    for job in requeued:
        job.state = "queued"
    session.commit()

    return orphans
