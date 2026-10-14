import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.db.session import get_session
from app.domains.canonical_financial.models import ImportBatch, ImportJob, ImportRowRejection
from app.domains.ingestion.identity import file_sha256
from app.schemas.imports import (
    CommitResponse,
    ImportCreateResponse,
    ImportStatusResponse,
    RejectionItem,
    RetryRequest,
)
from app.security.path_safety import safe_join, sanitize_display_filename
from app.security.upload_guard import (
    DecompressionLimitExceeded,
    UploadRejected,
    decompress_gzip_with_limit,
    save_upload_stream,
    validate_extension,
    validate_magic_bytes,
)

router = APIRouter(prefix="/api/v1/imports", tags=["imports"])


@router.post("", response_model=ImportCreateResponse, status_code=201)
def create_import(file: UploadFile, session: Session = Depends(get_session)) -> ImportCreateResponse:
    try:
        extension = validate_extension(file.filename or "")
    except UploadRejected as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    batch_id = uuid.uuid4()
    batch_dir = os.path.join(settings.upload_staging_dir, str(batch_id))
    os.makedirs(batch_dir, exist_ok=True)

    tmp_path = safe_join(batch_dir, "upload.tmp")
    try:
        save_upload_stream(file.file, tmp_path, settings.upload_max_bytes)
        validate_magic_bytes(tmp_path, extension)
    except UploadRejected as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    final_ext = extension
    final_path = tmp_path
    if extension == ".csv.gz":
        decompressed_path = safe_join(batch_dir, "decompressed.csv")
        try:
            decompress_gzip_with_limit(tmp_path, decompressed_path)
        except DecompressionLimitExceeded as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        os.remove(tmp_path)
        final_path = decompressed_path
        final_ext = ".csv"

    sha256 = file_sha256(final_path)
    stored_path = safe_join(batch_dir, f"{sha256}{final_ext}")
    os.replace(final_path, stored_path)

    batch = ImportBatch(
        id=batch_id,
        source_name="upload",
        original_filename=sanitize_display_filename(file.filename or "arquivo"),
        sha256=sha256,
        uploaded_at=datetime.now(timezone.utc),
        provider="unknown",
        format="csv" if final_ext != ".parquet" else "parquet",
        schema_version="undetected",
        status="uploaded",
    )
    session.add(batch)
    session.flush()

    job = ImportJob(import_batch_id=batch.id, state="queued")
    session.add(job)
    session.commit()

    return ImportCreateResponse(id=str(batch.id), status=batch.status)


@router.get("/{import_id}", response_model=ImportStatusResponse)
def get_import_status(import_id: uuid.UUID, session: Session = Depends(get_session)) -> ImportStatusResponse:
    batch = session.get(ImportBatch, import_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="import_batch não encontrado")

    job = session.execute(
        select(ImportJob).where(ImportJob.import_batch_id == import_id).order_by(ImportJob.id.desc()).limit(1)
    ).scalar_one_or_none()

    severity_counts = dict(
        session.execute(
            select(ImportRowRejection.severity, func.count())
            .where(ImportRowRejection.import_batch_id == import_id)
            .group_by(ImportRowRejection.severity)
        ).all()
    )

    rejections = session.execute(
        select(ImportRowRejection).where(ImportRowRejection.import_batch_id == import_id).limit(500)
    ).scalars().all()

    return ImportStatusResponse(
        id=str(batch.id),
        status=batch.status,
        provider=batch.provider,
        schema_version=batch.schema_version,
        job_state=job.state if job else None,
        job_attempt_count=job.attempt_count if job else None,
        job_failure_class=job.failure_class if job else None,
        job_error_detail=job.error_detail if job else None,
        rejections_by_severity=severity_counts,
        rejections=[
            RejectionItem(row_offset=r.row_offset, severity=r.severity, reason_code=r.reason_code, field=r.field)
            for r in rejections
        ],
    )


@router.post("/{import_id}/commit", response_model=CommitResponse)
def commit_import(import_id: uuid.UUID, session: Session = Depends(get_session)) -> CommitResponse:
    from app.services_worker_bridge import commit_batch_via_job, file_path_for_batch

    batch = session.get(ImportBatch, import_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="import_batch não encontrado")

    outcome = commit_batch_via_job(session, batch, file_path_for_batch(batch))
    return CommitResponse(
        status=outcome.status,
        dataset_id=str(outcome.dataset_id) if outcome.dataset_id else None,
        existing_batch_id=str(outcome.existing_batch_id) if outcome.existing_batch_id else None,
        blocking_overlap_dataset_ids=[str(d) for d in outcome.blocking_overlap_dataset_ids],
    )


@router.post("/{import_id}/retry")
def retry_import(import_id: uuid.UUID, body: RetryRequest, session: Session = Depends(get_session)) -> dict:
    from app.services_worker_bridge import manual_retry_batch

    batch = session.get(ImportBatch, import_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="import_batch não encontrado")

    try:
        job = manual_retry_batch(session, import_id, body.requested_by)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return {"job_id": str(job.id), "state": job.state}
