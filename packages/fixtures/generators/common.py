import csv
import os
from datetime import datetime, timedelta, timezone

FOCUS_HEADER = [
    "BillingAccountId",
    "SubAccountId",
    "ServiceName",
    "ResourceId",
    "RegionId",
    "ChargeCategory",
    "BillingPeriodStart",
    "BillingPeriodEnd",
    "ChargePeriodStart",
    "ChargePeriodEnd",
    "PricingQuantity",
    "PricingUnit",
    "BillingCurrency",
    "BilledCost",
    "EffectiveCost",
    "ListCost",
    "ContractedCost",
]

AZURE_NATIVE_HEADER = [
    "SubscriptionId",
    "ResourceGroup",
    "ServiceName",
    "InstanceId",
    "ResourceLocation",
    "BillingMonth",
    "Quantity",
    "UnitOfMeasure",
    "Cost",
    "Currency",
    "ChargeType",
]

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    import calendar

    start = datetime(year, month, 1, tzinfo=timezone.utc)
    last_day = calendar.monthrange(year, month)[1]
    end = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)
    return start, end


def write_csv(filename: str, header: list[str], rows: list[list[str]]) -> str:
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
    return path


def focus_row(
    *,
    billing_account="demo-sub-0001",
    sub_account="demo-rg-finops",
    service="VirtualMachines",
    resource_id="demo-vm-001",
    region="brazilsouth",
    charge_category="Usage",
    billing_start,
    billing_end,
    usage_start=None,
    usage_end=None,
    qty="24",
    unit="Hours",
    currency="BRL",
    billed_cost="120.500000",
    effective_cost="110.000000",
    list_cost="140.000000",
    contracted_cost="115.000000",
) -> list[str]:
    return [
        billing_account,
        sub_account,
        service,
        resource_id,
        region,
        charge_category,
        iso(billing_start),
        iso(billing_end),
        iso(usage_start) if usage_start else "",
        iso(usage_end) if usage_end else "",
        qty,
        unit,
        currency,
        billed_cost,
        effective_cost,
        list_cost,
        contracted_cost,
    ]
