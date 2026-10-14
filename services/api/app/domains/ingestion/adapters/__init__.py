from app.domains.ingestion.adapters.azure_cost_analysis import AzureCostAnalysisAdapter
from app.domains.ingestion.adapters.base import ProviderAdapter
from app.domains.ingestion.adapters.focus_1_0r2 import FocusAzureAdapter

ADAPTERS: list[ProviderAdapter] = [FocusAzureAdapter(), AzureCostAnalysisAdapter()]


def find_adapter(header: list[str]) -> ProviderAdapter | None:
    for adapter in ADAPTERS:
        if adapter.identify(header):
            return adapter
    return None
