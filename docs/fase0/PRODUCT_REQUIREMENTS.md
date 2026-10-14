# Visão do produto e requisitos funcionais

## Atores e Jobs-to-be-done
**Analista FinOps:** importar gastos, investigar variações, explicar custo e priorizar oportunidades.
**Arquiteto de Cloud:** verificar viabilidade técnica, impactos e riscos de otimizações.
**Gestor:** visualizar orçamento, tendência, economia e ações pendentes.
**Administrador local:** configurar moeda, thresholds, dados, modelos e chaves de API.

## Escopo
Fase MVP local: workspace único, importação manual (FOCUS CSV/Parquet e Azure export quando reconhecido), normalização, dashboard, análises, KPIs, forecast básico, anomalias, oportunidades com regras de suporte, simulador what-if, backlog e relatório, chat Claude read-only. Conectores, processamento agendado, multiusuário e automação REAL: fases posteriores.

## Catálogo funcional (IDs rastreáveis)
| ID | Módulo | Requisitos essenciais | Prioridade / fase |
|---|---|---|---|
| FR-001 | Data Hub | Upload múltiplos CSV/Parquet/JSON, metadados, hash, preview, encoding, delimitador, progressos | P0 |
| FR-002 | Data Hub | Detectar FOCUS e versão; mapeamento manual para esquemas desconhecidos | P0 |
| FR-003 | Data Hub | Pré-validação de período, cabeçalhos, moedas, nulos, duplicados, tipos; relatório de rejeições | P0 |
| FR-004 | Data Hub | Importar em estágio, confirmar e fazer commit transacional/idempotente | P0 |
| FR-005 | Cockpit | KPIs total, gasto por período, anomalias, cobertura de atribuição, forecast e savings por estado | P0 |
| FR-006 | Analytics | Slice/dice serviço, recurso, billing account, subscription, RG, tags, ambiente, região, moeda | P0 |
| FR-007 | Analytics | Seleção explícita Billed/Effective/List/Contracted conforme disponibilidade; separar métricas | P0 |
| FR-008 | Forecast | Baseline sazonal simples com intervalos e indicação de insuficiência, comparação budget | P0 |
| FR-009 | Anomalias | Sinais robustos por dia/serviço, limiar mínimo monetário, impacto, evidências | P0 |
| FR-010 | Optimization | Idle/discos/rightsizing somente quando dados operacionais bastam; senão lacuna | P0 |
| FR-011 | Simulação | Cenário what-if com hipóteses, custo atual e projetado, sobreposição e risco | P0 |
| FR-012 | Savings | Pipeline discovered→review→approved→implemented→validated/rejected com snapshots | P0 |
| FR-013 | Relatórios | Exportar PDF/CSV/JSON, fonte, data de corte, ressalvas, dados ausentes | P1 |
| FR-014 | AI | Chat read-only, RAG sobre resultados SQL autorizados, tool-calls definidos, referências | P1 |
| FR-015 | Governança | Tags faltantes, responsabilidade, custos não alocados, políticas locais | P1 |
| FR-016 | Compromissos | Coverage/utilization após contratos e uso amortizado disponíveis | P2 |
| FR-017 | Unit economics | Importar volumes de transações e mapear custo → unidade | P2 |
| FR-018 | Conectores | Azure e OCI inicialmente; AWS e GCP depois | P2 |
| FR-019 | Aprovações | Tickets, logs e pull requests controlados; sem execução de produção no MVP | P3 |
| FR-020 | Multiusuário | Auth, isolamento de tenant, RBAC e política empresarial | P3 |

## 12 seções alvo do produto
Cockpit; Data Hub; Cost Analytics; Optimization; Agentic FinOps; Forecast & Budgets; Commitments; Unit Economics; Governance; Savings Tracker; Simulations & Capacity; Reports/Assistant.
No MVP, algumas aparecem como áreas com estado 'Em desenvolvimento' em vez de telas falsas.

## Resultados visíveis obrigatórios
Cada KPI: nome, definição, custo-base, período, moeda, origem, janela de atualização, status verified/estimated/insufficient, fórmula/metodologia e drill-down.
Cada oportunidade: ID, tipo, alvo, evidência, custo baseline, período, economia bruta/líquida estimada, risco, pressupostos, dependências, concorrência com outras oportunidades, owner, ação proposta, estado e validação.

## Requisitos não funcionais
- Localhost exclusivamente por padrão; nenhum dado enviado para IA sem ação explícita e prévia pré-visualização dos campos transmitidos.
- Sessão local e secrets no backend; jamais embutir API keys no JavaScript ou nos relatórios.
- Testes determinísticos dos cálculos e regressão usando fixtures versionadas.
- Importação resiliente, rollback, idempotência, streaming, performance de 100k linhas em fixture de referência a definir.
- Acessibilidade básica teclado/contraste; responsivo desktop prioritário.
- Sem alegar medição em tempo real ao processar uploads manuais.

## Fora do escopo inicial
Alterações diretas em infraestrutura, predição de CPU sem telemetria, auditoria completa de contratos sem fontes, benchmark universal de economia, integração automática com cloud, login corporativo, workflows SaaS.
