# Relatório de entrega — F1: Fundação e Importação
Versão 1.0 | 14/10/2026 | Status: F1 implementada e testada localmente. Aguardando aprovação explícita para avançar a F2.

> Referências: `docs/PLANO_EXECUCAO_F1.md` v3.1 (plano autorizado), `docs/CHECKLIST_GO_NOGO_F1.md`. Nenhum dos 9 documentos originais em `docs/fase0/` foi alterado.

## 1. Resumo
F1 está implementada: upload → identificação de esquema (2 adapters concretos: Azure FOCUS 1.0r2 e Azure Cost Analysis nativo) → validação com taxonomia de severidade → staging → commit transacional idempotente com proteção de concorrência (scope_lock + fencing token) → dataset consultável via API e SPA. **Nenhuma** agregação, KPI, reconciliação, forecast, oportunidade ou chamada à Claude API foi implementada — rigorosamente fora do escopo autorizado.

**52 testes automatizados, todos passando** (18 unit, 13 integração, 11 segurança, 6 falha/concorrência, 1 performance, 3 E2E contra navegador real). Meta de performance (100k linhas / ≤60s) batida com folga: **P95 = 11,14s**.

## 2. Arquivos alterados/criados
```
alembic.ini, pyproject.toml, requirements.txt, .env.example, .gitignore, README.md
docs/RELATORIO_ENTREGA_F1.md                           (este arquivo)

services/api/app/
  config/settings.py
  db/session.py, db/migrations/env.py, db/migrations/versions/e1e379fd92f9_*.py
  domains/canonical_financial/models.py
  domains/ingestion/{adapters/{base,focus_1_0r2,azure_cost_analysis,__init__},
    sniffing, validation, dedup, overlap, field_mapping, staging, commit,
    granularity, identity, errors}.py
  security/{path_safety, upload_guard, csv_sanitize}.py
  schemas/{imports, datasets}.py
  api/v1/{imports, datasets, overlap}.py
  services_worker_bridge.py, main.py

services/worker/
  jobs/import_job.py, reaper.py, main.py

packages/fixtures/
  README.md, generators/{common, generate_all}.py, data/*.csv (8 fixtures)

apps/web/
  package.json, vite.config.ts, tsconfig.json, index.html
  src/main.tsx, src/app/{App.tsx, api.ts}, src/design-system/tokens.css
  src/features/data-hub/DataHub.tsx, src/features/shell-placeholders/Placeholder.tsx

tests/
  conftest.py
  unit/{test_smoke, test_adapters, test_granularity, test_identity_and_dedup_overlap_isolation}.py
  integration/{test_import_flow, test_overlap_resolution, test_dedup_triple_reimport_regression}.py
  security/{test_upload_security, test_log_redaction}.py
  failure/{test_fencing_token, test_reaper_and_scope_lock}.py
  performance/test_import_performance.py, performance/last_report.json
  e2e/test_data_hub_e2e.py
```

## 3. Migrations
Uma revisão Alembic (`e1e379fd92f9_f1_initial_schema`), aplicada e testada em `finops_ai` e `finops_ai_test`:
- `import_batch`, `dataset`, `cost_usage` — forma idêntica a `DATA_CONTRACTS.md`, sem alteração.
- `import_job` — estados persistentes, heartbeat, checkpoint, classificação de falha.
- `import_field_mapping` — mapeamento auditável, imutável por linha.
- `dataset_overlap_flag` — sobreposição financeira, `dataset_id`/`pending_import_batch_id` nullable (sinalização antes do commit existir).
- `scope_lock` — lease com `fencing_token` (sequence dedicada `scope_lock_fencing_token_seq`).
- `import_row_rejection` — quarentena estruturada por severidade/motivo/campo.
- Campo novo em `cost_usage`: `natural_key_hash` (identidade de lançamento financeiro).
- Campos novos em `dataset`: `granularity`, `granularity_source`.

Downgrade testado e funcional (usado durante o desenvolvimento para corrigir 2 erros de schema antes de qualquer dado real existir — ver seção 7).

## 4. Testes executados (resultado real, não resumo otimista)
```
tests/unit          18 passed
tests/integration    13 passed
tests/security       11 passed
tests/failure         6 passed
tests/performance     1 passed  (P95 = 11.14s, meta 60s)
tests/e2e              3 passed  (requer API+worker+SPA rodando — executado manualmente, não entra na suíte padrão de CI sem esse setup)
──────────────────────────────
TOTAL                52 passed, 0 failed
```
Comando: `python -m pytest tests/ -q -m "not performance and not e2e"` (suíte rápida, ~4s) e `python -m pytest tests/performance` (~70s) e `python -m pytest tests/e2e/test_data_hub_e2e.py` (com os 3 processos ativos).

### Cobertura por critério de aceite (`ACCEPTANCE_AND_ROADMAP.md`)
| Critério | Status | Evidência |
|---|---|---|
| AT-001 (reimport mesmo hash não duplica) | **Atendido** | `test_exact_duplicate_reimport_is_idempotent_noop`, `test_three_successive_identical_uploads_all_resolve_to_committed` |
| AT-002 (CSV malformado rejeitado por linha/campo, preserva origem, não altera base aprovada) | **Atendido** | `test_malformed_file_rejected_and_preserves_approved_base` |
| AT-003 (2 moedas não somadas silenciosamente) — parte de captura | **Atendido (F1)**; bloqueio de agregação é F2 | `test_multicurrency_captured_without_coercion` |
| AT-004 (datasets superpostos não dobram total faturado) — parte de detecção | **Atendido (F1)**; prevenção de soma é F2 | `test_different_hash_same_scope_period_flags_overlap_never_deletes` |
| AT-011 (indicadores não dependem só de cor) | **Atendido** | badges de severidade com texto explícito, verificado em `test_malformed_upload_shows_rejection_table_with_accessible_text_labels` |
| AT-013 (nenhum endpoint de alterar VM/remover storage) | **Atendido** | Nenhum endpoint de escrita em infraestrutura existe no código |

## 5. Resultado do benchmark de performance
```json
{
  "target_seconds": 60, "expected_rows": 100000, "runs": 5, "warmup_runs": 1,
  "p95_seconds": 11.14, "mean_seconds": 10.84,
  "measurement_scope": "staging (parse+validacao) + commit transacional; exclui upload, inicializacao de processo e renderizacao",
  "telemetry": {"os": "Linux-6.18.44-fc-v114-x86_64", "cpu_count": 4, "max_rss_kb": 526864}
}
```
Arquivo completo em `tests/performance/last_report.json`. Meta batida com margem de ~5,4x — folga saudável para o volume real de produção crescer sem risco imediato à meta.

## 6. Evidência visual (UI real, não mock)
Validado em navegador real (Chromium, via Playwright) contra API+worker+SPA rodando:
- Caminho feliz: upload → "[Comitado]" → dataset listado com 488 linhas, granularidade `daily (usage_period)`.
- Caminho de rejeição: upload malformado → "[Rejeitado]" → tabela de 4 erros com severidade em texto (não só cor) → dataset anterior preservado intacto na listagem.
- Áreas placeholder (Cockpit, Cost Analytics, Investigação/Relatórios): "Em desenvolvimento", nenhum número inventado.

## 7. Problemas encontrados e decisões durante a implementação (registro de desvios)
1. **`charge_category` modelado errado inicialmente**: a primeira versão da migration restringia `charge_category` aos 4 nomes de cost basis (billed/effective/list/contracted) — confundindo a *categoria* FOCUS (Usage/Purchase/Tax/Credit/Adjustment) com as *colunas* de custo. Corrigido antes de qualquer dado existir (downgrade+upgrade).
2. **Granularidade de teste com span=0**: as primeiras fixtures geravam `usage_start == usage_end` (mesmo instante), que meu classificador de granularidade não reconhecia como "diário" (span de 0 dias, não ~1). Corrigido gerando `usage_end = usage_start + 1 dia`, consistente com a semântica de período de uso do FOCUS.
3. **Ordem de verificação no commit**: a primeira versão do `commit_import_batch` checava sobreposição *antes* de verificar o fencing token — um worker obsoleto conseguiria criar `dataset_overlap_flag` espúrias antes de ser barrado. Corrigido: fencing token é verificado primeiro, antes de qualquer leitura/escrita de domínio (ver `docs/PLANO_EXECUCAO_F1.md` seção 7-ter, já refletida no código).
4. **Dedup com múltiplos committed do mesmo hash**: reimportações sucessivas do mesmo arquivo geravam múltiplos `import_batch` com `status='committed'` e o mesmo `sha256`; `find_committed_duplicate` usava `scalar_one_or_none()`, que lança exceção com mais de uma linha. **Encontrado durante o teste manual em navegador real** (não pelos testes automatizados que rodavam antes dessa correção) — corrigido para pegar o mais antigo (`order_by(uploaded_at).limit(1)`), com teste de regressão dedicado (`test_dedup_triple_reimport_regression.py`).
5. **`UPLOAD_STAGING_DIR` relativo quebra entre processos**: o padrão `./data/incoming` resolve diferente conforme o diretório de onde API e worker são iniciados — são processos separados. Documentado no `README.md`: exigir caminho absoluto idêntico para os dois processos (mapeia diretamente para o padrão de produção de volume compartilhado).
6. **Performance de insert**: a primeira implementação usava `session.add()` por linha (ORM) para as 100k linhas de `cost_usage` — substituído por bulk insert via SQLAlchemy Core (`CostUsage.__table__.insert()` com lista de dicts), dentro da mesma transação, sem perda de atomicidade. Resultado: P95 de 11s (sem essa troca, não foi medido quanto levaria, mas a abordagem ORM-por-linha é ordens de magnitude mais lenta para volumes desse tamanho).
7. **Limitação aceita, não corrigida**: `commit_import_batch` assume que todas as linhas de um `import_batch` compartilham o mesmo `billing_account` (usa o da primeira linha para compor `scope_key`). Arquivos com múltiplas contas de faturamento num único upload não são suportados corretamente em F1 — nenhuma fixture testa esse caso, e nenhuma validação o rejeita explicitamente hoje. Registrado como risco residual (seção 9).

## 8. O que foi deliberadamente NÃO implementado (dentro do escopo F1)
- Fluxo de aprovação humana para commit parcial (decisão explícita do GO condicional — "se não houver suporte seguro, bloquear").
- Supersessão de dataset (`resolution=replace_approved`) — aceito e registrado, mas commit permanece bloqueado; sem versionamento de dataset no schema mínimo de F1.
- Qualquer chamada à Claude API, qualquer tela de Cockpit/Cost Analytics/Investigação com dado real.
- Conectores de nuvem ao vivo, qualquer endpoint de escrita em infraestrutura.
- Multi-billing-account por import_batch (seção 7, item 7).

## 9. Riscos residuais
- **Multi-billing-account por batch** (seção 7.7) — baixo risco para a PoV (fixtures e caso de uso atual são single-account), mas precisa de decisão explícita antes de F2 se o uso real tiver arquivos com múltiplas contas.
- **`replace_approved` sem implementação real** — se um usuário real escolher essa resolução esperando que o dataset antigo seja substituído, a UI/API precisa deixar isso claro (hoje só o campo `note` da resposta API comunica isso; a SPA não expõe a tela de resolução de overlap ainda — só o endpoint existe e foi testado via API/integração, não via UI).
- **Teste E2E depende de setup manual** (3 processos rodando) — não roda em CI sem automação adicional (docker-compose + health-check); funcional mas não é self-contained hoje.
- **Scope lock não testado sob carga real concorrente (múltiplos processos OS reais)** — o teste de concorrência (`test_fencing_token.py`, `test_two_different_batches_cannot_hold_scope_lock_concurrently`) valida a lógica dentro de uma única conexão/processo de teste; não há teste de 2 processos `python services/worker/main.py` reais disputando o mesmo lock simultaneamente.

## 10. Limitações conhecidas (não são bugs, são escopo)
- Performance medida no ambiente de desenvolvimento deste container (4 vCPU), não num ambiente de referência fixo — telemetria completa registrada para contextualizar o número em qualquer leitura futura.
- Resolução de overlap (`kept_both_as_correction`/`rejected`) só acessível via API nesta entrega; UI de resolução fica para a próxima iteração dentro do próprio escopo de F1 ou início de F2 (a decidir).

## 11. Instruções de execução local
Ver `README.md` na raiz do repositório — setup completo, variáveis de ambiente, comandos de migration, geração de fixtures e execução dos 3 processos.

## 12. Próximos passos
F1 está pronta para revisão. **Não avanço para F2 sem nova autorização explícita**, conforme instruído. Pontos que recomendo decidir antes de F2:
1. Confirmar se o risco de multi-billing-account (seção 9) precisa ser endereçado agora ou pode esperar.
2. Decidir se a UI de resolução de overlap entra ainda em F1 (pequeno incremento) ou só em F2.
3. Confirmar que o benchmark de performance do ambiente de desenvolvimento é aceitável como evidência, ou se é necessário medir num ambiente de referência mais próximo de produção.
