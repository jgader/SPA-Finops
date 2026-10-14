"""Nenhum log gerado durante o ciclo de importação pode conter valor financeiro em texto
plano (seção 8 do plano) — varre os registros de log reais produzidos pelo worker ao
processar um import completo."""

import logging
import os

FIXTURES = os.path.join(os.path.dirname(__file__), "..", "..", "packages", "fixtures", "data")

# Valores de billed_cost conhecidos do fixture baseline (common.py/generate_all.py) —
# se qualquer um aparecer em texto plano no log, o log está vazando dado financeiro.
KNOWN_COST_VALUES = [f"{10 + i:.6f}" for i in range(8)]


def test_import_job_logs_never_contain_financial_values(client, drain_jobs, caplog):
    with caplog.at_level(logging.INFO, logger="finops_ai.worker.import_job"):
        path = os.path.join(FIXTURES, "focus_clean_baseline.csv")
        with open(path, "rb") as handle:
            resp = client.post("/api/v1/imports", files={"file": ("focus_clean_baseline.csv", handle, "text/csv")})
        drain_jobs()

    assert resp.status_code == 201
    full_log_text = "\n".join(record.getMessage() for record in caplog.records)

    for cost_value in KNOWN_COST_VALUES:
        assert cost_value not in full_log_text, f"valor financeiro {cost_value} apareceu em log"

    assert "billed_cost" not in full_log_text  # nem o nome do campo acompanhado de valor
