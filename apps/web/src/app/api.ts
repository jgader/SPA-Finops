export interface ImportStatus {
  id: string;
  status: string;
  provider: string;
  schema_version: string;
  job_state: string | null;
  job_attempt_count: number | null;
  job_failure_class: string | null;
  job_error_detail: string | null;
  rejections_by_severity: Record<string, number>;
  rejections: { row_offset: number; severity: string; reason_code: string; field: string | null }[];
}

export interface DatasetSummary {
  id: string;
  provider: string;
  scope_key: string;
  period_start: string;
  period_end: string;
  currency_set: string[];
  row_count: number;
  granularity: string;
  granularity_source: string;
  ingestion_version: string;
}

async function asJson<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    const detail = await resp.text();
    throw new Error(`${resp.status}: ${detail}`);
  }
  return resp.json();
}

export const api = {
  async upload(file: File): Promise<{ id: string; status: string }> {
    const form = new FormData();
    form.append("file", file);
    const resp = await fetch("/api/v1/imports", { method: "POST", body: form });
    return asJson(resp);
  },
  async getImport(id: string): Promise<ImportStatus> {
    const resp = await fetch(`/api/v1/imports/${id}`);
    return asJson(resp);
  },
  async commit(id: string): Promise<{ status: string; dataset_id: string | null }> {
    const resp = await fetch(`/api/v1/imports/${id}/commit`, { method: "POST" });
    return asJson(resp);
  },
  async listDatasets(): Promise<DatasetSummary[]> {
    const resp = await fetch("/api/v1/datasets");
    return asJson(resp);
  },
};
