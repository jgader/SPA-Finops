"""Loop do worker: reivindica jobs queued e os processa; roda o reaper periodicamente.
Processo separado (docker-compose), fila persistida em tabela (sem broker externo),
conforme arquitetura aprovada em docs/PLANO_EXECUCAO_F1.md."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services" / "api"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.config.settings import settings
from app.db.session import SessionLocal
from jobs.import_job import claim_next_queued_job, run_job
from reaper import sweep_orphaned_jobs


def main() -> None:
    last_reap = 0.0
    while True:
        session = SessionLocal()
        try:
            now = time.time()
            if now - last_reap >= settings.worker_reaper_poll_seconds:
                sweep_orphaned_jobs(session)
                last_reap = now

            job = claim_next_queued_job(session)
            if job is not None:
                try:
                    run_job(session, job)
                except Exception as exc:  # noqa: BLE001 — classificação já ocorreu em run_job
                    print(f"job {job.id} terminou com falha classificada: {exc}")
        finally:
            session.close()
        time.sleep(settings.worker_poll_seconds)


if __name__ == "__main__":
    main()
