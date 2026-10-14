from pydantic import BaseModel


class DatasetSummary(BaseModel):
    id: str
    provider: str
    scope_key: str
    period_start: str
    period_end: str
    currency_set: list[str]
    row_count: int
    granularity: str
    granularity_source: str
    ingestion_version: str


class DatasetQualityResponse(BaseModel):
    dataset_id: str
    import_batch_id: str
    row_count: int
    rejections_by_severity: dict[str, int]


class DuplicateCandidate(BaseModel):
    cost_usage_id: str
    natural_key_hash: str
    service: str
    resource_id: str | None
    billing_start: str
    billing_end: str
    billed_cost: str
    currency: str
