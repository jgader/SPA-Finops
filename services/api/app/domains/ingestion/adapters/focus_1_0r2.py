"""Adapter concreto para Azure FOCUS 1.0r2 (docs/AUDITORIA_VIABILIDADE_POV.md, decisão 1:
primeiro adapter concreto é 1.0r2; referência futura a FOCUS 1.4 fica em capabilities())."""

from decimal import Decimal

from app.domains.ingestion.adapters.base import (
    ISO_4217_KNOWN,
    FieldMappingEntry,
    MappedRow,
    ProviderAdapter,
    RowIssue,
    RowResult,
)

_HEADER = [
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

_REQUIRED = {"BillingAccountId", "ServiceName", "ChargeCategory", "BillingPeriodStart", "BillingPeriodEnd", "BillingCurrency", "BilledCost"}


class FocusAzureAdapter(ProviderAdapter):
    provider = "azure"
    schema_version = "focus-1.0r2"

    def identify(self, header: list[str]) -> bool:
        return _REQUIRED.issubset(set(header))

    def field_mapping(self) -> list[FieldMappingEntry]:
        mapping = {
            "BillingAccountId": "billing_account",
            "SubAccountId": "sub_account",
            "ServiceName": "service",
            "ResourceId": "resource_id",
            "RegionId": "region",
            "ChargeCategory": "charge_category",
            "BillingPeriodStart": "billing_start",
            "BillingPeriodEnd": "billing_end",
            "ChargePeriodStart": "usage_start",
            "ChargePeriodEnd": "usage_end",
            "PricingQuantity": "pricing_qty",
            "PricingUnit": "pricing_unit",
            "BillingCurrency": "currency",
            "BilledCost": "billed_cost",
            "EffectiveCost": "effective_cost",
            "ListCost": "list_cost",
            "ContractedCost": "contracted_cost",
        }
        return [
            FieldMappingEntry(source, canonical, transform_applied=None, confidence=Decimal("1.000"))
            for source, canonical in mapping.items()
        ]

    def map_row(self, raw: dict[str, str], row_offset: int, raw_ref: str) -> RowResult:
        issues: list[RowIssue] = []

        billing_account = (raw.get("BillingAccountId") or "").strip()
        if not billing_account:
            issues.append(RowIssue(row_offset, "error", "missing_required_field", "BillingAccountId"))

        service = (raw.get("ServiceName") or "").strip()
        if not service:
            issues.append(RowIssue(row_offset, "error", "missing_required_field", "ServiceName"))

        charge_category = (raw.get("ChargeCategory") or "").strip()
        if charge_category not in {"Usage", "Purchase", "Tax", "Credit", "Adjustment"}:
            issues.append(RowIssue(row_offset, "error", "invalid_charge_category", "ChargeCategory"))

        billing_start = self.parse_datetime(raw.get("BillingPeriodStart"))
        if billing_start is None:
            issues.append(RowIssue(row_offset, "error", "missing_or_invalid_datetime", "BillingPeriodStart"))

        billing_end = self.parse_datetime(raw.get("BillingPeriodEnd"))
        if billing_end is None:
            issues.append(RowIssue(row_offset, "error", "missing_or_invalid_datetime", "BillingPeriodEnd"))

        currency = (raw.get("BillingCurrency") or "").strip().upper()
        if len(currency) != 3:
            issues.append(RowIssue(row_offset, "error", "invalid_currency_format", "BillingCurrency"))
        elif currency not in ISO_4217_KNOWN:
            issues.append(RowIssue(row_offset, "warning", "currency_not_in_known_set", "BillingCurrency"))

        billed_cost = self.parse_decimal(raw.get("BilledCost"))
        if billed_cost is None:
            issues.append(RowIssue(row_offset, "error", "missing_or_invalid_decimal", "BilledCost"))

        usage_start = self.parse_datetime(raw.get("ChargePeriodStart"))
        usage_end = self.parse_datetime(raw.get("ChargePeriodEnd"))
        if raw.get("ChargePeriodStart") and usage_start is None:
            issues.append(RowIssue(row_offset, "warning", "invalid_datetime_format", "ChargePeriodStart"))
        if raw.get("ChargePeriodEnd") and usage_end is None:
            issues.append(RowIssue(row_offset, "warning", "invalid_datetime_format", "ChargePeriodEnd"))

        if any(issue.severity == "error" for issue in issues):
            return RowResult(row=None, issues=issues)

        row = MappedRow(
            row_offset=row_offset,
            provider=self.provider,
            billing_account=billing_account,
            sub_account=(raw.get("SubAccountId") or "").strip() or None,
            resource_id=(raw.get("ResourceId") or "").strip() or None,
            service=service,
            region=(raw.get("RegionId") or "").strip() or None,
            charge_category=charge_category,
            billing_start=billing_start,
            billing_end=billing_end,
            usage_start=usage_start,
            usage_end=usage_end,
            pricing_qty=self.parse_decimal(raw.get("PricingQuantity")),
            pricing_unit=(raw.get("PricingUnit") or "").strip() or None,
            currency=currency,
            billed_cost=billed_cost,
            effective_cost=self.parse_decimal(raw.get("EffectiveCost")),
            list_cost=self.parse_decimal(raw.get("ListCost")),
            contracted_cost=self.parse_decimal(raw.get("ContractedCost")),
            raw_ref=raw_ref,
        )
        return RowResult(row=row, issues=issues)
