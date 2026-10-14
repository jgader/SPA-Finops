# Plano de execução — F1: Fundação e Importação
Versão 3.0 (final para aprovação de codificação) | 14/10/2026 | Status: PROPOSTO PARA APROVAÇÃO — nenhum código escrito. Checklist GO/NO-GO em `docs/CHECKLIST_GO_NOGO_F1.md`.

> Referências: `docs/AUDITORIA_VIABILIDADE_POV.md` v1.0, `docs/fase0/ARCHITECTURE.md`, `docs/fase0/DATA_CONTRACTS.md`, `docs/fase0/PRODUCT_REQUIREMENTS.md`, `docs/fase0/ACCEPTANCE_AND_ROADMAP.md`, `docs/fase0/CLAUDE_CODE_BOOTSTRAP.md`. v2.0 incorporou 7 critérios adicionais. Esta v3.0 fecha os 4 parâmetros que ficaram abertos na v2.0 (seção 14 antiga) com os valores definidos pelo usuário em 14/10/2026, resolve os conflitos técnicos que essa definição gerou com a v2.0, e adiciona o checklist final de GO/NO-GO.

## 0. Decisões já fechadas, mantidas sem alteração
- **Arquitetura do worker**: processo separado, fila persistida em tabela (não in-process, não broker externo) — aprovado na rodada anterior, resolvido agora de forma mais detalhada na seção 7.
- **FOCUS**: primeiro adapter concreto Azure FOCUS 1.0r2; modelo canônico versionado preservando referência futura a FOCUS 1.4; nunca inventar campo ausente.
- **Sem IA em F1**: nenhuma chamada à Claude API, nenhuma infraestrutura de consentimento/teto de custo construída nesta fase — isso é F4.
- **SPA mínima**: 4 áreas de navegação, só Data Hub funcional em F1; Cockpit, Cost Analytics, Investigação/Relatórios em "Em desenvolvimento".
- **Escopo de F1**: upload → identificação → pré-validação → staging → commit idempotente → dataset consultável. Nenhuma agregação, nenhum KPI, nenhuma reconciliação (isso é F2).

## 0-bis. Conflitos técnicos entre a v2.0 e os parâmetros definidos agora
Dois pontos da v2.0 precisaram ser revertidos ou reformulados — registro aqui, não escondido dentro das seções, porque são mudanças de comportamento, não só de número:

**Conflito A — limiar de 5% de rejeição (revertido)**. A v2.0 propunha: "rejeitar o commit inteiro se >5% das linhas forem inválidas, permitir commit com quarentena abaixo disso". A decisão 3 do usuário rejeita explicitamente essa ideia ("não aceitar uma taxa fixa de 5% como autorização automática") e proíbe commit parcial automático. **Resolução**: removido qualquer limiar percentual. Novo comportamento (seção 7 revisada): qualquer linha de severidade `error` bloqueia o commit do `import_batch` inteiro — all-or-nothing. Severidade `warning` não bloqueia. F1 **não implementa** um fluxo de aprovação humana para commit parcial (construir e testar essa aprovação com segurança é escopo novo, não coberto por nenhum documento da Fase 0) — isso cai na cláusula de segurança que o próprio usuário definiu: *"se não houver suporte seguro a essa aprovação na F1, bloquear o commit até correção ou nova importação válida"*. Decisão explícita: **não construir** o fluxo de aprovação em F1; todo `import_batch` com qualquer linha `error` fica em `rejected`, ponto final, até reimportação corrigida.

**Conflito B — escopo da medição de performance (ajustado, não revertido)**. A v2.0 propunha medir "upload→commit completo". A decisão 1 do usuário exclui explicitamente "transferência de upload, inicialização e renderização" da medição. **Resolução**: o cronômetro começa quando o arquivo já staged é entregue ao pipeline de validação/normalização/persistência (pula transporte de rede e boot de processo) e termina no commit efetivado — ver seção 13.

Nenhum outro parâmetro definido pelo usuário conflita com a v2.0; os demais (heartbeat 5s, timeout 30s, 3 tentativas, 200MB) já eram exatamente os valores propostos — confirmados sem mudança de desenho.

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

Duas tabelas adicionais, propostas nesta v3.0 para atender às decisões de posse/lease e de quarentena estruturada (seções 7 e 7-bis):
- `scope_lock(scope_key, held_by_job_id, acquired_at, expires_at)` — lease exclusivo por `provider+scope+period`, distinto do controle de tentativas do próprio `import_job`: impede que dois jobs de **batches diferentes** tentem commitar o mesmo escopo+período ao mesmo tempo (cenário de concorrência da seção 12), enquanto `import_job.attempt_count`/`heartbeat_at` controlam retomada do **mesmo** job.
- `import_row_rejection(id, import_batch_id, row_offset, raw_excerpt_ref, severity, reason_code, field, created_at)` — substitui o campo genérico `errors` (JSON) de `import_batch` por um registro estruturado, consultável por severidade/campo/motivo; nunca contém o valor financeiro bruto da linha, só a referência (`raw_excerpt_ref`) para o arquivo original armazenado (ver seção 8, redação de logs).

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

## 7. Transacionalidade, idempotência, recuperação de falha, estados de job (critério 4 — parâmetros finais)
- **Commit transacional**: toda a gravação de `cost_usage` de um `import_batch` ocorre em uma única transação de banco; falha parcial faz rollback completo — nunca um dataset com metade das linhas.
- **Idempotência**: já descrita na seção 4(a) — commit por hash nunca duplica.
- **Estados de job** (`import_job.state`): `queued → running → succeeded|failed`. Transições são persistidas, não só em memória — se a API reiniciar, `GET /imports/{id}` continua respondendo corretamente a partir do banco.
- **Classificação de falha — transitória vs. permanente (novo, exigido pelo usuário: "erros permanentes não devem gerar tentativas automáticas")**: toda falha capturada pelo worker é classificada antes de decidir o próximo estado.
  - **Transitória** (conexão de banco perdida, timeout de I/O, worker morto/heartbeat expirado): elegível a retry automático via reaper, até o limite de tentativas.
  - **Permanente** (arquivo estruturalmente inválido, schema não reconhecido por nenhum adapter, violação de regra financeira crítica — seção 7-bis): vai direto para `failed`, **sem** passar pelo reaper, sem consumir tentativa — reprocessar só acontece via reimportação corrigida ou reprocessamento manual (abaixo), nunca automaticamente.
- **Heartbeat e timeout de órfão (parâmetros confirmados pelo usuário)**: heartbeat a cada 5s; job em `running` sem heartbeat por 30s é considerado suspeito de órfão.
- **Tentativas (parâmetro confirmado)**: máximo de 3 tentativas totais, **incluindo a primeira execução** (ou seja, no máximo 2 retries automáticos após a tentativa inicial) — só para falhas classificadas como transitórias. Esgotadas as 3, `failed` definitivo.
- **Lease/posse (novo, exigido pelo usuário: "controle de posse/lease para evitar commits concorrentes")**: antes de iniciar o commit, o worker adquire `scope_lock` para o `provider+scope+period` do dataset (tabela da seção 3). Um segundo job para o mesmo escopo+período, de qualquer `import_batch`, falha a aquisição do lock e aguarda ou retorna erro claro — nunca corre em paralelo. O lock tem `expires_at` para não travar permanentemente se o detentor morrer (liberado pelo próprio reaper ao detectar o job órfão).
- **`checkpoint_row_offset`**: permite a um job retomado (caso transitório) continuar a validação de onde parou em arquivos grandes, sem reprocessar do zero — relevante para a meta de performance (seção 13).
- **Reprocessamento manual controlado (novo, exigido pelo usuário)**: endpoint `POST /api/v1/imports/{id}/retry`, distinto do requeue automático do reaper — só aplicável a jobs em `failed`, exige confirmação explícita (não é botão de "tentar de novo" automático na UI), e cada chamada é registrada com quem/quando acionou.

## 7-bis. Taxonomia de severidade e bloqueio de commit (critério "rejeição e quarentena" — substitui o limiar de 5% da v2.0)
Três níveis, aplicados por `import_row_rejection` (seção 3):
- **`info`**: desvio cosmético (ex.: espaço extra em campo texto) — não aparece como erro, só em log de auditoria.
- **`warning`**: campo opcional ausente, valor fora do range usual mas não financeiramente crítico — **não bloqueia commit**, aparece no relatório de qualidade do dataset.
- **`error`** (inclui toda "inconsistência financeira crítica"): moeda inválida/ausente, valor de custo não parseável como `Decimal`, campo obrigatório ausente (`billing_start`, `currency`, `billed_cost`), violação de unicidade de linha, granularidade inconsistente dentro do mesmo dataset sem rótulo — **qualquer linha `error` quarentena a linha e bloqueia o commit do `import_batch` inteiro**. Não existe commit parcial automático em F1. O `import_batch` fica em `rejected` com o relatório de `import_row_rejection` completo, disponível para correção e reimportação — nunca altera a base já committed (AT-002).
- Não há fluxo de aprovação humana para liberar commit parcial nesta fase (ver Conflito A, seção 0-bis) — essa é uma decisão de produto explícita, não uma lacuna técnica, e deve ser revisitada em F2/F3 se a taxa de rejeição real se mostrar um problema operacional.

## 8. Segurança local (critério 5 — parâmetros finais)
- **Rede**: API faz bind em `127.0.0.1` por padrão (não `0.0.0.0`); CORS explícito só para a origem do Vite dev server; nenhuma configuração de produção exposta nesta fase — já previsto em `AGENTS_SECURITY.md`, confirmado como requisito de F1.
- **Limite de upload (parâmetro confirmado)**: 200MB por arquivo, rejeitado antes de gravar em disco (streaming com corte, não leitura completa em memória primeiro — requisito do usuário, "processamento em streaming").
- **Limites de descompactação e memória (novo, exigido pelo usuário)**: se o adapter aceitar entrada comprimida (ex.: `.csv.gz`, Parquet já é comprimido internamente pela própria biblioteca), aplicar limite de tamanho descomprimido (ex.: 10x o tamanho comprimido ou um teto absoluto, o que for menor) e abortar o stream se o limite for excedido — proteção contra zip bomb. Memória de processamento usa leitura em chunks (streaming), nunca carrega o arquivo inteiro nem seu conteúdo descomprimido de uma vez.
- **Validação de formato**: extensão declarada **mais** verificação de magic bytes/MIME real do conteúdo (não confiar só na extensão) — um `.csv` que na verdade é um executável é rejeitado na validação, não só "tratado como CSV e falha depois". Lista de extensões permitidas fechada (`.csv`, `.parquet`, `.csv.gz`), qualquer outra rejeitada antes de qualquer parsing.
- **Proteção contra manipulação de caminho**: `original_filename` do usuário é armazenado só como metadado de exibição — **nunca** usado para compor um caminho de arquivo no disco. Todo path de gravação é construído a partir de IDs internos gerados pelo sistema (`import_batch.id`, `sha256`), passando por `path_safety.py`, que resolve o caminho final e verifica que ele está contido dentro do diretório base permitido antes de qualquer `open()`/`write()`.
- **Redação de logs (novo, exigido pelo usuário: "não registrar dados financeiros sensíveis em logs")**: logs estruturados do pipeline de ingestão contêm apenas IDs, hashes, contagens, códigos de severidade/motivo e timestamps — nunca o valor de `billed_cost`/`effective_cost`/`list_cost`/`contracted_cost`, nem o conteúdo bruto de uma linha rejeitada. `import_row_rejection.raw_excerpt_ref` aponta para o arquivo original armazenado (acessível só via API autenticada do dataset, não via log), nunca duplica o valor no próprio log.
- **Sanitização de CSV**: payloads de fórmula (`=`, `+`, `-`, `@`) neutralizados em qualquer exportação/preview.

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
| Performance | 5 medições por adapter, P95 + telemetria, conforme metodologia final da seção 13 |
| Segurança | inalterado + path traversal explícito |
| E2E | inalterado + fluxo de resolução de `dataset_overlap_flag` na UI |

## 12. Cenários de falha (atualizado com os parâmetros finais)
| Cenário | Comportamento esperado |
|---|---|
| Worker morre no meio do parsing de um arquivo grande | Falha classificada como transitória; job fica `running` com heartbeat parado; reaper detecta após 30s, requeue com checkpoint (attempt 2 de 3); retomada não duplica linhas já processadas |
| Worker esgota as 3 tentativas por falhas transitórias repetidas | Job vai para `failed` definitivo; reprocessamento só via `POST /imports/{id}/retry` manual, nunca automático de novo |
| Upload do mesmo arquivo duas vezes em paralelo (dois cliques) | Segundo request detecta hash em processamento (ou já committed) e retorna o `import_batch` existente, não cria um segundo job concorrente |
| Conexão com Postgres cai durante commit | Falha transitória; transação não efetivada; job volta para `queued`; novo attempt não deixa estado parcial |
| Disco cheio durante staging | Upload falha de forma explícita (`failed`, `error_detail` claro); nenhum arquivo parcial é tratado como válido; espaço já gravado é limpo |
| Nome de arquivo malicioso (path traversal) | Rejeitado em `path_safety.py` antes de qualquer gravação; falha permanente, sem retry; severidade `error`, sem detalhe interno de path exposto ao cliente |
| Arquivo comprimido que expande muito além do limite (zip bomb) | Stream abortado ao exceder o limite de descompactação (seção 8); falha permanente, sem retry; nenhum dado é persistido |
| Arquivo corrompido no meio do stream (CSV trunca a meio de uma linha) | Linha incompleta registrada em `import_row_rejection` com severidade `error` e offset exato; **commit do batch inteiro bloqueado** (sem limiar percentual — ver seção 7-bis); falha permanente (erro de dado, não de infraestrutura), sem retry automático; correção exige reimportação |
| Esquema financeiro crítico inválido (ex.: moeda ausente, custo não parseável) em qualquer linha | Mesmo tratamento do cenário anterior — `error` bloqueia o commit inteiro, falha permanente |
| Dois commits concorrentes para o mesmo `scope+period` (`import_batch` diferentes) | `scope_lock` (seção 7) impede aquisição simultânea; o segundo commit aguarda ou falha com mensagem clara, nunca corrida de gravação simultânea |

## 13. Metodologia de performance (parâmetro final, decisão 1 do usuário)
- **Meta**: validar, normalizar e persistir 100.000 linhas em até 60s.
- **Escopo medido**: começa com o arquivo já staged (pós-upload); inclui parsing+validação+normalização+commit transacional; **exclui** transferência de upload pela rede, inicialização de processo/conexão e qualquer renderização de UI.
- **Protocolo**: 5 medições por adapter (FOCUS 1.0r2 e Azure Cost Analysis), após 1 execução de aquecimento descartada. Reportar P95 das 5 medições, não a melhor nem a média.
- **Telemetria registrada por medição**: CPU, RAM, I/O de disco, sistema operacional e versões (Python, Postgres, bibliotecas de parsing) — para que o número não vire um dado sem contexto reprodutível.
- **Validação pós-medição, não só tempo**: cada uma das 5 execuções verifica integridade (contagem de linhas igual ao fixture), idempotência (reimportar a mesma massa não duplica) e corretude dos `import_row_rejection` esperados (o fixture de performance é limpo, então o esperado é zero rejeições).
- **Máquina de referência**: a ser executada e registrada no próprio ambiente de CI/dev onde os testes rodarem (container atual: especificações a capturar automaticamente no relatório de teste, não fixadas a priori em hardware específico) — isso resolve a lacuna "a definir" do `PRODUCT_REQUIREMENTS.md` de forma reprodutível em vez de prometer um número de hardware que pode não corresponder ao ambiente real de execução.

## 14. Critérios de aceite objetivos (consolidados)
Mantidos da v1.0/v2.0 (AT-001 a AT-004 parciais, 0 achados críticos de segurança, nenhuma tela com número agregado), mais:
- 100% dos cenários da seção 12 cobertos por teste automatizado e com comportamento conforme a tabela — nenhum é "documentado mas não testado".
- Deduplicação por hash e detecção de sobreposição financeira nunca compartilham código nem mensagem de usuário — auditável lendo o diff do PR.
- Nenhuma linha de severidade `error` resulta em commit parcial em nenhum teste — verificação explícita de que o limiar de 5% não existe mais em código nem em teste.
- Toda falha classificada como permanente nos testes de `tests/failure` não consome tentativa de retry nem aciona o reaper.
- `scope_lock` impede, em teste de concorrência real (duas requisições simultâneas), que dois commits do mesmo `scope+period` sejam efetivados.
- Nenhum log gerado durante os testes de integração/falha contém valor de campo financeiro (`billed_cost` etc.) em texto plano — verificado por scanner de log dedicado.
- Performance: as 5 medições por adapter executadas, P95 registrado com a telemetria completa da seção 13 — mesmo que a meta de 60s não seja batida na primeira rodada, o número real é reportado, não arredondado para "passou".
- `import_field_mapping` consultável via API para qualquer `import_batch_id` committed, com histórico completo de edições manuais.

## 15. Resumo dos parâmetros finais (para referência rápida)
| Parâmetro | Valor |
|---|---|
| Heartbeat do worker | 5s |
| Timeout de suspeita de órfão | 30s |
| Máximo de tentativas (incluindo a primeira) | 3, só para falhas transitórias |
| Falha permanente | vai direto a `failed`, sem consumir tentativa, sem reaper |
| Limite de upload | 200MB por arquivo |
| Limite de descompactação | proporcional ao comprimido (ex.: 10x) ou teto absoluto, o menor dos dois |
| Commit parcial automático | **não existe** em F1 — qualquer `error` bloqueia o batch inteiro |
| Fluxo de aprovação para commit parcial | **não construído** em F1 (cláusula de segurança do usuário aplicada) |
| Meta de performance | 100k linhas em ≤60s, P95 de 5 medições, excluindo upload/init/render |
| Extensões aceitas | `.csv`, `.parquet`, `.csv.gz` |

Todos os pontos abertos da v2.0 estão resolvidos. Não há parâmetro pendente de confirmação nesta versão.
