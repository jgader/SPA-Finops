# Auditoria de viabilidade e diferenciação — FinOps AI vs. Microsoft FinOps Hubs
Versão 1.0 (consolidada) | 14/10/2026 | Status: **APROVADA pelo usuário em 14/10/2026** — decisões registradas na seção 5. Nenhum código de produto foi escrito até esta versão.

> Histórico: v0.1 foi escrita com 5 dos 9 documentos da Fase 0 (faltavam `PRODUCT_REQUIREMENTS.md`, `DATA_CONTRACTS.md`, `FINOPS_RULES.md`, `CLAUDE_CODE_BOOTSTRAP.md`, entregues depois em `FinOps_AI_Fase0_Especificacao.zip`). v0.2 revisou com os 9 documentos completos e levantou 7 decisões pendentes. Esta v1.0 consolida o resultado final: remove o texto de transição v0.1→v0.2 e registra as decisões já tomadas pelo usuário. Os 9 documentos originais permanecem inalterados em `docs/fase0/`.

## Confirmação de leitura dos 9 documentos da Fase 0
| Documento | Linhas | Lido integralmente |
|---|---|---|
| `00_README.md` | 24 | Sim |
| `PRODUCT_REQUIREMENTS.md` | 53 | Sim |
| `ARCHITECTURE.md` | 45 | Sim |
| `DATA_CONTRACTS.md` | 35 | Sim |
| `FINOPS_RULES.md` | 36 | Sim |
| `AGENTS_SECURITY.md` | 25 | Sim |
| `UI_UX_SPEC.md` | 34 | Sim |
| `ACCEPTANCE_AND_ROADMAP.md` | 38 | Sim |
| `CLAUDE_CODE_BOOTSTRAP.md` | 21 | Sim |

## 1. Resposta à pergunta de viabilidade (mantida desde v0.1)
Reconstruir o FinOps Hubs não se justifica. O Hubs é um pipeline de dados + BI maduro para quem já vive em Azure/Power BI/KQL (ingestão FOCUS nativa, Data Factory, Data Explorer, 5 relatórios Power BI, recomendações via Advisor, savings EA/MCA). Ele **não** entrega reconciliação com evidência auditável, simulação, nem investigação com proveniência estruturada — é aí que está a diferenciação defensável do FinOps AI: reconciliação financeira ativa, relatório de oportunidades que se nega a inventar economia sem dado de suporte, e investigação assistida com saída validada (`summary/facts/hypotheses/data_gaps/recommendations/limitations`, conforme `AGENTS_SECURITY.md`).

Fontes externas consultadas sobre o FinOps Hubs: https://learn.microsoft.com/cloud-computing/finops/toolkit/hubs/finops-hubs-overview , https://learn.microsoft.com/cloud-computing/finops/toolkit/hubs/data-model , https://learn.microsoft.com/cloud-computing/finops/toolkit/hubs/deploy , https://learn.microsoft.com/cloud-computing/finops/toolkit/hubs/configure-scopes , https://techcommunity.microsoft.com/blog/finopsblog/ , https://focus.finops.org/docs/specification/v1-4/datasets/ .

## 2. Matriz construir / integrar / adiar (vigente)
| FR (`PRODUCT_REQUIREMENTS.md`) | Item | Decisão PoV |
|---|---|---|
| FR-001–FR-004 | Data Hub: upload, detecção FOCUS, pré-validação, staging/commit idempotente | **Construir — F1** |
| FR-006, FR-007 | Analytics: slice/dice básico e cost basis | **Construir — F2 (mínimo)** |
| — | Reconciliação FOCUS vs. Azure Cost Analysis, anti-dupla-contagem, anti-soma-de-moeda | **Construir — F2** |
| FR-009 (parcial) | Anomalias/variação com causa estruturada | **Construir — F2, com qualificação de confiança obrigatória** |
| FR-014 | Investigação assistida por Claude (read-only) | **Construir — F4, com teto de custo e consentimento** |
| FR-013 | Relatório exportável com proveniência | **Construir — F4 (mínimo: 1–2 formatos)** |
| FR-005 | Cockpit (recorte: gasto, variação, oportunidades) | **Construir — F2/F4, sem forecast/savings pipeline completos** |
| FR-010 | Optimization completo (idle VM, rightsizing, disco órfão, scheduling, storage tier) | **Adiar** — PoV demonstra só o *padrão* de confiança (`verified/estimated/insufficient/blocked`) com 1 caso, fora das 4 áreas funcionais da PoV (decisão 7) |
| FR-008, FR-011, FR-012, FR-015–FR-020 | Forecast, simulação, savings pipeline, governança, compromissos, unit economics, conectores, aprovações, multiusuário | **Adiar** — já fora do MVP no `PRODUCT_REQUIREMENTS.md` original |

**Incompatibilidade registrada, não corrigida automaticamente**: `PRODUCT_REQUIREMENTS.md` marca FR-010 (Optimization) como prioridade **P0**, mesma categoria de Data Hub e Cockpit. A decisão 7 do usuário (seção 5) exclui Optimization das 4 áreas funcionais da PoV. Isso é uma divergência legítima de uma PoV recortada frente ao catálogo P0 do documento original — registro aqui para que não pareça que o P0 foi ignorado por omissão; ele foi conscientemente postergado para depois da PoV.

## 3. Esquema de dados (vigente, de `DATA_CONTRACTS.md`)
PoV usa o subconjunto: `import_batch`, `dataset`, `cost_usage` (com `billed_cost`/`effective_cost`/`list_cost`/`contracted_cost` separados, `raw_ref` preservando o bruto), `analysis_run`. `resource`, `resource_metric`, `budget`, `scenario`, `opportunity`, `savings_validation` só entram quando F2/F4 exigirem.

## 4. Critérios quantitativos (vigentes, de `FINOPS_RULES.md` e decisões do usuário)
| Métrica | Origem | Critério |
|---|---|---|
| Reconciliação FOCUS vs. Azure Cost Analysis | `total_cost = SUM(cost_value)` por cost_basis/período/moeda únicos | Diferença ≤ 0,5% sem divergência proposital; divergência proposital explicada e rotulada |
| Não dupla contagem entre datasets sobrepostos | `DATA_CONTRACTS.md` | 0 falso negativo nos overlaps injetados; falso positivo ≤ 5% |
| Bloqueio de soma cross-currency | ISO 4217, nunca somar sem FX datado | 100% dos casos com 2+ moedas bloqueados ou exigindo FX |
| Anomalias | MAD, mínimo 28 pontos diários recomendado (decisão 4) | Com <28 pontos, resultado sai qualificado como baixa confiança, nunca como anomalia confirmada |
| Causas de variação | Decisão 5: fatos comprovados, decomposição matemática, correlações, hipóteses de IA e dados ausentes, cada um rotulado separadamente | Hipótese de IA nunca aparece como causa confirmada |
| Rightsizing sem telemetria | Estado `insufficient` (`FINOPS_RULES.md`) | 100% dos casos sem CPU/memória suficiente retornam `insufficient` |
| Qualidade da investigação do agente | `AGENTS_SECURITY.md`: schema validado | ≥ 80% aprovação em teste cego; 0% de afirmação sem `get_provenance` |
| Performance de importação | Decisão 3 | 100.000 registros em ≤ 60s, sujeito a máquina/formato/metodologia de referência (a confirmar no plano F1, seção 6) |
| Custo por investigação do agente | Decisão 6 | Teto configurável de US$ 0,25/investigação; limite de tokens; bloqueio automático ao atingir orçamento; consumo real registrado |

## 5. Decisões aprovadas pelo usuário em 14/10/2026 (substituem as 7 "decisões pendentes" da v0.2)
1. **FOCUS**: primeiro adaptador concreto para Azure FOCUS 1.0r2; modelo canônico versionado preservando referência futura a FOCUS 1.4; nunca inventar campo ausente na exportação real.
2. **Sequenciamento**: F1 (fundação/importação) → F2 (analytics/reconciliação mínima) → F4 (investigação por IA limitada), cada etapa com validação e aprovação explícita antes da seguinte. F3 (optimization/simulation completos) não faz parte da PoV.
3. **Performance**: meta inicial de 100 mil registros em até 60s, sujeita a definição de máquina de referência, formato de arquivo e metodologia de medição (ver plano F1).
4. **Anomalias**: regra MAD de `FINOPS_RULES.md`, 28 pontos diários mínimo recomendado; histórico insuficiente produz resultado qualificado, nunca confiança artificial.
5. **Causas de variação**: saída separa fatos comprovados, decomposição matemática, correlações, hipóteses de IA e dados ausentes; hipótese de IA nunca é apresentada como causa confirmada.
6. **Custo de IA**: teto configurável inicial de US$ 0,25/investigação, limite de tokens, registro de consumo real, bloqueio automático de novas chamadas ao atingir o orçamento; nenhuma transmissão de dado sem consentimento explícito.
7. **Interface**: 4 áreas funcionais na PoV — Data Hub, Cockpit, Cost Analytics, Investigação/Relatórios — preservando a experiência visual do Capacity Planning (UI_UX_SPEC.md); demais módulos ficam no roadmap, nunca simulados como reais.

Nenhuma dessas decisões contradiz os 9 documentos originais de forma irreconciliável. Os pontos de atenção (não incompatibilidades bloqueantes) estão registrados: o conflito de versão FOCUS (decisão 1 resolve na prática, mas o `DATA_CONTRACTS.md` original continua citando 1.4 como baseline — ver plano F1, seção 3), e a exclusão de FR-010/P0 da PoV (seção 2 acima).

## 6. Independência arquitetural do FinOps Hubs
A PoV não depende de Azure Data Factory, Data Explorer ou Power BI do Hubs — usa Postgres + Parquet/DuckDB locais, conforme `ARCHITECTURE.md`. A integração futura com um ambiente que já rode FinOps Hubs é possível via `ProviderAdapter.capabilities()`: um adapter poderia, no futuro, ler do container de ingestão do Hubs ou do seu cluster Data Explorer como *fonte* alternativa, sem que o FinOps AI dependa da infraestrutura do Hubs para funcionar. Isso é detalhado no plano de execução F1 (próximo documento).

## Próximos passos
Auditoria aprovada. O plano de execução específico de F1 está em `docs/PLANO_EXECUCAO_F1.md`, aguardando aprovação final antes de qualquer implementação.
