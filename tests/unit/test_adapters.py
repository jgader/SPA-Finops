from decimal import Decimal

from app.domains.ingestion.adapters.azure_cost_analysis import AzureCostAnalysisAdapter
from app.domains.ingestion.adapters.focus_1_0r2 import FocusAzureAdapter

FOCUS_HEADER = [
    "BillingAccountId", "SubAccountId", "ServiceName", "ResourceId", "RegionId", "ChargeCategory",
    "BillingPeriodStart", "BillingPeriodEnd", "ChargePeriodStart", "ChargePeriodEnd",
    "PricingQuantity", "PricingUnit", "BillingCurrency", "BilledCost", "EffectiveCost",
    "ListCost", "ContractedCost",
]

AZURE_HEADER = [
    "SubscriptionId", "ResourceGroup", "ServiceName", "InstanceId", "ResourceLocation",
    "BillingMonth", "Quantity", "UnitOfMeasure", "Cost", "Currency", "ChargeType",
]


def test_focus_adapter_identifies_header():
    adapter = FocusAzureAdapter()
    assert adapter.identify(FOCUS_HEADER)
    assert not adapter.identify(AZURE_HEADER)


def test_azure_adapter_identifies_header():
    adapter = AzureCostAnalysisAdapter()
    assert adapter.identify(AZURE_HEADER)
    assert not adapter.identify(FOCUS_HEADER)


def test_focus_adapter_maps_valid_row():
    adapter = FocusAzureAdapter()
    raw = dict(zip(FOCUS_HEADER, [
        "sub-1", "rg-1", "VirtualMachines", "vm-1", "brazilsouth", "Usage",
        "2026-08-01T00:00:00Z", "2026-08-31T23:59:59Z", "2026-08-01T00:00:00Z", "2026-08-02T00:00:00Z",
        "24", "Hours", "BRL", "120.500000", "110.000000", "140.000000", "115.000000",
    ]))
    result = adapter.map_row(raw, row_offset=1, raw_ref="hash:1")
    assert result.row is not None
    assert result.issues == []
    assert result.row.billed_cost == Decimal("120.500000")
    assert result.row.currency == "BRL"


def test_focus_adapter_rejects_missing_required_field():
    adapter = FocusAzureAdapter()
    raw = dict(zip(FOCUS_HEADER, [
        "", "rg-1", "VirtualMachines", "vm-1", "brazilsouth", "Usage",
        "2026-08-01T00:00:00Z", "2026-08-31T23:59:59Z", "", "",
        "24", "Hours", "BRL", "120.500000", "", "", "",
    ]))
    result = adapter.map_row(raw, row_offset=2, raw_ref="hash:2")
    assert result.row is None
    assert any(i.severity == "error" and i.reason_code == "missing_required_field" for i in result.issues)


def test_focus_adapter_rejects_invalid_decimal_never_silently_coerces():
    adapter = FocusAzureAdapter()
    raw = dict(zip(FOCUS_HEADER, [
        "sub-1", "rg-1", "VirtualMachines", "vm-1", "brazilsouth", "Usage",
        "2026-08-01T00:00:00Z", "2026-08-31T23:59:59Z", "", "",
        "24", "Hours", "BRL", "not_a_number", "", "", "",
    ]))
    result = adapter.map_row(raw, row_offset=3, raw_ref="hash:3")
    assert result.row is None
    assert any(i.reason_code == "missing_or_invalid_decimal" for i in result.issues)


def test_focus_adapter_never_sums_currencies_itself_just_flags_unknown():
    adapter = FocusAzureAdapter()
    raw = dict(zip(FOCUS_HEADER, [
        "sub-1", "rg-1", "VirtualMachines", "vm-1", "brazilsouth", "Usage",
        "2026-08-01T00:00:00Z", "2026-08-31T23:59:59Z", "", "",
        "24", "Hours", "ZZZ", "120.500000", "", "", "",
    ]))
    result = adapter.map_row(raw, row_offset=4, raw_ref="hash:4")
    assert result.row is not None  # formato ISO 4217 válido (3 letras), só fora do conjunto conhecido
    assert any(i.severity == "warning" and i.reason_code == "currency_not_in_known_set" for i in result.issues)


def test_focus_adapter_capabilities_lists_focus_1_4_gaps():
    adapter = FocusAzureAdapter()
    caps = adapter.capabilities()
    assert caps["focus_reference_version"] == "1.4"
    assert caps["detected_schema_version"] == "focus-1.0r2"
    assert "SkuPriceId" in caps["fields_not_present_in_source_version"]


def test_azure_adapter_maps_native_charge_type_to_focus_category():
    adapter = AzureCostAnalysisAdapter()
    raw = dict(zip(AZURE_HEADER, [
        "sub-2", "rg-1", "Storage", "res-1", "brazilsouth", "2026-08", "720", "Hours",
        "300.000000", "BRL", "Refund",
    ]))
    result = adapter.map_row(raw, row_offset=1, raw_ref="hash:1")
    assert result.row is not None
    assert result.row.charge_category == "Credit"
    assert result.row.usage_start is None  # export nativo não tem período de uso separado
