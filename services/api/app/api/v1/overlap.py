import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.domains.canonical_financial.models import DatasetOverlapFlag
from app.domains.ingestion.overlap import resolve_overlap
from app.schemas.imports import OverlapResolveRequest

router = APIRouter(prefix="/api/v1/overlap", tags=["overlap"])

_VALID_RESOLUTIONS = {"replace_approved", "kept_both_as_correction", "rejected"}


@router.post("/{flag_id}/resolve")
def resolve_overlap_flag(
    flag_id: uuid.UUID, body: OverlapResolveRequest, session: Session = Depends(get_session)
) -> dict:
    """Decisão humana explícita — nunca automática (seção 4 do plano). 'replace_approved'
    é aceito aqui mas o commit permanece bloqueado (sem supersessão de dataset em F1)."""
    if body.resolution not in _VALID_RESOLUTIONS:
        raise HTTPException(status_code=400, detail=f"resolution inválida: {body.resolution}")

    flag = session.get(DatasetOverlapFlag, flag_id)
    if flag is None:
        raise HTTPException(status_code=404, detail="dataset_overlap_flag não encontrado")

    resolve_overlap(session, flag, body.resolution, body.resolved_by)
    session.commit()

    note = None
    if body.resolution == "replace_approved":
        note = "registrado, mas F1 não implementa supersessão de dataset — commit continua bloqueado"

    return {"flag_id": str(flag.id), "resolution": flag.resolution, "note": note}
