import os

FIXTURES = os.path.join(os.path.dirname(__file__), "..", "..", "packages", "fixtures", "data")


def _upload(client, filename: str, as_name: str | None = None):
    path = os.path.join(FIXTURES, filename)
    with open(path, "rb") as handle:
        return client.post(
            "/api/v1/imports", files={"file": (as_name or filename, handle, "text/csv")}
        )


def test_happy_path_commits_successfully(client, drain_jobs):
    resp = _upload(client, "focus_clean_baseline.csv")
    assert resp.status_code == 201
    import_id = resp.json()["id"]

    drain_jobs()

    status = client.get(f"/api/v1/imports/{import_id}").json()
    assert status["status"] == "committed", status
    assert status["rejections_by_severity"] == {}

    datasets = client.get("/api/v1/datasets").json()
    assert len(datasets) == 1
    assert datasets[0]["row_count"] == 8 * 61  # 8 serviços x (31+30) dias
    assert datasets[0]["granularity"] == "daily"
    assert datasets[0]["granularity_source"] == "usage_period"


def test_malformed_file_rejected_and_preserves_approved_base(client, drain_jobs):
    # Primeiro commita a base aprovada (AT-002: rejeição não pode alterar base já committed)
    _upload(client, "focus_clean_baseline.csv")
    drain_jobs()
    datasets_before = client.get("/api/v1/datasets").json()

    resp = _upload(client, "focus_malformed.csv")
    import_id = resp.json()["id"]
    drain_jobs()

    status = client.get(f"/api/v1/imports/{import_id}").json()
    assert status["status"] == "rejected"
    assert status["rejections_by_severity"].get("error", 0) >= 3  # missing field, bad decimal, bad category/currency
    # AT-002: sem commit parcial automático — nenhum dataset novo é criado
    datasets_after = client.get("/api/v1/datasets").json()
    assert len(datasets_after) == len(datasets_before)


def test_exact_duplicate_reimport_is_idempotent_noop(client, drain_jobs):
    _upload(client, "focus_clean_baseline.csv")
    drain_jobs()
    datasets_first = client.get("/api/v1/datasets").json()
    assert len(datasets_first) == 1

    resp = _upload(client, "focus_overlap_reimport.csv")  # bytes idênticos ao baseline
    import_id = resp.json()["id"]
    drain_jobs()

    status = client.get(f"/api/v1/imports/{import_id}").json()
    assert status["status"] == "committed"

    datasets_second = client.get("/api/v1/datasets").json()
    assert len(datasets_second) == 1  # nenhum dataset novo — AT-001


def test_different_hash_same_scope_period_flags_overlap_never_deletes(client, drain_jobs):
    _upload(client, "focus_clean_baseline.csv")
    drain_jobs()
    datasets_before = client.get("/api/v1/datasets").json()
    assert len(datasets_before) == 1

    resp = _upload(client, "focus_same_period_different_hash.csv")
    import_id = resp.json()["id"]
    drain_jobs()

    status = client.get(f"/api/v1/imports/{import_id}").json()
    # staged, não committed: sobreposição bloqueia até decisão humana — nunca falha a validação
    assert status["status"] == "staged", status

    datasets_after = client.get("/api/v1/datasets").json()
    assert len(datasets_after) == 1  # nada foi excluído nem substituído automaticamente


def test_multicurrency_captured_without_coercion(client, drain_jobs):
    resp = _upload(client, "focus_multicurrency.csv")
    import_id = resp.json()["id"]
    drain_jobs()

    status = client.get(f"/api/v1/imports/{import_id}").json()
    assert status["status"] == "committed"

    datasets = client.get("/api/v1/datasets").json()
    dataset = next(d for d in datasets if d["id"])
    assert set(dataset["currency_set"]) == {"BRL", "USD"}


def test_mixed_granularity_detected_from_usage_period(client, drain_jobs):
    resp = _upload(client, "focus_mixed_granularity.csv")
    import_id = resp.json()["id"]
    drain_jobs()

    status = client.get(f"/api/v1/imports/{import_id}").json()
    assert status["status"] == "committed"

    datasets = client.get("/api/v1/datasets").json()
    dataset = datasets[-1]
    assert dataset["granularity"] == "mixed"
    assert dataset["granularity_source"] == "usage_period"


def test_azure_cost_analysis_adapter_imports_correctly(client, drain_jobs):
    resp = _upload(client, "azure_cost_analysis_equivalent.csv")
    import_id = resp.json()["id"]
    drain_jobs()

    status = client.get(f"/api/v1/imports/{import_id}").json()
    assert status["status"] == "committed"
    assert status["schema_version"] == "azure-cost-analysis-native-1"

    datasets = client.get("/api/v1/datasets").json()
    dataset = next(d for d in datasets if d["ingestion_version"] == "azure-cost-analysis-native-1")
    assert dataset["granularity_source"] == "billing_period_fallback"  # sem usage period nesta fonte


def test_field_mapping_persisted_and_queryable(client, drain_jobs, db_session):
    from sqlalchemy import select
    from app.domains.canonical_financial.models import ImportFieldMapping

    resp = _upload(client, "focus_clean_baseline.csv")
    import_id = resp.json()["id"]
    drain_jobs()

    rows = db_session.execute(
        select(ImportFieldMapping).where(ImportFieldMapping.import_batch_id == import_id)
    ).scalars().all()
    assert len(rows) > 0
    assert any(r.canonical_field == "billed_cost" for r in rows)
