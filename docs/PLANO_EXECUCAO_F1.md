# Plano de execução — F1: Fundação e Importação
Versão 2.0 (revisada) | 14/10/2026 | Status: PROPOSTO PARA APROVAÇÃO — nenhum código escrito.

> Referências: `docs/AUDITORIA_VIABILIDADE_POV.md` v1.0, `docs/fase0/ARCHITECTURE.md`, `docs/fase0/DATA_CONTRACTS.md`, `docs/fase0/PRODUCT_REQUIREMENTS.md`, `docs/fase0/ACCEPTANCE_AND_ROADMAP.md`, `docs/fase0/CLAUDE_CODE_BOOTSTRAP.md`. Esta v2.0 incorpora 7 critérios adicionais exigidos pelo usuário em 14/10/2026, mantendo a arquitetura já aprovada conceitualmente (React + FastAPI + PostgreSQL, worker separado com fila persistida em tabela, dois adapters de importação, SPA mínima).

## 0. Decisões já fechadas, mantidas sem alteração
- **Arquitetura do worker**: processo separado, fila persistida em tabela (não in-process, não broker externo) — aprovado na rodada anterior, resolvido agora de forma mais detalhada na seção 7.
- **FOCUS**: primeiro adapter concreto Azure FOCUS 1.0r2; modelo canônico versionado preservando referência futura a FOCUS 1.4; nunca inventar campo ausente.
- **Sem IA em F1**: nenhuma chamada à Claude API, nenhuma infraestrutura de consentimento/teto de custo construída nesta fase — isso é F4.
- **SPA mínima**: 4 áreas de navegação, só Data Hub funcional em F1; Cockpit, Cost Analytics, Investigação/Relatórios em "Em desenvolvimento".
- **Escopo de F1**: upload → identificação → pré-validação → staging → commit idempotente → dataset consultável. Nenhuma agregação, nenhum KPI, nenhuma reconciliação (isso é F2).

## 1. Rastreamento: o que já estava nos documentos originais vs. o que é proposta nova desta revisão
O usuário pediu esta distinção explicitamente. Nenhum documento de `docs/fase0/` foi alterado — as células "Novo" abaixo são propostas minhas para preencher lacunas reais, sujeitas à sua aprovação.

| Critério pedido | Status | Onde já estava / o que é novo |
|---|---|---|
| 1. Separar dedup de hash de identificação de sobreposição financeira | **Novo (refinamento de ambiguidade original)** | `DATA_CONTRACTS.md` junta os dois num só passo: *"reimportação idempotente por hash+escopo+período"*. O documento não diz o que fazer quando o hash é diferente mas o escopo+período se repete (caso mais comum e mais perigoso: arquivo diferente, mesmo período). Proponho separar os dois mecanismos — seção 4. |
| 2. Preservar arquivo bruto, proveniência por linha, versão de esquema, mapeamento de campos | **Majoritariamente já coberto** | `raw_ref` por linha e `schema_version` já estão em `DATA_CONTRACTS.md`; "nunca perder dados brutos; armazenar checksum e procedência" já está em `ARCHITECTURE.md`. **Novo**: persistência do *mapeamento de campos* como registro próprio — `UI_UX_SPEC.md` pede "mapping editável" na tela, mas nenhum documento define onde/como isso é armazenado para auditoria. Proponho a tabela `import_field_mapping` — seção 5. |
| 3. Decimal; impedir agregação indevida de moeda/tipo de custo/granularidade | **Majoritariamente já coberto** | Decimal e não-soma-cross-currency já estão em `DATA_CONTRACTS.md`; "não misturar custos faturados, efetivos e preço de lista... reconciliar por dimensão" já está em `ARCHITECTURE.md`. **Novo**: nenhum documento tem um campo explícito de granularidade (diária/mensal) no esquema, embora `ARCHITECTURE.md` cite "distinguir granularidade diária/mensal" como padrão de qualidade. Proponho computar e persistir `granularity` por dataset — seção 6. |
| 4. Transacional, idempotente, recuperação de falha, estados persistentes de job | **Parcialmente coberto** | Os estados `uploaded→detected→validated→staged→committed\|rejected` já estão em `ARCHITECTURE.md`; commit transacional/idempotente já está em `ACCEPTANCE_AND_ROADMAP.md` (AT-001). **Novo**: nenhum documento descreve o que acontece se o worker morrer com um job em `running` (job órfão) — proponho heartbeat + reaper — seção 7. |
| 5. Segurança local: localhost, limites de upload, validação de formato, proteção a manipulação de caminho | **Parcialmente coberto** | "Endpoint API localhost por padrão, CORS explícito, uploads limitados" já está em `AGENTS_SECURITY.md`. **Novo**: nenhum documento menciona proteção contra path traversal/manipulação de nome de arquivo — proponho isso na seção 8, é uma lacuna de segurança real, não uma preferência estética. |
| 6. Canônico independente do Azure, adapters por provedor | **Já coberto** | `ProviderAdapter` com `identify/validate/map_financial/map_inventory/map_metrics/capabilities` já está em `ARCHITECTURE.md`, sem alteração — mantido. |
| 7. Preservar decisões FOCUS/SPA/sem IA em F1 | **Já coberto** | Decisões da rodada anterior, repetidas na seção 0 para não se perderem. |

## 2. Estrutura de repositório (atualizada)
```
finops-ai/
  apps/web/src/
    app/ design-system/ components/
    features/
      data-hub/
        upload/            # dropzone, validação client-side de extensão/tamanho antes do POST
        mapping/            # UI de mapeamento editável + preview de confiança
        staging-review/     # lista de erros por severidade
        commit-modal/
      shell-placeholders/
  services/api/app/
    api/v1/{imports,datasets}.py
    db/ (migrations Alembic)
    domains/ingestion/
      adapters/{base.py, focus_1_0r2.py, azure_cost_analysis.py}
      sniffing.py validation.py staging.py commit.py
      dedup.py              # NOVO — dedup por hash, isolado
      overlap.py            # NOVO — detecção de sobreposição financeira, isolado de dedup.py
      field_mapping.py      # NOVO — persistência/edição de mapeamento
    domains/canonical_financial/models.py
    schemas/
    security/
      upload_guard.py       # NOVO — limites, validação de MIME/magic-bytes, sanitização de nome
      path_safety.py        # NOVO — normalização e verificação de contenção de todo path de arquivo
  services/worker/
    jobs/import_job.py
    reaper.py                # NOVO — detecta jobs órfãos (heartbeat expirado) e os requeue ou marca failed
  packages/{contracts,fixtures}/
  data/{incoming,staging,warehouse}/   # arquivos brutos guardados por UUID, nunca pelo nome original
  tests/{unit,integration,e2e,security,performance,failure}/   # NOVO: failure/ para cenários de falha dedicados
  docker-compose.yml .env.example
```

## 3. Esquema de banco (revisado)
Tabelas de `DATA_CONTRACTS.md`, sem alteração de forma:
- `import_batch(id, source_name, original_filename, sha256, uploaded_at, provider, format, schema_version, status, errors)`
- `dataset(id, import_batch_id, kind, period_start, period_end, provider, currency_set, row_count, quality_score, ingestion_version)`
- `cost_usage(id, dataset_id, provider, billing_account, sub_account, resource_id, service, region, charge_category, billing_start, billing_end, usage_start, usage_end, pricing_qty, pricing_unit, currency, billed_cost, effective_cost, list_cost, contracted_cost, raw_ref)`

Tabelas **novas**, propostas para preencher as lacunas da seção 1:
- `import_job(id, import_batch_id, state, attempt_count, heartbeat_at, started_at, finished_at, error_detail, checkpoint_row_offset)` — `state ∈ {queued, running, succeeded, failed, orphaned_requeued}`. `checkpoint_row_offset` permite retomar parsing de arquivos grandes sem reprocessar do zero após falha (seção 7).
- `import_field_mapping(id, import_batch_id, source_field, canonical_field, transform_applied, confidence, is_manual_override, created_at)` — cada decisão de mapeamento (automática ou editada manualmente na UI) é um registro auditável, nunca sobrescrito, só versionado (nova linha com `created_at` mais recente).
- `dataset_overlap_flag(id, dataset_id, overlapping_dataset_id, scope_key, period_start, period_end, detected_at, resolution, resolved_by)` — registra toda sobreposição de **escopo+período financeiro** detectada entre datasets com hashes diferentes; `resolution ∈ {pending, replace_approved, kept_both_as_correction, rejected}`. Nunca é resolvido automaticamente (seção 4).

Campo **novo** em `dataset`: `granularity` (`daily|monthly|mixed|unknown`), calculado a partir da distribuição de `billing_start`/`billing_end` das linhas do dataset no momento do commit (seção 6).

## 4. Deduplicação de arquivo vs. sobreposição financeira (critério 1 — separação explícita)
Dois mecanismos independentes, nunca fundidos no código nem na UI:

**(a) Deduplicação por hash** — pergunta: "este exato arquivo já foi importado?". `sha256` do arquivo bruto. Se já existe um `import_batch` com o mesmo hash e status `committed`: a nova tentativa é um no-op idempotente — retorna o `import_batch` existente, não cria nada novo, não é erro (AT-001). Isso cobre reenvio acidental do mesmo arquivo.

**(b) Detecção de sobreposição financeira** — pergunta: "este arquivo (com hash diferente) descreve custo que já está coberto por outro dataset committed, no mesmo provider+scope+period+cost_basis?". Roda **depois** da checagem de hash, só quando o hash é novo. Se detectar sobreposição, cria um `dataset_overlap_flag` com `resolution=pending` e o commit **bloqueia** até decisão explícita (nunca substitui nem ignora silenciosamente): o usuário escolhe `replace_approved` (o novo dataset substitui o anterior, versionado) ou `kept_both_as_correction` (ambos coexistem, com a flag registrada para que F2 nunca some os dois sem saber do conflito). Isso cobre o caso real mais perigoso: reexportação do mesmo mês com uma linha corrigida, ou dois exports manuais do mesmo período por pessoas diferentes.

A UI de commit mostra esses dois casos com linguagem e ação diferentes — nunca a mesma mensagem genérica de "duplicado".

## 5. Proveniência (critério 2)
- **Arquivo bruto**: armazenado em `data/incoming/{import_batch_id}/{sha256}.<ext original validada>` — nunca pelo nome original fornecido pelo usuário (ver seção 8, path traversal). Nunca apagado automaticamente, mesmo em datasets rejeitados.
- **Proveniência por linha**: `cost_usage.raw_ref` aponta para a posição/linha exata no arquivo bruto (ex.: número de linha + hash do arquivo), permitindo auditoria célula a célula sem reprocessar.
- **Versão de esquema**: `import_batch.schema_version` e `dataset.ingestion_version` registram exatamente o que o adapter detectou (`focus-1.0r2`), nunca o que foi assumido.
- **Mapeamento de campos**: cada linha de `import_field_mapping` é imutável depois de criada; uma correção manual gera novo registro, preservando o histórico de como o mapeamento evoluiu durante a revisão humana.

## 6. Tipos monetários e prevenção de agregação indevida (critério 3)
- Todo campo de valor financeiro é `Decimal` em todas as camadas (Python/Pydantic/SQLAlchemy `Numeric`, nunca `float`/`double` em nenhum ponto do pipeline, incluindo serialização JSON — usar string decimal, não número de ponto flutuante, nas respostas de API).
- `currency` é sempre ISO 4217; qualquer tentativa de persistir `cost_usage` sem moeda válida é rejeitada na validação (severidade `error`, não `warning`).
- `charge_category` (billed/effective/list/contracted) nunca é normalizado para um único campo "custo" — os 4 campos existem lado a lado em `cost_usage`, forçando qualquer consumidor futuro (F2) a escolher explicitamente qual cost basis está usando.
- `granularity` (novo campo, seção 3) é calculado e persistido no commit — F2 fica proibido de comparar/somar datasets com granularidades diferentes sem tratamento explícito de conversão, porque a informação já está disponível para essa checagem, não precisa ser redescoberta.
- F1 **não agrega nada** — esta seção garante que os dados cheguem a F2 com metadados suficientes para que a agregação indevida seja tecnicamente difícil de acontecer por acidente, não que F1 já previna isso em tempo de agregação (que não existe ainda).

## 7. Transacionalidade, idempotência, recuperação de falha, estados de job (critério 4)
- **Commit transacional**: toda a gravação de `cost_usage` de um `import_batch` ocorre em uma única transação de banco; falha parcial faz rollback completo — nunca um dataset com metade das linhas.
- **Idempotência**: já descrita na seção 4(a) — commit por hash nunca duplica.
- **Estados de job** (`import_job.state`): `queued → running → succeeded|failed`. Transições são persistidas, não só em memória — se a API reiniciar, `GET /imports/{id}` continua respondendo corretamente a partir do banco.
- **Recuperação de falha (novo, lacuna real dos documentos originais)**:
  - Worker grava `heartbeat_at` periodicamente enquanto processa.
  - `reaper.py` roda a cada N segundos: qualquer job em `running` com `heartbeat_at` mais antigo que um limite configurável é marcado `orphaned_requeued`, reposto na fila como `queued` com `attempt_count+1`, até um máximo de tentativas (depois disso, `failed` com erro explícito, nunca uma retentativa infinita silenciosa).
  - `checkpoint_row_offset` permite a um job retomado continuar a validação de onde parou em arquivos grandes, em vez de reprocessar do zero — relevante para o teste de performance de 100k linhas (decisão de performance ainda pendente de confirmação, seção 11).
  - Falha de conexão com o banco durante commit: a transação não efetivada não deixa rastro; o job volta para `queued` e tenta de novo.

## 8. Segurança local (critério 5)
- **Rede**: API faz bind em `127.0.0.1` por padrão (não `0.0.0.0`); CORS explícito só para a origem do Vite dev server; nenhuma configuração de produção exposta nesta fase — já previsto em `AGENTS_SECURITY.md`, confirmado como requisito de F1.
- **Limite de upload**: tamanho máximo configurável (ex.: 200MB por arquivo na PoV, valor a confirmar), rejeitado antes de gravar em disco (streaming com corte, não leitura completa em memória primeiro).
- **Validação de formato**: extensão declarada **mais** verificação de magic bytes/MIME real do conteúdo (não confiar só na extensão) — um `.csv` que na verdade é um executável é rejeitado na validação, não só "tratado como CSV e falha depois".
- **Proteção contra manipulação de caminho (novo, lacuna real)**: `original_filename` do usuário é armazenado só como metadado de exibição — **nunca** usado para compor um caminho de arquivo no disco. Todo path de gravação é construído a partir de IDs internos gerados pelo sistema (`import_batch.id`, `sha256`), passando por `path_safety.py`, que resolve o caminho final e verifica que ele está contido dentro do diretório base permitido antes de qualquer `open()`/`write()`. Isso neutraliza tentativas de nome de arquivo como `../../etc/passwd` ou caminhos absolutos disfarçados de nome de arquivo.
- **Sanitização de CSV** (já no plano anterior): payloads de fórmula (`=`, `+`, `-`, `@`) neutralizados em qualquer exportação/preview.

## 9. Independência arquitetural do Azure (critério 6 — já coberto, mantido)
`ProviderAdapter` com `identify/validate/map_financial/map_inventory/map_metrics/capabilities()`, conforme `ARCHITECTURE.md`. F1 implementa dois adapters concretos (FOCUS 1.0r2, Azure Cost Analysis), ambos atrás da mesma interface; nenhuma lógica de domínio (`ingestion`, `canonical_financial`) referencia "Azure" diretamente — só os adapters conhecem o provider. Isso é o que permite, no futuro, um adapter ler de um ambiente que já rode FinOps Hubs como fonte alternativa, sem acoplamento.

## 10. Fixtures sintéticas (atualizadas, nenhum dado real)
Mantidas da v1.0 (`focus_clean_baseline`, `focus_malformed`, `focus_overlap_reimport`, `focus_multicurrency`, `azure_cost_analysis_equivalent`, `focus_perf_100k`), com 3 novas para os critérios desta revisão:

| Fixture nova | Propósito |
|---|---|
| `focus_same_period_different_hash.csv` | Mesmo scope+period do baseline, hash diferente (não é o mesmo arquivo) — testa especificamente a seção 4(b), distinto do teste de dedup por hash |
| `malicious_filename_traversal` | Upload com nome de arquivo contendo `../`, caminho absoluto, ou caracteres de controle — testa `path_safety.py` |
| `focus_mixed_granularity.csv` | Linhas diárias e mensais no mesmo dataset — testa o cálculo de `granularity=mixed` |

## 11. Testes automatizados (atualizados)
| Tipo | Cobertura nova/revisada |
|---|---|
| Unit | `dedup.py` e `overlap.py` testados **separadamente**, nunca no mesmo teste (reforça a separação do critério 1); cálculo de `granularity`; `path_safety.py` rejeita todo payload de traversal da fixture dedicada; validação de magic bytes vs. extensão divergente |
| Integração | fluxo completo incluindo `import_field_mapping` persistido e consultável após commit; `dataset_overlap_flag` criado e bloqueando commit até resolução explícita; reaper requeue de job órfão simulado (matar o worker no meio do processamento e verificar recuperação) |
| Falha (`tests/failure`, novo) | ver seção 12 — cada cenário de falha tem um teste correspondente, não é só documentação |
| Performance | inalterado da v1.0, pendente de confirmação de metodologia (seção 13) |
| Segurança | inalterado + path traversal explícito |
| E2E | inalterado + fluxo de resolução de `dataset_overlap_flag` na UI |

## 12. Cenários de falha (novo, pedido explicitamente)
| Cenário | Comportamento esperado |
|---|---|
| Worker morre no meio do parsing de um arquivo grande | Job fica `running` com heartbeat parado; reaper detecta, requeue com checkpoint; retomada não duplica linhas já processadas |
| Upload do mesmo arquivo duas vezes em paralelo (dois cliques) | Segundo request detecta hash em processamento (ou já committed) e retorna o `import_batch` existente, não cria um segundo job concorrente |
| Conexão com Postgres cai durante commit | Transação não efetivada; job volta para `queued`; novo attempt não deixa estado parcial |
| Disco cheio durante staging | Upload falha de forma explícita (`failed`, `error_detail` claro); nenhum arquivo parcial é tratado como válido; espaço já gravado é limpo |
| Nome de arquivo malicioso (path traversal) | Rejeitado em `path_safety.py` antes de qualquer gravação; registrado como tentativa de severidade `error` na resposta, sem detalhe interno de path exposto ao cliente |
| Arquivo corrompido no meio do stream (CSV trunca a meio de uma linha) | Linha incompleta é rejeitada com severidade `error` e offset exato; linhas anteriores válidas não são descartadas só porque o arquivo terminou mal — mas o commit inteiro só ocorre se a taxa de rejeição estiver dentro de um limiar aceitável (a definir) |
| Dois commits concorrentes para o mesmo `scope+period` | Lock otimista por `scope_key`; o segundo commit detecta o primeiro já em andamento e aguarda ou falha com mensagem clara, nunca corrida de gravação simultânea |

## 13. Critérios de aceite objetivos (consolidados desta revisão)
Mantidos da v1.0 (AT-001 a AT-004 parciais, performance, 0 achados críticos de segurança, nenhuma tela com número agregado), mais:
- 100% dos cenários da seção 12 cobertos por teste automatizado e com comportamento conforme a tabela — nenhum é "documentado mas não testado".
- Deduplicação por hash e detecção de sobreposição financeira nunca compartilham código nem mensagem de usuário — auditável lendo o diff do PR (critério de revisão de código, não só de teste).
- 100% das linhas malformadas de `malicious_filename_traversal` e `focus_mixed_granularity` tratadas conforme especificado nesta seção.
- `import_field_mapping` consultável via API para qualquer `import_batch_id` committed, com histórico completo de edições manuais.

## 14. Pontos abertos para confirmação antes de codificar
Carregado da v1.0 (ainda não resolvido):
1. **Metodologia de performance** (decisão 3 da auditoria): máquina de referência (proponho 2 vCPU/4GB), formato (medir CSV e Parquet separadamente), e escopo da medição (upload→commit completo, proposta mantida).

Novo desta revisão:
2. **Limite máximo de tentativas do reaper** antes de marcar um job `failed` definitivamente (proponho 3) — e **intervalo de heartbeat/timeout de órfão** (proponho heartbeat a cada 5s, timeout de órfão em 30s) — números de partida, ajustáveis.
3. **Limiar de taxa de rejeição** que ainda permite commit parcial de um arquivo com algumas linhas malformadas vs. rejeitar o arquivo inteiro (cenário de "arquivo corrompido no meio do stream", seção 12) — proponho: rejeitar o commit inteiro se >5% das linhas forem inválidas, permitir commit com quarentena das linhas inválidas abaixo disso; é uma escolha de produto, não só técnica.
4. **Tamanho máximo de upload** (proponho 200MB para a PoV) — confirmar se é suficiente para os casos de uso reais que você tem em mente.

Com esses 4 pontos confirmados, a próxima entrega é código: árvore materializada, migrations Alembic (incluindo as 3 tabelas novas), contratos OpenAPI, SPA Data Hub funcional, fixtures geradas, e os testes das seções 10–12.
