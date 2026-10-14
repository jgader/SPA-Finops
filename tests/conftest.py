import os
import uuid

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://postgres:finops_local_dev@127.0.0.1:5432/finops_ai_test"
)
os.environ.setdefault(
    "TEST_DATABASE_URL", "postgresql+psycopg://postgres:finops_local_dev@127.0.0.1:5432/finops_ai_test"
)

import pytest  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.config.settings import settings  # noqa: E402
from app.db.session import make_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

_TABLES = [
    "import_row_rejection",
    "scope_lock",
    "dataset_overlap_flag",
    "import_field_mapping",
    "import_job",
    "cost_usage",
    "dataset",
    "import_batch",
]


@pytest.fixture(scope="session")
def engine():
    return make_engine(settings.test_database_url)


@pytest.fixture
def db_session(engine, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_staging_dir", str(tmp_path / "incoming"))
    os.makedirs(settings.upload_staging_dir, exist_ok=True)

    Session = sessionmaker(bind=engine, future=True)
    session = Session()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        cleanup = Session()
        cleanup.execute(text(f"TRUNCATE {', '.join(_TABLES)} CASCADE"))
        cleanup.commit()
        cleanup.close()


@pytest.fixture
def new_batch_dir(tmp_path):
    def _make(batch_id: uuid.UUID) -> str:
        path = tmp_path / "incoming" / str(batch_id)
        os.makedirs(path, exist_ok=True)
        return str(path)

    return _make


@pytest.fixture
def client(db_session):
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


@pytest.fixture
def drain_jobs(db_session):
    def _drain(max_jobs: int = 10):
        from app.domains.ingestion.errors import PermanentFailure, TransientFailure
        from jobs.import_job import claim_next_queued_job, run_job

        processed = 0
        while processed < max_jobs:
            job = claim_next_queued_job(db_session)
            if job is None:
                break
            try:
                run_job(db_session, job)
            except (PermanentFailure, TransientFailure):
                pass
            processed += 1
        return processed

    return _drain
