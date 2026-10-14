"""Três identidades distintas e nunca fundidas (docs/PLANO_EXECUCAO_F1.md seção 4):
(a) identidade de ARQUIVO -> sha256 do conteúdo bruto;
(b) identidade de DATASET -> scope_key (provider+billing_account+cost_basis_schema+kind);
(c) identidade de LANÇAMENTO FINANCEIRO -> natural_key_hash por linha."""

import hashlib
from datetime import datetime

from app.domains.ingestion.adapters.base import MappedRow


def file_sha256(file_path: str) -> str:
    digest = hashlib.sha256()
    with open(file_path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scope_key_for(provider: str, billing_account: str, kind: str) -> str:
    return f"{provider}:{billing_account}:{kind}"


def natural_key_hash(row: MappedRow) -> str:
    parts = [
        row.provider,
        row.billing_account,
        row.resource_id or "",
        row.service,
        row.charge_category,
        row.billing_start.isoformat(),
        row.billing_end.isoformat(),
    ]
    digest = hashlib.sha256("|".join(parts).encode("utf-8"))
    return digest.hexdigest()


def period_key(period_start: datetime, period_end: datetime) -> str:
    return f"{period_start.date().isoformat()}_{period_end.date().isoformat()}"
