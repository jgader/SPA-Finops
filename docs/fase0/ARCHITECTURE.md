# Arquitetura técnica e contratos entre camadas

## Topologia local
Browser React SPA (porta 5173 desenvolvimento) → API FastAPI (localhost:8000) → serviços de ingestão, cálculo, forecast, oportunidades e agente → PostgreSQL local + artefatos Parquet locais. DuckDB/Polars para agregação analítica. O worker processa jobs assíncronos; nunca bloquear requisições com parsing grande. Claude API chamada EXCLUSIVAMENTE pelo backend com consentimento.

## Stack sugerida, não obrigação de versão
React + TypeScript + Vite; Tailwind/shadcn/ui; Apache ECharts; Python FastAPI/Pydantic; Polars/DuckDB; PostgreSQL; SQLAlchemy/Alembic; pytest; Playwright; Docker Compose opcional. Manter versões pinadas e lockfiles.

## Domínios
- `ingestion`: adapters, sniff, schema mapping, validation, dedup, staging e commit.
- `canonical_financial`: fato FOCUS de custo/uso, dim resource, dim billing scope e compromisso quando aplicável.
- `operations`: métricas CPU/memória, inventário, ownership, preços, change events.
- `analytics`: agregação, regras de métricas, provenance, drill-down.
- `forecast`: baseline, parametrização e avaliação holdout.
- `optimization`: oportunidades, exclusões, confidence, simulação.
- `ai`: ferramentas allowlist; prompts; logs sem secrets.
- `governance`: ownership, regras e estados.
- `reporting`: snapshot imutável e export.

## Estrutura de repositório
```
finops-ai/
  apps/web/src/{app,components,features,design-system}
  services/api/app/{api,config,db,domains,schemas,security}
  services/worker/
  packages/{contracts,fixtures}
  data/{incoming,staging,warehouse,exports}
  docs/
  tests/{unit,integration,e2e,security}
  docker-compose.yml
  .env.example
```

## API inicial (v1)
`POST /api/v1/imports` inicia upload; `GET /imports/{id}` status; `POST /imports/{id}/commit` valida e consolida; `GET /datasets` lista; `GET /datasets/{id}/quality` qualidade; `GET /analytics/costs` agregações; `GET /analytics/kpis`; `POST /analysis-runs`; `GET /analysis-runs/{id}`; `GET /opportunities`; `PATCH /opportunities/{id}` altera estado; `POST /scenarios`; `GET /scenarios/{id}`; `POST /assistant/chat` (se habilitado); `GET /reports/{id}`.
Todas respostas de KPIs retornam `source_dataset_ids`, `calculation_version`, `freshness`, `currency`, `cost_basis`, `confidence`, `warnings`.

## Estados assíncronos
`uploaded → detected → validated → staged → committed` ou `rejected`. `analysis_run`: queued→running→completed/failed, com logs e erro recuperável.

## Design para multicloud
`ProviderAdapter` com `identify(input)`, `validate(input)`, `map_financial(input)`, `map_inventory(input)`, `map_metrics(input)` e `capabilities()`. A compatibilidade depende do esquema real, não da string do provider. Preservar extensão não mapeada e versionar adapters.

## Padrões de qualidade
Nunca perder dados brutos; armazenar checksum e procedência, distinguir granularidade diária/mensal; não somar moedas distintas; versionar FX externo; não misturar custos faturados, efetivos e preço de lista; reconciliar por dimensão antes de publicar totais.
