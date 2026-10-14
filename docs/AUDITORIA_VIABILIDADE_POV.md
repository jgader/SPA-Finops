# Auditoria de viabilidade e diferenciação — FinOps AI vs. Microsoft FinOps Hubs
Versão 0.2 | 14/10/2026 | Status: ANÁLISE PARA DECISÃO — nenhum código de produto foi escrito nesta etapa.

> Escopo deste documento: responder "vale a pena construir isso, e o quê exatamente, antes de qualquer outra coisa", agora com os **9 documentos da Fase 0** lidos integralmente (o ZIP `FinOps_AI_Fase0_Especificacao.zip` continha os 4 que faltavam na v0.1: `PRODUCT_REQUIREMENTS.md`, `DATA_CONTRACTS.md`, `FINOPS_RULES.md`, `CLAUDE_CODE_BOOTSTRAP.md`). Os documentos originais não foram alterados — permanecem em `docs/fase0/` exatamente como recebidos.

## Nota de revisão (v0.1 → v0.2)
A v0.1 foi escrita com uma lacuna real: faltavam os documentos que definem fórmulas, contratos de dados e o catálogo funcional rastreável. Isso mudou três conclusões da v0.1, listadas aqui antes do resto para não ficarem perdidas no meio do texto:
1. **As fórmulas e os limiares já existem** (`FINOPS_RULES.md`). A v0.1 dizia que os números das seções de critério de qualidade eram "propostos por mim, não extraídos de contrato aprovado" — isso não é mais verdade para a maior parte deles. Onde ainda invento algo (ex.: tamanho de fixture), digo explicitamente.
2. **Há um conflito de versão FOCUS que não existia na minha análise anterior porque eu não tinha o dado para ver o conflito.** Ver seção 1, Problema confirmado P-1.
3. **O usuário pediu agora explicitamente que a PoV preserve uma SPA mínima funcional** inspirada no Capacity Planning. Isso contradiz minha recomendação da v0.1 de adiar toda UI — corrijo isso na seção 6.

Da v0.1 eu mantenho, sem alteração, a tese central: não vale reconstruir o FinOps Hubs, e a diferenciação está na reconciliação com evidência + investigação assistida + relatório de oportunidades fundamentadas — isso não dependia dos 4 documentos que faltavam.

---

## Como ler este documento
Cada achado é marcado como:
- **[CONFIRMADO]** — está escrito, textualmente ou por contradição direta, em algum dos 9 documentos.
- **[HIPÓTESE]** — minha interpretação ou preenchimento de lacuna; pode estar errada, preciso de confirmação.
- **[RECOMENDAÇÃO]** — o que eu faria, dado o confirmado e a hipótese.
- **[DECISÃO PENDENTE]** — não decido isto sozinho; listado também, consolidado, na seção 9.

## 1. Problemas confirmados nos documentos (não são opinião minha)

**P-1. Conflito de versão FOCUS — [CONFIRMADO]**
O pedido original do usuário para a PoV especifica "importação FOCUS 1.0r2". O `DATA_CONTRACTS.md` diz: *"Base de referência FOCUS 1.4 ... NUNCA presumir que qualquer provedor emite 1.4 só porque ela é publicada."* Já a pesquisa de mercado que fiz sobre o Azure Cost Management (fontes na v0.1) mostra que a Azure exporta nativamente **FOCUS 1.0**, com um backport de campos do 1.2, e suporte pleno ao 1.2 é "release futuro" — 1.4 não é mencionado em nenhuma documentação pública da Azure até o momento desta auditoria. Ou seja, há três referências de versão diferentes em jogo: o pedido do usuário (1.0r2), o baseline do contrato de dados (1.4), e o que a Azure realmente envia hoje (1.0 + backport parcial de 1.2). O próprio `DATA_CONTRACTS.md` já antecipa isso ("adaptadores aceitam versões detectadas... registram o esquema observado"), o que é a postura certa de engenharia, mas não resolve qual versão a PoV deve *assumir como padrão* para os fixtures sintéticos e para os testes de aceite.
[DECISÃO PENDENTE-1] Vou propor um encaminhamento na seção 9.

**P-2. `CLAUDE_CODE_BOOTSTRAP.md` proíbe IA na primeira entrega, a PoV pede o agente desde o início — [CONFIRMADO]**
O bootstrap original é explícito: *"OBJETIVO DESTA TAREFA: implementar SOMENTE Fase 1, fundação e importação local... A Fase 1 deve funcionar com IA desabilitada."* e regra 9: *"Não avançar Fase 2 sem aprovação explícita."* A sequência original é F1 (fundação/importação) → F2 (analytics/cockpit) → F3 (optimization/simulation) → F4 (assistente/reports). O agente Claude só entra na F4.
O pedido da PoV que o usuário já validou junta, numa única entrega, importação (F1) + reconciliação/variação (F2) + investigação por Claude (F4) — isto é, atravessa três fases do roadmap original de uma vez. Isso não é necessariamente errado (uma PoV pode ser transversal por definição), mas é uma divergência real do documento de bootstrap que precisa ser nomeada, não silenciada. Se a PoV falhar no critério de utilidade do agente (seção 7), não dá para saber se foi porque o agente é ruim ou porque a base de F1/F2 ainda não estava madura o suficiente para alimentá-lo bem — a sequência em fases do bootstrap existe justamente para evitar essa ambiguidade de diagnóstico.
[DECISÃO PENDENTE-2]

**P-3. Pedido de UI mínima contradiz a recomendação de "adiar toda UI" da v0.1 — [CONFIRMADO, resolvido nesta revisão]**
O usuário agora pede explicitamente: *"a PoV deverá preservar uma interface SPA mínima e funcional inspirada no Capacity Planning original."* Isso é compatível com o próprio `UI_UX_SPEC.md`, que já previa isso: *"No MVP, áreas P2+ podem aparecer apenas em roadmap, não fingir funcionalidade."* — ou seja, o documento original nunca pediu as 12 áreas completas no MVP, só a navegação/estrutura delas visível, com a maioria em estado "em desenvolvimento" (confirmado também no `PRODUCT_REQUIREMENTS.md`: *"No MVP, algumas aparecem como áreas com estado 'Em desenvolvimento' em vez de telas falsas."*). Minha recomendação da v0.1 de "adiar toda UI" estava mais radical do que o próprio plano original pedia. Corrijo na seção 6.

**P-4. Não existe benchmark de performance definido — [CONFIRMADO]**
`PRODUCT_REQUIREMENTS.md`, requisito não funcional: *"performance de 100k linhas em fixture de referência a definir"* — o próprio documento marca isso como pendente. Não é uma lacuna que eu detectei; é uma lacuna que o documento confirma ter.
[DECISÃO PENDENTE-3]

**P-5. Critério de confiança tem 4 estados, não 2 como a v0.1 assumiu — [CONFIRMADO]**
A v0.1 tratava a saída do rightsizing sem telemetria como binária (`insufficient_data` vs. número). O `FINOPS_RULES.md` define 4 estados formais: `verified` (cálculo auditado, fontes adequadas), `estimated` (simulação com premissas), `insufficient` (dados críticos ausentes), `blocked` (conflito/regra de segurança) — e exige que o nível de confiança "nunca seja reduzido a um score sem explicar componentes" (cobertura, recência, evidência, criticidade). Isso é mais rico e mais exigente do que a v0.1 testava. Atualizado na seção 7.

## 2. O que mudou na auditoria de diferenciação (seção 2–3 da v0.1)
Nada muda na comparação com o FinOps Hubs em si — os 4 documentos novos são internos ao FinOps AI, não alteram o que o Hubs faz ou não faz. O que muda é que agora tenho o **catálogo funcional rastreável** (`PRODUCT_REQUIREMENTS.md`, IDs FR-001 a FR-020) para ancorar a matriz de prioridade em vez de categorias genéricas. Rever seção 4.

Confirmação adicional de diferenciação: `FINOPS_RULES.md` formaliza a prevenção de dupla contagem como regra de engine (*"agrupar recomendações pelo mesmo recurso, mesmo componente financeiro e mesmo período... não somar diretamente cada oportunidade"*) e define `realized_savings` como contrafactual ajustável, nunca o valor estimado da oportunidade. Isso é uma disciplina que nenhuma ferramenta do Hubs/Advisor impõe — reforça a tese da seção 3 da v0.1, não a altera.

## 3. Matriz construir / integrar / adiar — revisada com IDs rastreáveis
| FR (Requisitos) | Item | Decisão PoV | Observação |
|---|---|---|---|
| FR-001, FR-002, FR-003, FR-004 | Data Hub: upload, detecção FOCUS, pré-validação, staging/commit idempotente | **Construir** | Núcleo; usar o modelo `import_batch`/`dataset`/`cost_usage` de `DATA_CONTRACTS.md` tal como especificado |
| FR-006, FR-007 | Analytics: slice/dice básico e seleção de cost basis (billed/effective/list) | **Construir (mínimo)** | Só o necessário para sustentar reconciliação e variação, não o módulo completo |
| — (reconciliação é regra, não FR explícito) | Reconciliação FOCUS vs. Azure Cost Analysis, anti-dupla-contagem, anti-soma-de-moeda | **Construir** | Aplicar regras de `DATA_CONTRACTS.md` (Decimal, ISO 4217, não somar actual+amortized sobreposto) |
| FR-009 (parcial) | Análise de variação com causa atribuída | **Construir (PoV, versão simplificada)** | `FINOPS_RULES.md` define anomalia via MAD com mínimo de 28 pontos — **a PoV sintética pode não ter histórico suficiente**; ver Decisão Pendente-4 |
| FR-014 | Chat/investigação assistida por Claude (read-only) | **Construir (PoV, 3–4 tools)** | P1 no catálogo original, mas é o核 da tese de diferenciação — ver P-2 sobre risco de sequenciamento |
| FR-013 | Relatório exportável com proveniência e ressalvas | **Construir (mínimo: PDF/JSON, não os três formatos)** | — |
| FR-005 | Cockpit completo (KPIs, forecast, savings por estado) | **Construir só o recorte que sustenta a narrativa** (gasto, variação, oportunidades) | Forecast e savings pipeline completos ficam fora |
| FR-008 | Forecast com baseline sazonal | **Adiar** | Confirma decisão da v0.1; `FINOPS_RULES.md` exige backtesting de janelas completas, que a PoV sintética dificilmente sustenta com rigor |
| FR-010 | Optimization (idle VM, rightsizing, disco órfão, scheduling, storage tier) | **Construir 1 caso apenas, como prova do padrão `insufficient`/`verified`** | Ver seção 6; os outros tipos ficam de fora, mas o *padrão* de confiança deve ser demonstrado |
| FR-011 | Simulação what-if | **Adiar** | Confirma v0.1 |
| FR-012 | Savings pipeline com estados | **Adiar** | Confirma v0.1 |
| FR-015 a FR-020 (Governança, Compromissos, Unit economics, Conectores, Aprovações, Multiusuário) | — | **Adiar (fora do MVP pelo próprio documento original)** | Já estava fora do escopo do próprio `PRODUCT_REQUIREMENTS.md` para o MVP, quanto mais para a PoV |

## 4. Esquema de dados da PoV — agora specificado, não genérico
`DATA_CONTRACTS.md` já define o modelo lógico mínimo. A PoV usa um subconjunto direto dele, sem inventar tabelas novas:
`import_batch`, `dataset`, `cost_usage` (com `billed_cost`/`effective_cost`/`list_cost`/`contracted_cost` separados, `raw_ref` preservando o dado bruto), `analysis_run`. `resource`, `resource_metric`, `budget`, `scenario`, `opportunity`, `savings_validation` entram apenas na medida do caso único de otimização da seção 6 — não é necessário instanciar o modelo de `scenario`/`savings_validation` completo para a PoV.

**[HIPÓTESE]** Assumo que o fixture sintético da PoV pode representar `cost_usage` sem popular `resource_metric` em volume — exceto para o único caso de otimização demonstrado, onde preciso de métricas suficientes para diferenciar `verified`/`estimated`/`insufficient` de forma didática.

## 5. Critérios quantitativos — agora alinhados às fórmulas reais de `FINOPS_RULES.md`
Esta tabela substitui a da v0.1, que tinha números propostos por mim sem base documental.

| Métrica | Fórmula/regra de origem | Critério de aceite da PoV |
|---|---|---|
| Reconciliação FOCUS vs. Azure Cost Analysis | `total_cost = SUM(cost_value)` por cost_basis único, período e moeda | Diferença ≤ 0,5% nos cenários sem divergência proposital; divergência proposital deve ser explicada e rotulada |
| Não dupla contagem entre datasets sobrepostos | `DATA_CONTRACTS.md`: "evitar duplicidade entre actual e amortized ou datasets sobrepostos" | 0 falso negativo nos casos de overlap injetados; falso positivo ≤ 5% |
| Bloqueio de soma cross-currency | `DATA_CONTRACTS.md`: moeda ISO 4217, nunca somar sem taxa e data | 100% dos casos com 2+ moedas bloqueados ou exigindo FX datado |
| Atribuição de causa de variação | Decomposição local (preço/volume/novo recurso) — **não há fórmula explícita em `FINOPS_RULES.md` para "causa de variação"**, só `budget_variance = actual - budget` | [HIPÓTESE] proponho ≥ 90% de classificação correta nos 5 casos sintéticos injetados; **[DECISÃO PENDENTE-5]**: confirmar se a decomposição por causa é aceitável como extensão não especificada ou se precisa ser formalizada em `FINOPS_RULES.md` antes |
| Anomalias | MAD sobre série diária homogênea, mínimo 28 pontos recomendado, impacto monetário mínimo + fator relativo | Ver Decisão Pendente-4: PoV sintética provavelmente não atinge 28 pontos por série; se não atingir, o sistema deve marcar explicitamente "baixa confiança" (exigido pelo próprio `FINOPS_RULES.md`: *"em histórico curto, usar regras simples e qualificar como baixa confiança"*), não pode se omitir |
| Rightsizing sem telemetria suficiente | Confiança: `insufficient` (dados críticos ausentes) | 100% dos casos sem CPU/memória suficiente retornam `insufficient`, nunca `verified`/`estimated` |
| Dupla contagem de savings | Regra: agrupar por recurso + componente financeiro + período; não somar direto | 0 casos de soma de economia no mesmo grupo |
| Qualidade da investigação do agente | `AGENTS_SECURITY.md`: saída `summary/facts/hypotheses/data_gaps/recommendations/limitations` validada; erro de validação impede publicação | ≥ 80% aprovação em teste cego (ver seção 7); 0% de afirmação sem `get_provenance` |
| Performance de importação | `PRODUCT_REQUIREMENTS.md`: "100k linhas... a definir" | [HIPÓTESE, pendente confirmação] proponho 50k linhas como meta mínima da PoV (metade do volume de referência do MVP, compatível com dado sintético), não 100k — ver Decisão Pendente-3 |
| Custo por investigação do agente | Não definido em nenhum dos 9 documentos | [DECISÃO PENDENTE] mantém-se aberta da v0.1 — ver seção 9 |

## 6. UI mínima da PoV — correção da v0.1
A v0.1 recomendava adiar toda UI. Corrigido: a PoV constrói uma SPA mínima mas **real** (não mock), com:
- Shell com tema escuro/tokens do `UI_UX_SPEC.md` (cores, tipografia IBM Plex) e a barra de navegação com as 12 áreas visíveis, mas só 4 funcionais (Data Hub, Cockpit, uma versão reduzida de Optimization com o único caso de otimização da seção 3, Assistant) — as demais aparecem como "Em desenvolvimento", exatamente como `PRODUCT_REQUIREMENTS.md` e `UI_UX_SPEC.md` já pediam para o MVP.
- Filtro global de período/provider/moeda/cost basis do header, mesmo que com poucas opções reais na PoV — é parte do contrato de UX, não decorativo.
- Nenhuma tela com números inventados: `CLAUDE_CODE_BOOTSTRAP.md` é explícito — *"Não gere dashboards com números inventados... mostrar empty state e opção de carregar conjunto DEMO explicitamente sinalizado."* Isso vale igualmente para a PoV.

Isso é mais trabalho de frontend do que a v0.1 estimava, mas é proporcional ao que os documentos originais já pediam para qualquer MVP — não é uma ampliação de escopo, é uma correção da minha leitura anterior.

## 7. Plano de testes — mantido da v0.1, com 2 adições
Além do que já estava na v0.1 (fixtures de reconciliação, overlap, moeda, causa de variação, caso sem telemetria, prompt injection, CSV injection, teste cego de utilidade):
- **Teste de estado de confiança completo**: cada resultado de oportunidade/KPI deve aparecer com um dos 4 estados (`verified/estimated/insufficient/blocked`) e a explicação de componentes exigida por `FINOPS_RULES.md` — testar que a UI nunca usa só cor para indicar isso (exigência de acessibilidade do `UI_UX_SPEC.md`, AT-011).
- **Teste de série curta para anomalia**: confirmar que, com menos de 28 pontos, o sistema rotula "baixa confiança" em vez de omitir ou tratar como anomalia confirmada.

## 8. Riscos adicionais identificados nesta revisão
- **P-1 (versão FOCUS) é um risco de retrabalho real**: se a PoV for construída assumindo FOCUS 1.0r2 e o contrato de dados for formalizado depois em 1.4, campos podem não ter equivalência direta (FOCUS evolui campos entre versões). Resolver a decisão pendente-1 antes de escrever o parser, não depois.
- **P-2 (sequenciamento F1→F4 comprimido na PoV) é um risco de diagnóstico, não de engenharia**: se o teste cego de utilidade do agente (critério de go/no-go da v0.1) falhar, vai ser preciso distinguir "o agente é fraco" de "a base de dados da PoV é fraca porque pulamos a maturação de F1/F2". Recomendo registrar esse risco explicitamente no relatório de resultado da PoV, não só no critério de entrada.
- **Risco de escopo da UI mínima**: "mínima e funcional" pode ser lido de forma elástica. Defino explicitamente na seção 6 o que entendo por mínima (4 de 12 áreas funcionais) — se não for isso que o usuário tem em mente, é melhor alinhar agora.

## 9. Decisões pendentes — consolidado (quem decide é o usuário, não eu)
1. **Versão FOCUS da PoV**: seguir o pedido original (1.0r2, compatível com o que a Azure exporta hoje) e tratar 1.4 como alvo de contrato futuro quando o produto for alem da PoV; ou formalizar 1.4 desde já e aceitar que o fixture sintético simule campos que a Azure não exporta nativamente ainda. **Minha recomendação**: 1.0r2 agora — é o que vai casar com o Azure Cost Analysis real na reconciliação, que é o ponto central da PoV. Mas é decisão do usuário.
2. **Sequenciamento F1→F4 comprimido na PoV**: aceitar o atravessamento de fases (já implícito na aprovação anterior do usuário) com o risco de diagnóstico nomeado na seção 8, ou exigir que a reconciliação/variação (F1/F2) seja validada isoladamente primeiro, com o agente entrando só numa segunda rodada da PoV. **Minha recomendação**: manter o atravessamento (é mais rápido chegar à resposta que importa: "o agente agrega valor?"), mas registrar formalmente o risco de diagnóstico misto no critério de aceite.
3. **Meta de performance da PoV**: 50k linhas (minha proposta) em vez dos 100k do MVP completo, ou outro número. Documento original marca isso como "a definir" — não há resposta certa pré-existente.
4. **Volume mínimo de série temporal para anomalia (28 pontos)**: a PoV sintética vai gerar séries com esse comprimento mínimo, ou vai assumir desde já o modo "baixa confiança" como caminho principal de teste? Isso muda o desenho do fixture.
5. **Decomposição de causa de variação**: formalizar a fórmula em `FINOPS_RULES.md` antes da PoV (mais rigor, mais atraso) ou tratar como extensão não especificada só para a PoV, documentada separadamente e submetida a revisão depois. 
6. **Orçamento de custo por investigação do agente Claude**: segue aberta desde a v0.1 — nenhum dos 9 documentos define isso.
7. **Escopo exato da "SPA mínima e funcional"**: confirmar se a leitura da seção 6 (4 áreas funcionais de 12, as demais em "Em desenvolvimento") corresponde ao que o usuário tem em mente.

## Fontes externas consultadas (mantidas da v0.1)
- https://learn.microsoft.com/cloud-computing/finops/toolkit/hubs/finops-hubs-overview
- https://learn.microsoft.com/cloud-computing/finops/toolkit/hubs/data-model
- https://learn.microsoft.com/cloud-computing/finops/toolkit/hubs/deploy
- https://learn.microsoft.com/cloud-computing/finops/toolkit/hubs/configure-scopes
- https://techcommunity.microsoft.com/blog/finopsblog/
- https://focus.finops.org/docs/specification/v1-4/datasets/

## Próximos passos
Nenhuma implementação começa até as 7 decisões pendentes da seção 9 serem resolvidas (mesmo que a resposta a algumas seja "aceito a sua recomendação, siga"). Recomendo respondê-las em bloco numa única rodada, para eu já sair com o plano de arquivos (próxima entrega natural, conforme `CLAUDE_CODE_BOOTSTRAP.md`: árvore do repositório, diagrama de componentes, migrations, contratos de endpoint) alinhado em vez de iterar decisão por decisão.
