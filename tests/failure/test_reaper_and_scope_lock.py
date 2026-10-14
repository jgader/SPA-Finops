"""Cenários de falha da seção 12 do plano: reaper requeue de job órfão (transitória) e
contenção de scope_lock entre dois import_batch diferentes para o mesmo scope+period."""

import datetime
import os
import shutil
import uuid

import pytest

from app.config.settings import settings
from app.domains.canonical_financial.models import ImportBatch, ImportJob
from app.domains.ingestion.commit import acquire_scope_lock
from app.domains.ingestion.errors import ScopeLockHeld
from app.domains.ingestion.identity import file_sha256

FIXTURES = os.path.join(os.path.dirname(__file__), "..", "..", "packages", "fixtures", "data")


def _make_batch(db_session, sha_suffix: str = "") -> ImportBatch:
    batch = ImportBatch(
        id=uuid.uuid4(),
        source_name="test",
        original_filename="x.csv",
        sha256=f"deadbeef{sha_suffix}",
        uploaded_at=datetime.datetime.now(datetime.timezone.utc),
        provider="azure",
        format="csv",
        schema_version="focus-1.0r2",
        status="staged",
    )
    db_session.add(batch)
    db_session.commit()
    return batch


def test_orphaned_job_within_attempt_budget_is_requeued(db_session):
    from reaper import sweep_orphaned_jobs

    batch = _make_batch(db_session)
    job = ImportJob(
        import_batch_id=batch.id,
        state="running",
        attempt_count=1,
        heartbeat_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=120),
    )
    db_session.add(job)
    db_session.commit()

    sweep_orphaned_jobs(db_session)
    db_session.refresh(job)
    assert job.state == "queued"  # elegível a retomada automática (transitória, dentro do limite)


def test_orphaned_job_exhausting_attempts_fails_permanently_no_more_retry(db_session):
    from reaper import sweep_orphaned_jobs

    batch = _make_batch(db_session, "2")
    job = ImportJob(
        import_batch_id=batch.id,
        state="running",
        attempt_count=settings.worker_max_attempts,  # já esgotou as 3 tentativas
        heartbeat_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=120),
    )
    db_session.add(job)
    db_session.commit()

    sweep_orphaned_jobs(db_session)
    db_session.refresh(job)
    assert job.state == "failed"


def test_two_different_batches_cannot_hold_scope_lock_concurrently(db_session):
    job_1 = ImportJob(import_batch_id=_make_batch(db_session, "a").id, state="running")
    job_2 = ImportJob(import_batch_id=_make_batch(db_session, "b").id, state="running")
    db_session.add_all([job_1, job_2])
    db_session.commit()

    scope_key = "azure:demo-sub-9999:cost_and_usage"
    acquire_scope_lock(db_session, scope_key, job_1.id, lease_seconds=60)

    with pytest.raises(ScopeLockHeld):
        acquire_scope_lock(db_session, scope_key, job_2.id, lease_seconds=60)


def test_manual_retry_resets_failed_job_and_records_who_requested(db_session):
    from jobs.import_job import manual_retry

    batch = _make_batch(db_session, "3")
    job = ImportJob(import_batch_id=batch.id, state="failed", attempt_count=3, failure_class="permanent")
    db_session.add(job)
    db_session.commit()

    manual_retry(db_session, job, requested_by="analista@demo.local")
    db_session.refresh(job)
    assert job.state == "queued"
    assert job.attempt_count == 0
    assert job.manual_retry_requested_by == "analista@demo.local"


def test_manual_retry_rejected_when_job_not_failed(db_session):
    from jobs.import_job import manual_retry

    batch = _make_batch(db_session, "4")
    job = ImportJob(import_batch_id=batch.id, state="running")
    db_session.add(job)
    db_session.commit()

    with pytest.raises(ValueError):
        manual_retry(db_session, job, requested_by="analista@demo.local")
