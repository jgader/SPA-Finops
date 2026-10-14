"""Deduplicação por HASH DE ARQUIVO — mecanismo (a) da seção 4 do plano. Isolado de
overlap.py por desenho: este módulo só lê/escreve ImportBatch, nunca Dataset."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.canonical_financial.models import ImportBatch


def find_committed_duplicate(session: Session, sha256: str) -> ImportBatch | None:
    """Pergunta (a) da seção 4: 'este exato arquivo já foi importado?'. Pode haver mais de
    um import_batch 'committed' com o mesmo hash (reimportações idempotentes sucessivas
    também viram 'committed' via este mesmo caminho) — pega o mais antigo, que é sempre o
    que efetivamente tem um Dataset associado."""
    stmt = (
        select(ImportBatch)
        .where(ImportBatch.sha256 == sha256, ImportBatch.status == "committed")
        .order_by(ImportBatch.uploaded_at.asc())
        .limit(1)
    )
    return session.execute(stmt).scalar_one_or_none()
