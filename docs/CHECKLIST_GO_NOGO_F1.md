# Checklist GO/NO-GO — início da codificação de F1
Versão 1.0 | 14/10/2026 | Status: PARA REVISÃO DO USUÁRIO — a autorização para implementar é um ato separado e explícito, não decorre deste checklist sozinho.

> Referência: `docs/PLANO_EXECUCAO_F1.md` v3.0. Este documento não substitui o plano — é o filtro final antes de abrir o primeiro arquivo de código.

## Como usar
Cada item é **GO** (confirmado, sem ambiguidade restante), **NO-GO** (bloqueia o início até resolver) ou **ACEITO COM RISCO** (prossigo, mas o risco fica registrado e visível, não escondido). Marco minha avaliação; a decisão de autorizar é sua.

## 1. Escopo e sequenciamento
- [GO] F1 limitado a upload→identificação→validação→staging→commit→dataset consultável; nenhuma agregação, KPI, reconciliação, forecast, oportunidade ou IA.
- [GO] Dois adapters concretos: Azure FOCUS 1.0r2 e Azure Cost Analysis; modelo canônico versionado preserva referência futura a FOCUS 1.4 sem inventar campo.
- [GO] SPA com 4 áreas de navegação visíveis; só Data Hub funcional; demais em "Em desenvolvimento", nunca com dado simulado.
- [GO] Nenhuma chamada à Claude API nem infraestrutura de consentimento/custo nesta fase.

## 2. Esquema de dados e proveniência
- [GO] Tabelas de `DATA_CONTRACTS.md` (`import_batch`, `dataset`, `cost_usage`) usadas sem alteração de forma.
- [GO] Tabelas novas definidas com proposta de schema completo: `import_job`, `import_field_mapping`, `dataset_overlap_flag`, `scope_lock`, `import_row_rejection`.
- [GO] Arquivo bruto, proveniência por linha (`raw_ref`), versão de esquema e mapeamento de campos todos persistidos e auditáveis.
- [ACEITO COM RISCO] As 5 tabelas novas ainda não passaram por revisão de modelagem formal (índices, chaves estrangeiras, constraints de unicidade) — isso é trabalho normal de implementação (migrations Alembic), não um risco de produto, mas registro que o desenho de schema desta versão é lógico, não físico.

## 3. Deduplicação, sobreposição e concorrência
- [GO] Deduplicação por hash e detecção de sobreposição financeira são mecanismos, tabelas e mensagens de UI explicitamente separados (critério 1 do usuário).
- [GO] `scope_lock` com lease e expiração previne commits concorrentes no mesmo `provider+scope+período`.
- [GO] Nenhuma resolução de sobreposição é automática — sempre requer decisão humana explícita (`dataset_overlap_flag.resolution`).

## 4. Tipos monetários e metadados de agregação
- [GO] `Decimal` em todas as camadas, incluindo serialização de API; nunca `float` para valor financeiro.
- [GO] Moeda ISO 4217 obrigatória; `charge_category` (billed/effective/list/contracted) nunca colapsado num único campo.
- [GO] Campo `granularity` novo, calculado no commit, disponível para F2 usar — F1 não agrega nada por conta própria.

## 5. Transacionalidade, falha e recuperação
- [GO] Commit atômico por `import_batch`; idempotência por hash; estados de job persistidos em banco, não em memória.
- [GO] Heartbeat 5s / timeout de órfão 30s / máximo 3 tentativas (incluindo a primeira) — confirmados pelo usuário.
- [GO] Classificação explícita de falha transitória (elegível a retry via reaper) vs. permanente (vai direto a `failed`, sem retry) — resolve a exigência "erros permanentes não devem gerar tentativas automáticas".
- [GO] Reprocessamento manual via endpoint dedicado (`POST /imports/{id}/retry`), distinto e auditável, separado do requeue automático.

## 6. Rejeição e quarentena
- [GO] Taxonomia de severidade (`info`/`warning`/`error`) definida; qualquer `error` bloqueia o commit do batch inteiro — sem limiar percentual, conforme exigido.
- [GO] Fluxo de aprovação humana para commit parcial **não será construído em F1** — decisão explícita, não lacuna. Revisitar em F2/F3 se necessário.
- [ACEITO COM RISCO] Bloqueio total por qualquer linha `error` é estrito (1 linha ruim em 100k bloqueia tudo). É a opção mais segura e a que o usuário pediu explicitamente; o risco de usabilidade (reimportações frequentes por erros pontuais) é conhecido e aceito como trade-off consciente, não como surpresa a ser descoberta depois.

## 7. Segurança local
- [GO] Bind em `127.0.0.1`, CORS explícito, upload limitado a 200MB, streaming (nunca carga integral em memória).
- [GO] Validação de formato por magic bytes + lista fechada de extensões (`.csv`, `.parquet`, `.csv.gz`).
- [GO] Proteção contra path traversal: nome original do usuário nunca compõe caminho em disco; toda escrita passa por `path_safety.py`.
- [GO] Limite de descompactação contra zip bomb para entradas comprimidas.
- [GO] Redação de log: nenhum valor financeiro em texto plano em nenhum log — a ser verificado por scanner dedicado nos testes.

## 8. Independência arquitetural
- [GO] `ProviderAdapter` isola toda lógica específica de provider; nenhum domínio de `ingestion`/`canonical_financial` referencia "Azure" diretamente.
- [GO] Nenhuma dependência de Data Factory, Data Explorer ou Power BI do FinOps Hubs; Postgres + Parquet/DuckDB locais.

## 9. Fixtures e dados
- [GO] Todas as fixtures sintéticas, com rótulo `# DEMO-SYNTHETIC`, nomes fictícios, geradas por script versionado — nenhum dado real de organização.
- [GO] 9 fixtures cobrindo: caminho feliz, malformado, overlap por reimportação idêntica, overlap por hash diferente, multi-moeda, granularidade mista, performance (100k), nome de arquivo malicioso, equivalente Azure Cost Analysis.

## 10. Performance
- [GO] Meta (100k linhas/60s), protocolo (5 medições, P95, aquecimento descartado), escopo de medição (exclui upload/init/render) e telemetria (CPU/RAM/disco/SO/versões) todos definidos.
- [ACEITO COM RISCO] A "máquina de referência" será o ambiente real de execução dos testes (não um hardware fixado a priori) — isso é mais honesto que prometer um número de hardware hipotético, mas significa que o resultado de 60s pode variar entre ambientes de CI/dev/produção local; o relatório de teste sempre inclui a telemetria para dar contexto a qualquer leitura futura do número.

## 11. Testes
- [GO] Cobertura planejada em 6 categorias (unit, integração, falha, performance, segurança, E2E), com os 9 cenários de falha da seção 12 do plano todos mapeados a teste automatizado específico.
- [GO] Teste dedicado garantindo que `dedup.py` e `overlap.py` nunca compartilham código (requisito de separação, verificável por revisão, não só por execução).

## 12. Documentação e governança
- [GO] Os 9 documentos originais da Fase 0 permanecem inalterados em `docs/fase0/`; toda proposta nova está identificada como tal nas tabelas de rastreamento da auditoria e do plano.
- [GO] Divergência registrada e não corrigida automaticamente: FR-010 (Optimization) é P0 no `PRODUCT_REQUIREMENTS.md` original mas fica fora das 4 áreas funcionais da PoV — decisão consciente do usuário, não omissão.

## Pendências remanescentes (nenhuma bloqueante, mas listadas por transparência)
- Nenhum parâmetro técnico está em aberto nesta versão — todos os 4 da rodada anterior foram resolvidos.
- A única dependência real para começar a codificar é a autorização explícita do usuário, pedida separadamente deste checklist.

## Resultado consolidado
**39 itens GO, 3 ACEITO COM RISCO (riscos conhecidos e já decididos conscientemente, não lacunas escondidas), 0 NO-GO.**

Minha avaliação: não há bloqueador técnico ou de escopo para iniciar a codificação de F1. Os 3 itens "aceito com risco" são escolhas de produto já deliberadas (bloqueio total por erro, máquina de referência variável, modelagem física de schema ainda não revisada) — nenhum deles exige nova decisão sua antes de começar, mas registro para que, se o resultado real incomodar depois, fique claro que foi um trade-off conhecido, não um acidente.

**Aguardando autorização explícita para iniciar a implementação de F1.**
