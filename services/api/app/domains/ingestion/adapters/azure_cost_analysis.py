"""Adapter concreto para o export nativo Azure Cost Analysis (não-FOCUS). Serve de segunda
fonte para a reconciliação de F2; aqui em F1 só é importado e normalizado, nunca comparado
(docs/PLANO_EXECUCAO_F1.md seção 0). Este export não tem as 4 colunas de cost basis lado a
lado nem período de uso efetivo separado do faturamento — por isso granularidade cai para
'billing_period_fallback' (seção 6-ajuste-3) e effective/list/contracted ficam None, não
inventados."""

from decimal import Decimal

from app.domains.ingestion.adapters.base import (
    ISO_4217_KNOWN,
    FieldMappingEntry,
    MappedRow,
    ProviderAdapter,
    RowIssue,
    RowResult,
)

_REQUIRED = {"SubscriptionId", "ServiceName", "BillingMonth", "Cost", "Currency", "ChargeType"}

_CHARGE_TYPE_MAP = {"Usage": "Usage", "Purchase": "Purchase", "Refund": "Credit"}


class AzureCostAnalysisAdapter(ProviderAdapter):
    provider = "azure"
    schema_version = "azure-cost-analysis-native-1"

    def identify(self, header: list[str]) -> bool:
        return _REQUIRED.issubset(set(header))

    def field_mapping(self) -> list[FieldMappingEntry]:
        mapping = {
            "SubscriptionId": ("billing_account", None, Decimal("1.000")),
            "ResourceGroup": ("sub_account", None, Decimal("1.000")),
            "ServiceName": ("service", None, Decimal("1.000")),
            "InstanceId": ("resource_id", None, Decimal("1.000")),
            "ResourceLocation": ("region", None, Decimal("1.000")),
            "BillingMonth": ("billing_start+billing_end", "month_to_period_bounds", Decimal("0.900")),
            "Quantity": ("pricing_qty", None, Decimal("1.000")),
            "UnitOfMeasure": ("pricing_unit", None, Decimal("1.000")),
            "Cost": ("billed_cost", None, Decimal("1.000")),
            "Currency": ("currency", None, Decimal("1.000")),
            "ChargeType": ("charge_category", "native_charge_type_to_focus_category", Decimal("0.800")),
        }
        return [
            FieldMappingEntry(source, canonical, transform, confidence)
            for source, (canonical, transform, confidence) in mapping.items()
        ]

    def map_row(self, raw: dict[str, str], row_offset: int, raw_ref: str) -> RowResult:
        issues: list[RowIssue] = []

        billing_account = (raw.get("SubscriptionId") or "").strip()
        if not billing_account:
            issues.append(RowIssue(row_offset, "error", "missing_required_field", "SubscriptionId"))

        service = (raw.get("ServiceName") or "").strip()
        if not service:
            issues.append(RowIssue(row_offset, "error", "missing_required_field", "ServiceName"))

        native_charge_type = (raw.get("ChargeType") or "").strip()
        charge_category = _CHARGE_TYPE_MAP.get(native_charge_type)
        if charge_category is None:
            issues.append(RowIssue(row_offset, "error", "invalid_charge_category", "ChargeType"))

        billing_start, billing_end = self._month_bounds(raw.get("BillingMonth"))
        if billing_start is None or billing_end is None:
            issues.append(RowIssue(row_offset, "error", "missing_or_invalid_datetime", "BillingMonth"))

        currency = (raw.get("Currency") or "").strip().upper()
        if len(currency) != 3:
            issues.append(RowIssue(row_offset, "error", "invalid_currency_format", "Currency"))
        elif currency not in ISO_4217_KNOWN:
            issues.append(RowIssue(row_offset, "warning", "currency_not_in_known_set", "Currency"))

        billed_cost = self.parse_decimal(raw.get("Cost"))
        if billed_cost is None:
            issues.append(RowIssue(row_offset, "error", "missing_or_invalid_decimal", "Cost"))

        if any(issue.severity == "error" for issue in issues):
            return RowResult(row=None, issues=issues)

        row = MappedRow(
            row_offset=row_offset,
            provider=self.provider,
            billing_account=billing_account,
            sub_account=(raw.get("ResourceGroup") or "").strip() or None,
            resource_id=(raw.get("InstanceId") or "").strip() or None,
            service=service,
            region=(raw.get("ResourceLocation") or "").strip() or None,
            charge_category=charge_category,
            billing_start=billing_start,
            billing_end=billing_end,
            usage_start=None,
            usage_end=None,
            pricing_qty=self.parse_decimal(raw.get("Quantity")),
            pricing_unit=(raw.get("UnitOfMeasure") or "").strip() or None,
            currency=currency,
            billed_cost=billed_cost,
            effective_cost=None,
            list_cost=None,
            contracted_cost=None,
            raw_ref=raw_ref,
        )
        return RowResult(row=row, issues=issues)

    @staticmethod
    def _month_bounds(raw_value: str | None):
        """BillingMonth vem como 'YYYY-MM'. Período de faturamento = mês inteiro."""
        if not raw_value or len(raw_value.strip()) != 7:
            return None, None
        try:
            from datetime import datetime, timezone
            import calendar

            year, month = (int(part) for part in raw_value.strip().split("-"))
            start = datetime(year, month, 1, tzinfo=timezone.utc)
            last_day = calendar.monthrange(year, month)[1]
            end = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)
            return start, end
        except (ValueError, IndexError):
            return None, None
