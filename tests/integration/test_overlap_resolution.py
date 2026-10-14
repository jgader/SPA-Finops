import os

FIXTURES = os.path.join(os.path.dirname(__file__), "..", "..", "packages", "fixtures", "data")


def _upload(client, filename: str):
    path = os.path.join(FIXTURES, filename)
    with open(path, "rb") as handle:
        return client.post("/api/v1/imports", files={"file": (filename, handle, "text/csv")})


def _commit_baseline_then_conflicting(client, drain_jobs):
    _upload(client, "focus_clean_baseline.csv")
    drain_jobs()
    resp = _upload(client, "focus_same_period_different_hash.csv")
    import_id = resp.json()["id"]
    drain_jobs()
    return import_id


def test_overlap_rejected_resolution_keeps_batch_rejected_and_commit_blocked(client, drain_jobs, db_session):
    from sqlalchemy import select

    from app.domains.canonical_financial.models import DatasetOverlapFlag

    import_id = _commit_baseline_then_conflicting(client, drain_jobs)
    status = client.get(f"/api/v1/imports/{import_id}").json()
    assert status["status"] == "staged"

    flag = db_session.execute(
        select(DatasetOverlapFlag).where(DatasetOverlapFlag.pending_import_batch_id == import_id)
    ).scalars().first()
    assert flag is not None
    assert flag.resolution == "pending"

    resolve_resp = client.post(f"/api/v1/overlap/{flag.id}/resolve", json={"resolution": "rejected", "resolved_by": "analista@demo.local"})
    assert resolve_resp.status_code == 200

    commit_resp = client.post(f"/api/v1/imports/{import_id}/commit")
    assert commit_resp.json()["status"] == "overlap_rejected_by_user"

    final_status = client.get(f"/api/v1/imports/{import_id}").json()
    assert final_status["status"] == "rejected"


def test_overlap_kept_both_as_correction_allows_commit_without_deleting_original(client, drain_jobs, db_session):
    from sqlalchemy import select

    from app.domains.canonical_financial.models import DatasetOverlapFlag

    import_id = _commit_baseline_then_conflicting(client, drain_jobs)
    datasets_before = client.get("/api/v1/datasets").json()
    assert len(datasets_before) == 1

    flag = db_session.execute(
        select(DatasetOverlapFlag).where(DatasetOverlapFlag.pending_import_batch_id == import_id)
    ).scalars().first()

    client.post(f"/api/v1/overlap/{flag.id}/resolve", json={"resolution": "kept_both_as_correction", "resolved_by": "analista@demo.local"})

    commit_resp = client.post(f"/api/v1/imports/{import_id}/commit")
    assert commit_resp.json()["status"] == "committed"

    datasets_after = client.get("/api/v1/datasets").json()
    assert len(datasets_after) == 2  # ambos coexistem — nunca excluiu o original


def test_overlap_replace_approved_is_accepted_but_not_implemented_commit_stays_blocked(client, drain_jobs, db_session):
    from sqlalchemy import select

    from app.domains.canonical_financial.models import DatasetOverlapFlag

    import_id = _commit_baseline_then_conflicting(client, drain_jobs)
    flag = db_session.execute(
        select(DatasetOverlapFlag).where(DatasetOverlapFlag.pending_import_batch_id == import_id)
    ).scalars().first()

    resolve_resp = client.post(f"/api/v1/overlap/{flag.id}/resolve", json={"resolution": "replace_approved", "resolved_by": "analista@demo.local"})
    assert resolve_resp.json()["note"] is not None  # avisa explicitamente que não está implementado

    commit_resp = client.post(f"/api/v1/imports/{import_id}/commit")
    assert commit_resp.json()["status"] == "overlap_pending"  # ainda bloqueado — nunca substitui sozinho


def test_duplicate_candidates_endpoint_lists_matching_natural_key_hash(client, drain_jobs, db_session):
    from sqlalchemy import select

    from app.domains.canonical_financial.models import Dataset, DatasetOverlapFlag

    import_id = _commit_baseline_then_conflicting(client, drain_jobs)
    flag = db_session.execute(
        select(DatasetOverlapFlag).where(DatasetOverlapFlag.pending_import_batch_id == import_id)
    ).scalars().first()
    client.post(f"/api/v1/overlap/{flag.id}/resolve", json={"resolution": "kept_both_as_correction", "resolved_by": "x"})
    client.post(f"/api/v1/imports/{import_id}/commit")

    new_dataset_id = next(
        d.id for d in db_session.execute(select(Dataset)).scalars().all() if str(d.import_batch_id) == import_id
    )

    candidates = client.get(f"/api/v1/datasets/{new_dataset_id}/overlap/{flag.id}/candidates").json()
    # Só 1 linha difere entre os dois arquivos — as demais ~247 devem bater por natural_key_hash
    assert len(candidates) > 200
