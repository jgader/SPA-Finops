# Plano de execução — F1: Fundação e Importação
Versão 1.0 | 14/10/2026 | Status: PROPOSTO PARA APROVAÇÃO — nenhum código escrito.

> Referências: `docs/AUDITORIA_VIABILIDADE_POV.md` v1.0 (decisões aprovadas), `docs/fase0/ARCHITECTURE.md`, `docs/fase0/DATA_CONTRACTS.md`, `docs/fase0/PRODUCT_REQUIREMENTS.md` (FR-001–FR-004), `docs/fase0/ACCEPTANCE_AND_ROADMAP.md` (AT-001, AT-002, parte de AT-003/AT-004), `docs/fase0/CLAUDE_CODE_BOOTSTRAP.md` (regra: só F1 nesta entrega, sem IA, sem dashboards com números inventados).

## 0. O que F1 é e não é
**É**: upload de arquivo → identificação de schema/provider → pré-validação → staging → commit idempotente → dataset consultável (metadados e qualidade, não analytics). Dois adapters concretos: **Azure FOCUS 1.0r2** e **Azure Cost Analysis** (export nativo) — ambos entram pelo mesmo pipeline de importação, mas F1 **não compara** os dois (isso é reconciliação, que é F2). SPA com 4 áreas de navegação visíveis, só Data Hub funcional; as outras 3 (Cockpit, Cost Analytics, Investigação/Relatórios) aparecem como "Em desenvolvimento" — nenhum número, nenhum mock.

**Não é**: nenhuma agregação de custo, nenhuma métrica de KPI, nenhuma chamada a IA, nenhuma oportunidade, nenhum forecast. Se qualquer tela mostrar um número de custo agregado, isso é escopo vazado de F2 — não deve acontecer em F1.

## 1. Estrutura de repositório (recorte de `ARCHITECTURE.md` para F1)
```
finops-ai/
  apps/web/src/
    app/                      # shell, roteamento, layout global, filtro de contexto
    design-system/            # tokens de tema (UI_UX_SPEC.md), tipografia IBM Plex
    components/                # tabela, cards, modal de commit, badges de severidade
    features/
      data-hub/                # upload, preview, mapping, staging, commit
      shell-placeholders/       # telas "Em desenvolvimento" das 3 áreas não funcionais
  services/api/app/
    api/v1/imports.py          # endpoints de import
    api/v1/datasets.py         # endpoints de dataset/quality
    config/
    db/                        # engine, sessão, migrations (Alembic)
    domains/ingestion/
      adapters/
        focus_1_0r2.py         # adapter concreto Azure FOCUS 1.0r2
        azure_cost_analysis.py # adapter concreto Azure Cost Analysis export
        base.py                # ProviderAdapter: identify/validate/map_financial/capabilities
      sniffing.py               # delimitador, encoding, amostra
      validation.py             # regras por linha/campo, severidade
      staging.py
      commit.py                 # transacional, idempotente por hash+escopo+período
    domains/canonical_financial/
      models.py                 # import_batch, dataset, cost_usage (SQLAlchemy)
    schemas/                    # Pydantic: contratos de request/response
    security/                   # sanitização de CSV, limites de upload, CORS explícito
  services/worker/
    jobs/import_job.py          # processamento assíncrono do parsing/validação/commit
  packages/
    contracts/                  # schemas compartilhados web/api (OpenAPI/JSON Schema)
    fixtures/                   # fixtures sintéticas versionadas (seção 4)
  data/{incoming,staging,warehouse}/   # nunca versionado no git, só estrutura + .gitkeep
  docs/                          # já existente
  tests/{unit,integration,e2e,security,performance}/
  docker-compose.yml             # Postgres local + API + worker
  .env.example                   # sem valores reais
```

**Decisão de arquitetura para F1 (proponho, pendente confirmação)**: `services/worker` existe como processo separado desde já (não como função in-process), mesmo sendo F1 o único consumidor por ora — isso respeita a regra de `ARCHITECTURE.md` ("nunca bloquear requisições com parsing grande") e evita reescrever a fronteira API/worker quando F2/F4 chegarem. Implementação do worker em F1 é deliberadamente simples: uma fila local (tabela `job` + polling, sem Redis/RabbitMQ) — infraestrutura mínima para um workspace único local. Se isso for mais do que você quer para uma PoV, alternativa é FastAPI `BackgroundTasks` in-process; decido pela fila com tabela porque o requisito de performance (decisão 3: 100k linhas/60s) e o requisito de não bloquear request grande pedem um mecanismo de acompanhamento de progresso (`GET /imports/{id}` precisa de estado real, não só "ainda rodando").

## 2. Contratos de API (subconjunto de `ARCHITECTURE.md`, só o que F1 usa)
| Endpoint | Função | Estado/contrato |
|---|---|---|
| `POST /api/v1/imports` | Inicia upload (multipart, limite configurável de tamanho) | Retorna `import_batch.id`, estado `uploaded` |
| `GET /api/v1/imports/{id}` | Status do processamento | `uploaded→detected→validated→staged→committed\|rejected`, inclui `errors[]` por severidade quando houver |
| `POST /api/v1/imports/{id}/commit` | Confirma staging → canônico, transacional | Bloqueia se `scope+period` já existir sem flag explícita de substituição; idempotente por `sha256` |
| `GET /api/v1/datasets` | Lista datasets committed | `provider, period, currency_set, row_count, quality_score` |
| `GET /api/v1/datasets/{id}/quality` | Relatório de qualidade | Contagem de rejeições por severidade/campo, preserva referência ao arquivo bruto |

Toda resposta segue o padrão de proveniência de `ARCHITECTURE.md` onde aplicável: `source_dataset_ids`, `calculation_version` (aqui, `ingestion_version`), `freshness`, `currency`, `warnings`. Nenhum endpoint de analytics, opportunities, scenarios ou assistant existe nesta fase — eles retornam 404, não um placeholder funcional.

## 3. Contrato de dados e o ponto de atenção FOCUS 1.0r2 vs. 1.4
Tabelas desta fase, extraídas sem alteração de `DATA_CONTRACTS.md`:
- `import_batch(id, source_name, original_filename, sha256, uploaded_at, provider, format, schema_version, status, errors)`
- `dataset(id, import_batch_id, kind, period_start, period_end, provider, currency_set, row_count, quality_score, ingestion_version)`
- `cost_usage(id, dataset_id, provider, billing_account, sub_account, resource_id, service, region, charge_category, billing_start, billing_end, usage_start, usage_end, pricing_qty, pricing_unit, currency, billed_cost, effective_cost, list_cost, contracted_cost, raw_ref)`

**Tratamento do conflito de versão (decisão 1 da auditoria)**: `schema_version` em `import_batch`/`dataset` registra a versão **detectada no arquivo real** (ex.: `focus-1.0r2`), nunca assumida. O `adapters/base.py` expõe `capabilities()` com a lista de campos FOCUS 1.4 que o adapter 1.0r2 **não preenche** — esses campos ficam `NULL` com uma flag de proveniência `"not_present_in_source_version"`, nunca inferidos ou zerados silenciosamente. Isso cumpre a decisão "não inventar campos ausentes" e mantém o modelo canônico pronto para quando um adapter 1.4 existir, sem exigir migração de schema quebrada depois.

**Regras de `DATA_CONTRACTS.md` aplicadas literalmente em F1**: `Decimal` para todo valor financeiro (nunca `float`); timestamps ISO-8601 UTC internamente com timezone original preservado em campo separado; moeda sempre ISO 4217; nulos/ausentes/não aplicáveis marcados com códigos distintos (não o mesmo `NULL` para os três casos); `raw_ref` preserva o dado bruto por linha para auditoria.

## 4. Fixtures sintéticas (nenhum dado real de organização)
Todas geradas programaticamente, com nomes de recursos/contas fictícios (`demo-rg-01`, `svc-fake-storage`, `sub-0000-demo`) e rotuladas com um cabeçalho `# DEMO-SYNTHETIC` no próprio arquivo:

| Fixture | Propósito | Liga a |
|---|---|---|
| `focus_clean_baseline.csv` | 2 meses, 3 serviços, 1 moeda (BRL), ~500 linhas | Caminho feliz, AT-001 |
| `focus_malformed.csv` | cabeçalhos errados, nulos em campo obrigatório, tipo inválido em `billed_cost`, linhas duplicadas | AT-002 |
| `focus_overlap_reimport.csv` | mesmo `scope+period` do baseline, reimportado com uma linha levemente diferente | AT-001, AT-004 (detecção, não a soma — isso é F2) |
| `focus_multicurrency.csv` | BRL e USD misturados na mesma série, sem taxa de câmbio | AT-003 (parte de captura: nunca coagir/somar na ingestão) |
| `azure_cost_analysis_equivalent.csv` | Export nativo Azure Cost Analysis do mesmo período do baseline, granularidade diferente (mensal vs. diária) | Prepara F2 (reconciliação), mas valida que o adapter importa corretamente em F1 |
| `focus_perf_100k.csv` (ou `.parquet`) | 100.000 linhas sintéticas geradas por script, sem repetição ingênua (variação real de serviço/valor/data) | Decisão 3 — teste de performance |

Scripts geradores ficam em `packages/fixtures/generators/`, versionados — nenhuma fixture é editada manualmente depois de gerada, para manter reprodutibilidade.

## 5. Testes
| Tipo | Cobertura |
|---|---|
| Unit (`tests/unit`) | sniffing de delimitador/encoding; detecção de versão FOCUS; parsing `Decimal` (rejeita float silencioso); validação ISO 4217; cálculo de `sha256`; regras de severidade de rejeição por linha/campo |
| Property-based (`tests/unit`, Hypothesis ou similar) | reimportar o mesmo hash N vezes nunca duplica linhas nem altera `row_count`; todo `scope+period` já existente é sempre detectado antes do commit |
| Integração (`tests/integration`) | fluxo completo `uploaded→detected→validated→staged→committed` contra Postgres real (testcontainer); caminho `rejected` preserva arquivo original e não altera base já aprovada; commit é atômico (falha no meio não deixa estado parcial) |
| Performance (`tests/performance`) | `focus_perf_100k` importa e comita em ≤ 60s na máquina de referência (a definir — ver seção 6); mede e registra o tempo real mesmo se passar, para série histórica de regressão |
| Segurança (`tests/security`) | payloads de fórmula CSV (`=`, `+`, `-`, `@` no início de campo) neutralizados em qualquer exportação/preview; scanner de segredo nos logs e no `.env.example`; limite de tamanho de upload respeitado; CORS explícito testado |
| E2E (`tests/e2e`, Playwright) | upload→preview→mapping→modal de commit (caminho feliz); upload malformado→relatório de rejeição visível com severidade; as 3 áreas não funcionais mostram "Em desenvolvimento", nunca dado fictício |

## 6. Ponto aberto antes de codificar: metodologia de performance (decisão 3)
A decisão 3 já fixa a meta (100k registros / 60s) mas deixa 3 variáveis em aberto que preciso confirmar com você antes de escrever o teste, porque definem o que "passar" significa:
- **Máquina de referência**: proponho especificar como container de 2 vCPU / 4 GB RAM (perfil comum de ambiente local de desenvolvimento) e registrar isso no próprio teste, para que o número não vire um mito sem contexto.
- **Formato do arquivo**: CSV puro (pior caso de parsing) ou Parquet (melhor caso)? Proponho medir os dois e reportar ambos, já que o `DATA_CONTRACTS.md` aceita ambos os formatos.
- **O que conta como "importação"**: só parsing+staging, ou staging+commit completo (incluindo gravação transacional no Postgres)? Proponho medir o ciclo completo upload→commit, porque é o que o usuário final experimenta — mas isso é mais exigente que medir só o parser.

## 7. Critérios de aceite para aprovar F1 e seguir para F2
- AT-001 (reimportação idempotente) — 100% nos casos de teste.
- AT-002 (rejeição granular, preserva origem, não altera base aprovada) — 100%.
- AT-004, parte de detecção (overlap de `scope+period` sempre detectado) — 100%; a parte de "não dobrar o total faturado" fica para F2, que é quem agrega.
- AT-003, parte de captura (nunca somar/coagir moeda na ingestão) — 100%; o bloqueio na UI de agregação é F2.
- Performance: resultado medido e registrado conforme seção 6, mesmo que a meta de 60s não seja batida de primeira — reporto o número real, não arredondo para "passou".
- 0 achados críticos de segurança (CSV injection, segredo exposto, CORS aberto).
- Nenhuma tela de F1 mostra número de custo agregado, KPI ou qualquer dado fictício fora do que está explicitamente rotulado como DEMO.
- Screenshots funcionais do fluxo de upload→commit e do fluxo de rejeição, resultado real dos testes automatizados (não resumo otimista), lacunas residuais documentadas — conforme o critério operacional do `ACCEPTANCE_AND_ROADMAP.md` ("não contar um mock como engine em produção").

## 8. O que fica explicitamente fora de F1 (para não vazar escopo)
Nenhuma reconciliação FOCUS×Azure Cost Analysis (F2); nenhuma anomalia/variação (F2); nenhum KPI de Cockpit com número real (F2); nenhuma chamada à Claude API, nem com IA desligada por padrão — a infraestrutura de consentimento/teto de custo (decisão 6) só é construída quando F4 começar, não antes, para não gastar esforço de engenharia em algo que só é testável depois que F2 existir.

## Antes de codificar, preciso que você confirme
1. A decisão de arquitetura do worker (fila com tabela própria vs. `BackgroundTasks` in-process) — seção 1.
2. As 3 variáveis de metodologia de performance — seção 6.
3. Se o corte de escopo de F1 (seção 0 e 8) está exatamente como você espera, em particular que **nenhuma** reconciliação ou número de custo apareça ainda nesta fase.

Com isso confirmado, a próxima entrega (conforme `CLAUDE_CODE_BOOTSTRAP.md`) é: árvore de repositório materializada, migrations Alembic, contratos de endpoint em OpenAPI, SPA shell com Data Hub funcional, fixture baseline e teste de import end-to-end.
