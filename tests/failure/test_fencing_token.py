"""Cenário de concorrência exigido pelo GO condicional (ajuste 1): worker A adquire o lease,
o lease é forçado a expirar (sem matar A), worker B assume com um fencing_token novo e
comita com sucesso, e worker A — que não sabe que foi substituído — tenta comitar depois
usando o token antigo. Deve falhar sem afetar o dataset que B já comitou."""

import os
import shutil
import uuid

import pytest

from app.domains.canonical_financial.models import ImportBatch, ImportJob
from app.domains.ingestion.commit import (
    FencingTokenMismatch,
    acquire_scope_lock,
    commit_import_batch,
    force_expire_lock_for_test,
)
from app.domains.ingestion.identity import file_sha256
from app.domains.ingestion.staging import stage_import_batch

FIXTURES = os.path.join(os.path.dirname(__file__), "..", "..", "packages", "fixtures", "data")


def _stage_batch(db_session, tmp_path, filename: str, provider="azure", fmt="csv") -> tuple[ImportBatch, str]:
    import datetime

    batch_dir = tmp_path / "incoming" / "batch"
    os.makedirs(batch_dir, exist_ok=True)
    src = os.path.join(FIXTURES, filename)
    sha256 = file_sha256(src)
    dest = str(batch_dir / f"{sha256}.csv")
    shutil.copyfile(src, dest)

    batch = ImportBatch(
        id=uuid.uuid4(),
        source_name="test",
        original_filename=filename,
        sha256=sha256,
        uploaded_at=datetime.datetime.now(datetime.timezone.utc),
        provider=provider,
        format=fmt,
        schema_version="undetected",
        status="uploaded",
    )
    db_session.add(batch)
    db_session.flush()
    stage_import_batch(db_session, batch, dest)
    db_session.commit()
    return batch, dest


def test_stale_worker_commit_rejected_after_lease_reassigned(db_session, tmp_path):
    batch, file_path = _stage_batch(db_session, tmp_path, "focus_clean_baseline.csv")
    assert batch.status == "staged"

    job_a = ImportJob(import_batch_id=batch.id, state="running")
    job_b = ImportJob(import_batch_id=batch.id, state="running")
    db_session.add_all([job_a, job_b])
    db_session.commit()

    scope_key = "azure:demo-sub-0001:cost_and_usage"

    # Worker A adquire o lease primeiro.
    token_a = acquire_scope_lock(db_session, scope_key, job_a.id, lease_seconds=30)

    # Simula a passagem do tempo sem matar A: o lease expira.
    force_expire_lock_for_test(db_session, scope_key)

    # Worker B assume o escopo — fencing_token avança.
    token_b = acquire_scope_lock(db_session, scope_key, job_b.id, lease_seconds=30)
    assert token_b != token_a

    # B comita com sucesso usando seu próprio token.
    outcome_b = commit_import_batch(db_session, batch, job_b.id, file_path, held_token=token_b)
    assert outcome_b.status == "committed"
    assert outcome_b.dataset_id is not None

    # A "desperta" agora e tenta comitar com o token obsoleto — deve ser rejeitado,
    # e o dataset de B precisa permanecer intacto (nada sobrescrito, nada duplicado).
    db_session.refresh(batch)
    batch.status = "staged"  # força o estado de volta só para exercitar o caminho de A isoladamente
    db_session.commit()

    with pytest.raises(FencingTokenMismatch):
        commit_import_batch(db_session, batch, job_a.id, file_path, held_token=token_a)

    from sqlalchemy import select
    from app.domains.canonical_financial.models import Dataset

    datasets = db_session.execute(select(Dataset)).scalars().all()
    assert len(datasets) == 1
    assert datasets[0].id == outcome_b.dataset_id
