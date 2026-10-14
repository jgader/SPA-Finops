"""Cálculo de granularidade — ajuste 3 do GO condicional (docs/PLANO_EXECUCAO_F1.md seção 6):
infere a partir do período de USO efetivo quando disponível; billing_period é fallback
explícito e mais fraco; 'unknown' quando não há evidência suficiente em nenhum dos dois."""

from collections import Counter

from app.domains.ingestion.adapters.base import MappedRow


def _classify_span_days(span_days: float) -> str | None:
    if 0.9 <= span_days <= 1.1:
        return "daily"
    if 27 <= span_days <= 31:
        return "monthly"
    return None


def compute_granularity(rows: list[MappedRow]) -> tuple[str, str]:
    """Retorna (granularity, granularity_source)."""
    if not rows:
        return "unknown", "insufficient_evidence"

    usage_spans = []
    for row in rows:
        if row.usage_start is not None and row.usage_end is not None:
            span_days = (row.usage_end - row.usage_start).total_seconds() / 86400
            classified = _classify_span_days(span_days)
            if classified:
                usage_spans.append(classified)

    if usage_spans:
        counts = Counter(usage_spans)
        distinct = set(counts)
        if len(distinct) > 1:
            return "mixed", "usage_period"
        return distinct.pop(), "usage_period"

    billing_spans = []
    for row in rows:
        span_days = (row.billing_end - row.billing_start).total_seconds() / 86400
        classified = _classify_span_days(span_days)
        if classified:
            billing_spans.append(classified)

    if billing_spans:
        counts = Counter(billing_spans)
        distinct = set(counts)
        if len(distinct) > 1:
            return "mixed", "billing_period_fallback"
        return distinct.pop(), "billing_period_fallback"

    return "unknown", "insufficient_evidence"
