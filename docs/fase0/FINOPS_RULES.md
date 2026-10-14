# Regras analíticas, fórmulas e prioridades

## Princípios
Três fases da FinOps Foundation: Inform, Optimize e Operate; maturidade Crawl/Walk/Run. Os cálculos seguem engine determinístico e métodos registrados. Nenhuma oportunidade é economia realizada até validação financeira posterior.

## Métricas
- `total_cost = SUM(cost_value)` para cost_basis escolhido, período delimitado, moeda única, atribuição e filtros declarados.
- `allocation_coverage = attributable_cost / eligible_total_cost`, definindo explicitamente elegibilidade e estratégia de custos compartilhados.
- `budget_variance = actual - budget` e `budget_consumption = actual/budget`, cuidando de mês parcial.
- `forecast_error_WAPE = SUM(abs(actual-forecast))/SUM(abs(actual))` nos períodos avaliáveis; se denominador zero, n/a; manter MAE.
- `commitment_utilization = consumed_commitment / purchased_commitment` e `coverage = eligible_spend_under_commitments / eligible_total_spend` só com dados contratuais apropriados.
- `realized_savings = counterfactual_adjusted_baseline - observed_adjusted_cost`, com contrafactual revisável, janela e efeitos concorrentes.
- `unit_cost = eligible_allocated_cost/business_units`, com denominador e política de rateio auditáveis.

## Detecção de anomalias V1
Por série diária homogênea de serviço/recurso: baseline mediana e dispersão robusta (MAD) ou desvio absoluto com tratamento quando MAD=0; mínimo 28 pontos recomendado para detecção sazonal semanal; exigir impacto monetário mínimo e fator relativo; marcar mudanças de catálogo e dados faltantes. Em histórico curto, usar regras simples e qualificar como baixa confiança. Anomalia ≠ desperdício comprovado.

## Forecast V1
Baseline última janela, média móvel e opção tendência; backtesting de janelas completas; configurar periodicidade, horizonte e intervalo de predição. Não mostrar faixa estatística sem método calibrado. Forecast futuro não é gasto realizado.

## Oportunidades V1
**Idle VM:** exigir métricas cobertura suficiente, avaliação de janelas 7/14/30 dias configuráveis, CPU/memória/rede/IO, horário, criticidade e dependências; resultado 'candidato a revisão', jamais 'desligar automaticamente'.
**Rightsizing:** requer SKU atual, série histórica de CPU e memória, cobertura percentis e sazonalidade, SKU candidato real e cotação; respeitar arquitetura, IOPS, throughput, licença e restrição regional.
**Disco órfão:** requer inventário atual `attached=false`, idade, snapshots/backup, owner, dependências e custo atribuível.
**Scheduling:** depende de janela de utilização e dependência operacional; economia = horas faturáveis evitáveis × preço marginal ajustado; cautela com reserva e custos não variáveis.
**Storage tier:** dados de acesso, egress/retrieval e política de retenção; economia líquida inclui acesso/recuperação/migração.
**Commitments:** só depois de otimizações de capacidade; cobertura, utilização, duração, rampas e risco contratual.

## Prevenção de dupla contagem
Agrupar recomendações pelo mesmo recurso, mesmo componente financeiro e mesmo período; cálculo conjunto com dependências/precedência. Cenário mostra bruto, overlaps, custo de implementação, líquido e sensibilidade. Não somar diretamente cada oportunidade.

## Confiança
verified: cálculo auditado e fontes adequadas; estimated: simulação com premissas; insufficient: dados críticos ausentes; blocked: conflito/safety rule. Nível de confiança da recomendação também incorpora cobertura, recência, evidência e criticidade; nunca reduzir a um score sem explicar componentes.

## Operacionalização FinOps
Fila de oportunidades → revisão técnica → aprovação → execução fora do MVP → janela de observação → resultado validado. Guardar snapshots before/after e motivo de rejeição.
