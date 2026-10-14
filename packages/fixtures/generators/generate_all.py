"""Gera as 8 fixtures sintéticas de F1 (a 9ª, nome de arquivo malicioso, reusa o conteúdo
limpo do baseline — não precisa de conteúdo próprio). Determinístico: mesma saída sempre."""

import shutil
from datetime import timedelta

from common import AZURE_NATIVE_HEADER, FOCUS_HEADER, focus_row, month_bounds, write_csv

SERVICES = [
    "VirtualMachines",
    "Storage",
    "Networking",
    "DatabaseServices",
    "Monitoring",
    "LoadBalancer",
    "KeyVault",
    "AppService",
]


def gen_clean_baseline() -> str:
    rows = []
    for year, month in ((2026, 8), (2026, 9)):
        b_start, b_end = month_bounds(year, month)
        day = b_start
        while day <= b_end:
            for idx, service in enumerate(SERVICES):
                rows.append(
                    focus_row(
                        service=service,
                        resource_id=f"demo-res-{idx:03d}",
                        billing_start=b_start,
                        billing_end=b_end,
                        usage_start=day,
                        usage_end=day + timedelta(days=1),
                        billed_cost=f"{10 + idx:.6f}",
                    )
                )
            day += timedelta(days=1)
    return write_csv("focus_clean_baseline.csv", FOCUS_HEADER, rows)


def gen_overlap_reimport(baseline_path: str) -> str:
    import os

    dest = os.path.join(os.path.dirname(baseline_path), "focus_overlap_reimport.csv")
    shutil.copyfile(baseline_path, dest)
    return dest


def gen_same_period_different_hash() -> str:
    year, month = 2026, 8
    b_start, b_end = month_bounds(year, month)
    rows = []
    day = b_start
    while day <= b_end:
        for idx, service in enumerate(SERVICES):
            cost = 10 + idx
            if day == b_start and idx == 0:
                cost = 999  # única diferença: muda o hash do arquivo, mesmo scope+period
            rows.append(
                focus_row(
                    service=service,
                    resource_id=f"demo-res-{idx:03d}",
                    billing_start=b_start,
                    billing_end=b_end,
                    usage_start=day,
                    usage_end=day + timedelta(days=1),
                    billed_cost=f"{cost:.6f}",
                )
            )
        day += timedelta(days=1)
    return write_csv("focus_same_period_different_hash.csv", FOCUS_HEADER, rows)


def gen_malformed() -> str:
    b_start, b_end = month_bounds(2026, 8)
    good = focus_row(billing_start=b_start, billing_end=b_end, usage_start=b_start, usage_end=b_start)
    rows = [good]

    missing_account = focus_row(
        billing_account="", billing_start=b_start, billing_end=b_end, usage_start=b_start, usage_end=b_start
    )
    rows.append(missing_account)

    bad_cost = focus_row(
        billing_start=b_start, billing_end=b_end, usage_start=b_start, usage_end=b_start, billed_cost="not_a_number"
    )
    rows.append(bad_cost)

    bad_currency = focus_row(
        billing_start=b_start, billing_end=b_end, usage_start=b_start, usage_end=b_start, currency="US"
    )
    rows.append(bad_currency)

    bad_category = focus_row(
        billing_start=b_start, billing_end=b_end, usage_start=b_start, usage_end=b_start, charge_category="Weird"
    )
    rows.append(bad_category)

    rows.append(good)  # duplicata exata (linha repetida) — ainda assim é só mais uma linha válida
    return write_csv("focus_malformed.csv", FOCUS_HEADER, rows)


def gen_multicurrency() -> str:
    b_start, b_end = month_bounds(2026, 8)
    rows = []
    for idx, service in enumerate(SERVICES):
        currency = "BRL" if idx % 2 == 0 else "USD"
        rows.append(
            focus_row(
                service=service,
                resource_id=f"demo-res-{idx:03d}",
                billing_start=b_start,
                billing_end=b_end,
                usage_start=b_start,
                usage_end=b_start,
                currency=currency,
                billed_cost=f"{50 + idx:.6f}",
            )
        )
    return write_csv("focus_multicurrency.csv", FOCUS_HEADER, rows)


def gen_mixed_granularity() -> str:
    b_start, b_end = month_bounds(2026, 8)
    rows = []
    for idx, service in enumerate(SERVICES[:4]):
        rows.append(
            focus_row(
                service=service,
                resource_id=f"demo-daily-{idx:03d}",
                billing_start=b_start,
                billing_end=b_end,
                usage_start=b_start,
                usage_end=b_start + timedelta(days=1),
                billed_cost=f"{20 + idx:.6f}",
            )
        )
    for idx, service in enumerate(SERVICES[4:]):
        rows.append(
            focus_row(
                service=service,
                resource_id=f"demo-monthly-{idx:03d}",
                billing_start=b_start,
                billing_end=b_end,
                usage_start=b_start,
                usage_end=b_end,
                billed_cost=f"{30 + idx:.6f}",
            )
        )
    return write_csv("focus_mixed_granularity.csv", FOCUS_HEADER, rows)


def gen_perf_100k(n: int = 100_000) -> str:
    b_start, b_end = month_bounds(2026, 8)
    days_in_month = (b_end.date() - b_start.date()).days + 1
    rows = []
    for i in range(n):
        day = b_start + timedelta(days=i % days_in_month)
        rows.append(
            focus_row(
                resource_id=f"demo-res-{i % 1000:04d}",
                billing_start=b_start,
                billing_end=b_end,
                usage_start=day,
                usage_end=day + timedelta(days=1),
                billed_cost=f"{(i % 500) + 1:.6f}",
            )
        )
    return write_csv("focus_perf_100k.csv", FOCUS_HEADER, rows)


def gen_azure_cost_analysis_equivalent() -> str:
    rows = [
        [
            "demo-sub-0002",
            "demo-rg-finops",
            service,
            f"demo-res-{idx:03d}",
            "brazilsouth",
            "2026-08",
            "720",
            "Hours",
            f"{300 + idx * 10:.6f}",
            "BRL",
            "Usage",
        ]
        for idx, service in enumerate(SERVICES)
    ]
    return write_csv("azure_cost_analysis_equivalent.csv", AZURE_NATIVE_HEADER, rows)


def main() -> None:
    baseline = gen_clean_baseline()
    gen_overlap_reimport(baseline)
    gen_same_period_different_hash()
    gen_malformed()
    gen_multicurrency()
    gen_mixed_granularity()
    gen_perf_100k()
    gen_azure_cost_analysis_equivalent()
    print("fixtures geradas em packages/fixtures/data/")


if __name__ == "__main__":
    main()
