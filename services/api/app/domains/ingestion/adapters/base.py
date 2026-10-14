"""ProviderAdapter — interface comum (ARCHITECTURE.md). Nenhum código de domínio fora dos
adapters concretos conhece "Azure"; isso é o que garante independência do FinOps Hubs
(docs/PLANO_EXECUCAO_F1.md seção 9) e permite, no futuro, adapters de outros provedores."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation


@dataclass
class FieldMappingEntry:
    source_field: str
    canonical_field: str
    transform_applied: str | None
    confidence: Decimal


@dataclass
class RowIssue:
    row_offset: int
    severity: str  # info | warning | error
    reason_code: str
    field: str | None


@dataclass
class MappedRow:
    row_offset: int
    provider: str
    billing_account: str
    sub_account: str | None
    resource_id: str | None
    service: str
    region: str | None
    charge_category: str
    billing_start: datetime
    billing_end: datetime
    usage_start: datetime | None
    usage_end: datetime | None
    pricing_qty: Decimal | None
    pricing_unit: str | None
    currency: str
    billed_cost: Decimal
    effective_cost: Decimal | None
    list_cost: Decimal | None
    contracted_cost: Decimal | None
    raw_ref: str


@dataclass
class RowResult:
    row: MappedRow | None
    issues: list[RowIssue] = field(default_factory=list)


ISO_4217_KNOWN = {"USD", "BRL", "EUR", "GBP", "JPY", "AUD", "CAD"}

_FOCUS_1_4_FIELDS_NOT_IN_1_0R2 = {
    "SkuPriceId",
    "PricingCategory",
    "ServiceSubcategory",
    "CommitmentDiscountId",
    "CommitmentDiscountType",
}


class ProviderAdapter(ABC):
    provider: str
    schema_version: str

    @abstractmethod
    def identify(self, header: list[str]) -> bool:
        """Esse adapter reconhece este cabeçalho? Nunca assume versão — só confirma."""

    @abstractmethod
    def field_mapping(self) -> list[FieldMappingEntry]:
        """Mapeamento declarado, persistido em import_field_mapping no momento do staging."""

    @abstractmethod
    def map_row(self, raw: dict[str, str], row_offset: int, raw_ref: str) -> RowResult:
        """Converte uma linha bruta em MappedRow, ou devolve issues se inválida.
        Nunca inventa valor para campo ausente — ausência é ausência, registrada como tal."""

    def capabilities(self) -> dict:
        """Campos do baseline FOCUS 1.4 que este adapter concreto não preenche —
        nunca inferidos, sempre deixados ausentes com proveniência explícita
        (docs/PLANO_EXECUCAO_F1.md seção 3)."""
        return {
            "focus_reference_version": "1.4",
            "detected_schema_version": self.schema_version,
            "fields_not_present_in_source_version": sorted(_FOCUS_1_4_FIELDS_NOT_IN_1_0R2),
        }

    @staticmethod
    def parse_decimal(raw_value: str | None) -> Decimal | None:
        """Decimal, nunca float — valor malformado retorna None (validação decide severidade)."""
        if raw_value is None or raw_value.strip() == "":
            return None
        try:
            return Decimal(raw_value.strip())
        except InvalidOperation:
            return None

    @staticmethod
    def parse_datetime(raw_value: str | None) -> datetime | None:
        if raw_value is None or raw_value.strip() == "":
            return None
        try:
            value = raw_value.strip()
            if value.endswith("Z"):
                value = value[:-1] + "+00:00"
            return datetime.fromisoformat(value)
        except ValueError:
            return None
