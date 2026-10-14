from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_serializer


class ImportCreateResponse(BaseModel):
    id: str
    status: str


class RejectionItem(BaseModel):
    row_offset: int
    severity: str
    reason_code: str
    field: str | None


class ImportStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    provider: str
    schema_version: str
    job_state: str | None
    job_attempt_count: int | None
    job_failure_class: str | None
    job_error_detail: str | None
    rejections_by_severity: dict[str, int]
    rejections: list[RejectionItem]


class CommitResponse(BaseModel):
    status: str
    dataset_id: str | None = None
    existing_batch_id: str | None = None
    blocking_overlap_dataset_ids: list[str] = []


class RetryRequest(BaseModel):
    requested_by: str


class OverlapResolveRequest(BaseModel):
    resolution: str
    resolved_by: str
