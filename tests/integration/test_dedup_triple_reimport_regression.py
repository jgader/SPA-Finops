"""Regressão: 3+ reimportações idênticas não devem quebrar o dedup (bug real encontrado em
teste manual via navegador — múltiplos import_batch 'committed' com o mesmo hash faziam
find_committed_duplicate levantar MultipleResultsFound)."""

import os

FIXTURES = os.path.join(os.path.dirname(__file__), "..", "..", "packages", "fixtures", "data")


def test_three_successive_identical_uploads_all_resolve_to_committed(client, drain_jobs):
    path = os.path.join(FIXTURES, "focus_clean_baseline.csv")
    ids = []
    for _ in range(3):
        with open(path, "rb") as handle:
            resp = client.post("/api/v1/imports", files={"file": ("focus_clean_baseline.csv", handle, "text/csv")})
        ids.append(resp.json()["id"])
        drain_jobs()

    for import_id in ids:
        status = client.get(f"/api/v1/imports/{import_id}").json()
        assert status["status"] == "committed", status

    datasets = client.get("/api/v1/datasets").json()
    assert len(datasets) == 1  # ainda só 1 dataset real — os outros 2 foram no-op
