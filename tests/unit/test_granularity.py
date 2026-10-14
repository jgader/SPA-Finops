from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.domains.ingestion.adapters.base import MappedRow
from app.domains.ingestion.granularity import compute_granularity


def _row(usage_start=None, usage_end=None, billing_start=None, billing_end=None) -> MappedRow:
    b_start = billing_start or datetime(2026, 8, 1, tzinfo=timezone.utc)
    b_end = billing_end or datetime(2026, 8, 31, tzinfo=timezone.utc)
    return MappedRow(
        row_offset=1, provider="azure", billing_account="sub-1", sub_account=None, resource_id=None,
        service="VirtualMachines", region=None, charge_category="Usage",
        billing_start=b_start, billing_end=b_end, usage_start=usage_start, usage_end=usage_end,
        pricing_qty=None, pricing_unit=None, currency="BRL", billed_cost=Decimal("1"),
        effective_cost=None, list_cost=None, contracted_cost=None, raw_ref="x",
    )


def test_empty_rows_is_unknown_insufficient_evidence():
    assert compute_granularity([]) == ("unknown", "insufficient_evidence")


def test_daily_usage_period_detected():
    day = datetime(2026, 8, 5, tzinfo=timezone.utc)
    rows = [_row(usage_start=day, usage_end=day + timedelta(days=1)) for _ in range(5)]
    assert compute_granularity(rows) == ("daily", "usage_period")


def test_monthly_usage_period_detected():
    rows = [_row(
        usage_start=datetime(2026, 8, 1, tzinfo=timezone.utc),
        usage_end=datetime(2026, 8, 31, tzinfo=timezone.utc),
    )]
    assert compute_granularity(rows) == ("monthly", "usage_period")


def test_mixed_usage_period_detected():
    day = datetime(2026, 8, 5, tzinfo=timezone.utc)
    rows = [
        _row(usage_start=day, usage_end=day + timedelta(days=1)),
        _row(usage_start=datetime(2026, 8, 1, tzinfo=timezone.utc), usage_end=datetime(2026, 8, 31, tzinfo=timezone.utc)),
    ]
    assert compute_granularity(rows) == ("mixed", "usage_period")


def test_falls_back_to_billing_period_when_usage_absent():
    rows = [_row(usage_start=None, usage_end=None) for _ in range(3)]  # billing span = 1 mês inteiro
    granularity, source = compute_granularity(rows)
    assert granularity == "monthly"
    assert source == "billing_period_fallback"


def test_unknown_when_neither_period_gives_evidence():
    rows = [_row(
        usage_start=None, usage_end=None,
        billing_start=datetime(2026, 8, 1, tzinfo=timezone.utc),
        billing_end=datetime(2026, 8, 3, tzinfo=timezone.utc),  # nem diário nem mensal
    )]
    assert compute_granularity(rows) == ("unknown", "insufficient_evidence")
