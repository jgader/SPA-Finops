# Auditoria de viabilidade e diferenciação — FinOps AI vs. Microsoft FinOps Hubs
Versão 0.1 | 14/10/2026 | Status: ANÁLISE PARA DECISÃO — nenhum código de produto foi escrito nesta etapa.

> Escopo deste documento: responder "vale a pena construir isso, e o quê exatamente, antes de qualquer outra coisa" — não é uma reafirmação do plano em `docs/fase0/`. Onde o plano original é ambicioso demais para uma PoV, este documento recorta e diz por quê.

## 0. Gap de insumos
O `00_README.md` da Fase 0 lista 8 documentos como ordem de leitura. Só 5 foram fornecidos: `UI_UX_SPEC`, `00_README`, `ACCEPTANCE_AND_ROADMAP`, `AGENTS_SECURITY`, `ARCHITECTURE`. Faltam **PRODUCT_REQUIREMENTS.md**, **DATA_CONTRACTS.md**, **FINOPS_RULES.md** e **CLAUDE_CODE_BOOTSTRAP.md** — exatamente os documentos que definiriam personas/escopo (G0-1), o schema FOCUS/Azure versionado (G0-2) e as fórmulas/limiares (G0-4). Esta auditoria foi escrita a partir do que existe; qualquer número de fórmula ou campo citado abaixo é proposta minha, não extração de um contrato já aprovado. Antes de codificar, os 3 documentos ausentes precisam existir e ser revisados — caso contrário G0-2 a G0-4 não têm como ser considerados atendidos de fato, só "aprovados no papel".

## 1. Resposta direta à pergunta de viabilidade
**Reconstruir o FinOps Hubs não se justifica, e não é isso que o plano da Fase 0 propõe — mas o plano, como está, ainda gasta uma fração grande do primeiro ciclo de construção (F1–F2) em capacidades onde o Hubs já é maduro, e só chega à parte diferenciadora (F4, agente) depois.** A recomendação é invertida: a PoV deve provar primeiro o que o Hubs não faz (reconciliação com evidência + investigação assistida + relatório de oportunidade com proveniência), usando a menor base analítica possível, e só then decidir se o resto (forecast, simulação, UI completa de 12 áreas) merece ser construído.

Risco que o plano atual não nomeia explicitamente: se a resposta de valor do agente Claude for genérica ("isso parece uma VM subutilizada, considere rightsizing") sem nada que o Advisor/Hubs já não diga, a PoV falha mesmo que toda a engenharia funcione. Isso tem que ser testável antes de se investir em pipeline — ver seção 5.

## 2. O que o Microsoft FinOps Hubs já cobre bem
Baseado em documentação pública (ver fontes ao final):

| Capacidade | Hubs/Toolkit | Observação |
|---|---|---|
| Ingestão de exports Cost Management (Azure) | Sim, nativa | Data Factory + Storage Gen2, FOCUS 1.0 (1.2 em backport) |
| Normalização FOCUS | Sim | `Costs_raw`/`Costs_final` com funções versionadas em Data Explorer |
| Multi-cloud (AWS/GCP/OCI) | Parcial | Requer conversão externa para FOCUS 1.0 e drop manual no container; não é "conector" out-of-the-box |
| Análise ad hoc (KQL/Data Explorer) | Sim | Forte para quem sabe KQL; não é self-service para analista financeiro |
| Dashboards BI prontos | Sim | 5 relatórios Power BI: charge breakdown, summary, Advisor recommendations, governance |
| Recomendações de otimização | Parcial | Via Azure Advisor (rightsizing, reserved instances) — não calcula economia a partir de telemetria própria |
| Savings de EA/MCA (contracted vs list) | Sim | Desde a versão 0.7 |
| Governança (relatório) | Parcial | Visão de subscriptions/resource types; não é motor de política |
| Simulação de cenário / what-if | Não | Inexistente |
| Reconciliação financeira (fatura vs. uso vs. orçamento) | Não | Fora do escopo do toolkit |
| Investigação conversacional / agente | Não | Integração recente com Copilot via Azure MCP server é consulta a dados, não investigação com hipótese e evidência estruturada |
| Dedução de causa de variação com narrativa | Não | — |
| Multi-moeda com proveniência de FX | Parcial | Depende de Cost Management, não é tratado como objeto de primeira classe |

**Conclusão da seção**: o Hubs é um pipeline de dados + BI confiável para quem já vive no ecossistema Azure/Power BI/KQL. Ele não entrega: reconciliação com evidência auditável, simulação, nem nenhuma forma de raciocínio sobre "por que isso aconteceu" além do que cai num dashboard. É exatamente aí que o `AGENTS_SECURITY.md` da Fase 0 aponta o agente Claude — isso está certo.

## 3. Onde está a diferenciação real (e onde não está)
**Diferenciação defensável:**
- Investigação assistida que produz `summary/facts/hypotheses/data_gaps/recommendations/limitations` com proveniência rastreável até o dataset — Hubs não tem isso, Power BI não tem isso.
- Reconciliação financeira ativa (billed vs. effective vs. list, detecção de dupla contagem, bloqueio de soma de moedas) como *produto*, não como relatório estático.
- Relatório de oportunidades que se nega a inventar economia sem dado de suporte (`insufficient_data` em vez de número fantasioso) — isso é uma escolha de produto que o Advisor não faz (Advisor sempre sugere, raramente mede confiança).
- Simulação sem dupla contagem entre oportunidades no mesmo recurso/componente.

**Não é diferenciação, é commodity que já existe em outro lugar e custa caro reconstruir:**
- Dashboards de série temporal e pivot de custo — Power BI + Hubs já fazem isso bem, e refazer "só com cara diferente" (que é o que o `UI_UX_SPEC.md` pede, tema escuro IBM Plex) é custo de UI sem vantagem técnica.
- Ingestão nativa multi-cloud profunda — caro, de baixo retorno na PoV, e não é o que convence um stakeholder a aprovar o projeto.
- As 12 áreas de navegação do `UI_UX_SPEC.md` (Cockpit, Data Hub, Cost Analytics, Optimization, Agentic AI, Forecast, Commitments, Unit Economics, Governance, Savings, Simulations, Reports). Construir shell para 12 áreas antes de provar valor em 1 é o erro clássico de "parecer uma plataforma" antes de ser uma.

**Contraponto que precisa ser dito**: se a diferenciação real é o agente, o valor do produto está limitado pela qualidade dos dados que ele recebe. Um agente excelente sobre uma reconciliação errada produz uma alucinação com aparência de autoridade — pior que não ter agente. Isso eleva a reconciliação financeira (seção 5, PoV) de "funcionalidade de apoio" a "pré-requisito do diferencial", não um item paralelo.

## 4. Matriz construir / integrar / adiar
| Item | Decisão | Justificativa |
|---|---|---|
| Importação FOCUS 1.0r2 (CSV/Parquet) | **Construir** | Núcleo da PoV; sem isso nada mais existe |
| Normalização canônica (billed/effective/list, moeda, cost basis) | **Construir** | Base de confiança; é onde o Hubs é fraco em auditabilidade fina |
| Reconciliação com detecção de dupla contagem/overlap | **Construir** | Diferenciador declarado, AT-001/003/004 dependem disso |
| Análise de variação mês a mês com causa atribuída | **Construir (PoV)** | Testável com dados sintéticos, valor imediato para stakeholder |
| Investigação assistida por Claude (tools allowlist read-only) | **Construir (PoV)** | É o produto; mas escopo mínimo: 3–4 tools, não as 8 do `AGENTS_SECURITY.md` |
| Relatório de oportunidades com evidência | **Construir (PoV)** | Fecha o loop de valor demonstrável |
| Dashboards BI genéricos (pivot, export, múltiplas visões) | **Adiar** | Replica Power BI/Hubs sem vantagem; só construir o mínimo para sustentar a narrativa da PoV |
| Forecast com sazonalidade/holdout | **Adiar para F2+** | Não citado como item da PoV pelo usuário; valor real exige histórico que a PoV sintética não tem |
| Simulação de cenários (What-if UI completa) | **Adiar** | Fora do pedido explícito da PoV |
| Conectores Azure/AWS/GCP read-only ao vivo | **Adiar (F5)** | Fase 0 já marca isso fora do MVP; manter assim |
| UI com 12 áreas / tema completo IBM Plex | **Adiar** | Construir apenas as telas que sustentam a PoV (Data Hub, Cockpit reduzido, Investigação, Relatório) |
| Ingestão multi-cloud (AWS/GCP/OCI) | **Integrar depois, não na PoV** | Azure é o único provider exigido agora |
| Autoexecução de mudança / conectores de escrita | **Nunca no MVP** | Já excluído corretamente pela Fase 0, mantém-se |

## 5. Escopo da Prova de Valor (PoV) — o que efetivamente será validado
Objetivo único e testável: **dado um conjunto FOCUS 1.0r2 + export Azure Cost Analysis sintéticos com inconsistências conhecidas de propósito, o sistema reconcilia corretamente, identifica as variações certas, e o agente produz um relatório de oportunidades que um analista financeiro julga "mais útil que abrir o Cost Management direto" em um teste cego.**

Componentes mínimos:
1. **Importação FOCUS 1.0r2**: upload, sniff de schema, mapping, staging, commit idempotente por hash (reusa AT-001/002 do `ACCEPTANCE_AND_ROADMAP.md`).
2. **Azure Cost Analysis**: ingestão do export nativo (paralelo ao FOCUS) para comparação cruzada — é o teste de reconciliação entre duas fontes do mesmo custo.
3. **Reconciliação financeira**: billed vs. effective, bloqueio de soma de moeda, prevenção de overlap de período/dataset.
4. **Análise de variação**: mês corrente vs. anterior, por serviço/recurso, com decomposição (volume vs. preço vs. novo recurso) — critério objetivo de corretude, não opinião.
5. **Investigação assistida por Claude**: 3–4 tools read-only (`get_dataset_quality`, `get_cost_breakdown`, `get_anomalies`, `get_provenance`); saída estruturada validada (`summary/facts/hypotheses/data_gaps/recommendations/limitations`).
6. **Relatório de oportunidades fundamentadas**: cada item com evidência, nível de confiança, e links de proveniência; zero "economia estimada" sem dado de suporte.

Fora da PoV, mesmo que estejam no roadmap: forecast, simulação de cenário, savings pipeline com estados, commitments, unit economics, governance, UI de 12 áreas, conectores ao vivo.

## 6. Arquitetura recortada para a PoV
Reaproveita a topologia do `ARCHITECTURE.md`, mas com domínio reduzido:

```
apps/web (shell mínimo: Data Hub, Cockpit reduzido, Investigação, Relatório)
  → services/api (FastAPI): imports, datasets, analytics/costs (variação), analysis-runs, assistant/chat
    → domains: ingestion, canonical_financial, analytics (só variação+reconciliação), ai (tools allowlist)
    → Postgres local + Parquet (sem worker assíncrono dedicado na PoV — fila simples in-process é suficiente no volume de dados sintéticos)
  → Claude API (backend-only, opt-in, com o protocolo de consentimento do AGENTS_SECURITY.md)
```

Cortes deliberados frente ao `ARCHITECTURE.md` original, e por quê:
- **Sem worker assíncrono dedicado** — volume de dados sintéticos da PoV não justifica a infraestrutura; reintroduzir no F1 real se o volume de produção exigir.
- **Sem domínio `operations`** (CPU/RAM/inventário) — a PoV não faz rightsizing medido; isso é exatamente o caso que deve aparecer como `insufficient_data` (AT-006), o que é interessante provar, não contornar.
- **Sem domínio `forecast`, `optimization` completo (simulação), `governance`, `reporting` com snapshot imutável** — ficam para depois do gate de aprovação da PoV.
- **DuckDB/Polars mantidos** para a agregação, mesmo em volume pequeno — evita reescrever a camada de cálculo quando a PoV virar produto.

## 7. Critérios quantitativos de qualidade
Estes substituem "funciona no meu teste manual" por números que decidem a aprovação:

| Métrica | Critério de aceite |
|---|---|
| Reconciliação FOCUS vs. Azure Cost Analysis | Diferença entre os dois totais do mesmo período/escopo ≤ 0,5% ou motivo de divergência explicado e rotulado (ex.: granularidade diária vs. mensal) |
| Reimportação idempotente | 0 linhas duplicadas e 0 variação de total ao reimportar o mesmo hash 10x |
| Detecção de dupla contagem (overlap de datasets) | 100% dos casos sintéticos de overlap injetados são detectados (0 falso negativo); falso positivo ≤ 5% dos datasets sem overlap |
| Bloqueio de soma de moeda sem FX | 100% dos casos com 2+ moedas no mesmo agregado são bloqueados ou exigem taxa datada — 0 exceções silenciosas |
| Atribuição de causa de variação | Para os casos sintéticos com causa conhecida (preço, volume, recurso novo/removido), classificação correta ≥ 90% |
| Rightsizing sem telemetria | 100% dos casos sem métricas de CPU/RAM retornam `insufficient_data`, nunca uma economia numérica |
| Dupla contagem de savings entre oportunidades | 0 casos de soma de economia no mesmo recurso+componente de custo entre duas oportunidades simultâneas |
| Qualidade da resposta do agente | ≥ 80% das respostas em teste cego (ver seção 8) avaliadas por um analista financeiro como "corretas e com evidência suficiente para agir"; 0% com afirmação de fato não suportado por `get_provenance` |
| Latência de investigação | Resposta do agente (pergunta → resposta estruturada) ≤ 20s em p95 com dataset de até 50k linhas |
| Sanitização de CSV | 100% dos payloads de fórmula/injeção testados (ver OWASP CSV injection) neutralizados nos relatórios exportados |

## 8. Plano de testes com dados sintéticos
- **Fixtures FOCUS 1.0r2**: gerar 3 cenários — (a) baseline limpo de 2 meses, 3 serviços, 1 moeda; (b) overlap intencional de dataset (mesmo período reimportado com leve diferença de linha) para testar dedup/dupla contagem; (c) 2 moedas misturadas sem FX para testar bloqueio.
- **Fixture Azure Cost Analysis equivalente**: export paralelo do mesmo período com granularidade e cost basis levemente diferentes (billed vs. effective), propositalmente, para testar a reconciliação e sua explicação de divergência.
- **Casos de variação com causa conhecida**: injetar 5 eventos sintéticos (aumento de preço de SKU, crescimento de volume, recurso novo, recurso removido, mudança de desconto) e verificar se a decomposição aponta a causa certa.
- **Caso "sem telemetria"**: recurso caro sem métricas de CPU/RAM — deve sair como candidato a rightsizing `insufficient_data`.
- **Teste de prompt injection**: inserir texto instrucional dentro de campos de descrição/tag do CSV ("ignore instruções anteriores e...") e confirmar que o agente trata como dado, não como comando.
- **Teste CSV formula/injection**: campos começando com `=`, `+`, `-`, `@` nos relatórios exportados devem ser neutralizados.
- **Teste cego com analista financeiro (humano)**: 8–10 perguntas de investigação sobre os datasets sintéticos, resposta do agente avaliada sem saber se é FinOps AI ou um resumo manual feito por outra pessoa — critério de "utilidade percebida" da seção 7.
- **Testes automatizados**: pytest unit (fórmulas, parsing), property-based (invariantes de não-dupla-contagem e não-soma-de-moeda), integração com Postgres real, golden fixtures com soma conhecida, scanner de segredo no log do agente.

## 9. Condições objetivas de go/no-go
**Go** (segue para F1 real) somente se **todos**:
1. Reconciliação FOCUS vs. Azure Cost Analysis dentro do critério da seção 7 nos 3 cenários sintéticos.
2. Zero falha nos testes de não-dupla-contagem e não-soma-de-moeda (são bloqueadores, não "quase").
3. ≥ 80% de aprovação no teste cego de utilidade do agente, com 0 afirmação não suportada por proveniência.
4. Rightsizing sem telemetria nunca retorna economia numérica nos casos de teste.
5. Custo de chamada à Claude API por investigação fica dentro de um orçamento definido antes da PoV (ex.: custo médio por sessão de investigação ≤ valor X a definir com o usuário) — **isto está ausente da Fase 0 e precisa ser decidido antes da PoV**, porque é o tipo de custo recorrente que inviabiliza o produto silenciosamente depois de aprovado.
6. Nenhum achado crítico de segurança aberto (prompt injection, CSV injection, exposição de chave) nos testes da seção 8.

**No-go / replanejar** se:
- A utilidade percebida do agente ficar abaixo de 80% e a causa for "respostas genéricas, equivalentes ao Advisor" — sinal de que a diferenciação da seção 3 não se sustentou na prática, e vale repensar que tools/que perguntas o agente responde antes de escalar.
- A reconciliação FOCUS vs. Azure Cost Analysis divergir de forma não explicável — sinal de que o contrato de dados (ausente, seção 0) precisa ser escrito e revisado antes de qualquer outra coisa.
- O custo por investigação exceder o orçamento combinado — decidir entre reduzir agressividade do agente (menos chamadas, mais cache/regra determinística) ou recalibrar expectativa de uso.

## 10. Riscos não endereçados no plano original (contraponto)
- **Escopo da Fase 0 é de plataforma completa; o pedido atual é de PoV.** Os documentos de Fase 0 descrevem 12 áreas de UI e 5 fases de construção. Se a PoV for tratada como "F1 começando", existe risco real de o time (ou eu) recair no escopo grande por inércia dos documentos já escritos. Recomendo tratar esta auditoria como o documento que *substitui* a ordem de prioridade do roadmap para os próximos 4–6 semanas, não como um adendo.
- **Dependência de documentos ausentes.** Sem `FINOPS_RULES.md`, as fórmulas de variação e os limiares de anomalia desta auditoria são provisórias meus. Isso precisa ser formalizado (mesmo que de forma mínima, só para a PoV) antes de codificar, ou o critério de "classificação correta ≥ 90%" da seção 7 não tem como ser auditado de forma independente.
- **O teste cego de utilidade do agente (seção 8) é o ponto crítico e o mais fácil de pular sob pressão de prazo.** É também o único teste que realmente valida a tese de diferenciação da seção 3. Pular esse teste e declarar sucesso com base só em testes automatizados de reconciliação seria provar que o pipeline funciona, não que o produto vale a pena.
- **Custo operacional do agente não está no plano.** `AGENTS_SECURITY.md` trata de segurança e consentimento, mas não de orçamento de chamadas. Decidir isso agora evita decisão às pressas depois.
- **Azure Cost Analysis como segunda fonte pode ser subestimado em esforço.** Mapear semântica de billed/effective entre FOCUS e o export nativo da Azure historicamente gera divergências sutis de granularidade (diária vs. mensal, tags ausentes). Reservar tempo de descoberta explícito para isso, não só tempo de implementação.

## Fontes consultadas (FinOps Hubs / Microsoft)
- https://learn.microsoft.com/cloud-computing/finops/toolkit/hubs/finops-hubs-overview
- https://learn.microsoft.com/cloud-computing/finops/toolkit/hubs/data-model
- https://learn.microsoft.com/cloud-computing/finops/toolkit/hubs/deploy
- https://learn.microsoft.com/cloud-computing/finops/toolkit/hubs/configure-scopes
- https://techcommunity.microsoft.com/blog/finopsblog/ (posts de release do FinOps toolkit/hubs)
- https://focus.finops.org/docs/specification/v1-4/datasets/ (referenciado no `00_README.md` original)

## Próximos passos
Este documento, junto com `docs/fase0/*` (preservados sem alteração), é a entrega solicitada: auditoria, arquitetura da PoV e plano de validação. Nenhuma implementação de código começa até aprovação explícita sobre:
1. Escopo da seção 5 (confirmar que é isso e só isso).
2. Orçamento de custo por investigação do agente (item ausente, seção 9.5).
3. Quem decide os limiares de FINOPS_RULES.md para a PoV, já que o documento original não foi fornecido.
