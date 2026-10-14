# Esquemas, FOCUS e qualidade dos dados

## FOCUS
Base de referência FOCUS 1.4 — datasets Cost and Usage (obrigatório segundo spec), Billing Period, Contract Commitment, Invoice Detail (condicionais): https://focus.finops.org/docs/specification/v1-4/datasets/ . Adaptadores aceitam versões detectadas na exportação e registram o esquema observado. NUNCA presumir que qualquer provedor emite 1.4 só porque ela é publicada.

## Dados de entrada
1) Cost and usage: csv/parquet FOCUS ou exportação de billing Azure reconhecida; 2) inventário: cloud provider, account, recurso, SKU, estado, região, tags, configuração, captura; 3) métricas: recurso, timestamp, métrica, unidade, agregação, valor, cobertura; 4) rate/pricing: SKU, tarifa, moeda, validade, origem; 5) business dimensions e volumes para unit economics; 6) budget/commitments/contract metadata.

## Modelo lógico mínimo
`import_batch(id, source_name, original_filename, sha256, uploaded_at, provider, format, schema_version, status, errors)`;
`dataset(id, import_batch_id, kind, period_start, period_end, provider, currency_set, row_count, quality_score, ingestion_version)`;
`cost_usage(id, dataset_id, provider, billing_account, sub_account, resource_id, service, region, charge_category, billing_start, billing_end, usage_start, usage_end, pricing_qty, pricing_unit, currency, billed_cost, effective_cost, list_cost, contracted_cost, raw_ref)`;
`resource(id, provider, account, native_id, type, sku, region, environment, criticality, owner, inventory_asof)`;
`resource_metric(id, resource_id, timestamp, name, unit, aggregation, value, sample_count, provenance)`;
`budget(id, scope, amount, currency, period)`;
`scenario(id, parent_id, assumptions_json, created_at, state)`;
`opportunity(id, type, resource_id, baseline_cost, projected_cost, savings_estimate, confidence, risk, assumptions_json, evidence_json, overlap_group, owner, state)`;
`savings_validation(id, opportunity_id, before_window, after_window, baseline_model, actual_savings, adjustments_json, status)`;
`analysis_run(id, dataset_versions, engine_versions, config_hash, timestamp, warnings)`.

## Import flow
1. Arquivo para staging local (limite configurável; scan e extensão MIME); 2. sniff delimitador, encoding, colunas e amostra; 3. detectar família e provider; 4. relatório de mapeamento; 5. parse temporal/decimal preservando bruto; 6. validar registros e quarentena; 7. preview de qualidade e pré-reconciliação; 8. commit explícito; 9. snapshots e análises; 10. reimportação idempotente por hash+escopo+período, com política de substituição explícita.

## Regras mínimas
- Decimais financeiros `Decimal` (nunca float nos cálculos de moeda); ISO-8601 UTC internamente, timezone original registrado.
- Strings de moeda ISO 4217 e nunca soma cross-currency sem taxa e data identificadas.
- Marcar valores nulos, ausentes e não aplicáveis separadamente.
- Evitar duplicidade entre linhas de actual e amortized ou datasets sobrepostos.
- Preservar metadados e campos provider-specific como extensões.
- Devolver `insufficient_data` se pricing, metrics ou granularidade não suportarem recomendação.

## Exemplo de retorno de análise (schema interno ilustrativo)
```json
{"metric_id":"monthly_cost","status":"verified","period_start":"2026-09-01","period_end":"2026-09-30","currency":"BRL","cost_basis":"billed","value":"12345.67","source_dataset_ids":["ds-001"],"calculation_version":"cost-v1","warnings":[]}
```
