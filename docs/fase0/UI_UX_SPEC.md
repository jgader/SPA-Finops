# UX/UI — inspiração Capacity Planning FASE31

## Observado no anexo
Tema escuro com CSS vars `--bg #0d0f14`, `--surface #161921`, `--card #1c2030`, `--accent #4f7ef7`, `--accent2 #7c5de8`, verde/âmbar/vermelho para estados; fontes IBM Plex Sans e IBM Plex Mono; header com KPIs, navegação por tabs e subtabs; tabela com search/filtro/ordenação; cards; modais; gráficos Chart.js; configuração de thresholds; save/load JSON; histórico e forecast; simulação HA. Referência funcional, sem reutilização automática de código.

## Navegação alvo
Sidebar ou barra horizontal desktop com 12 áreas: Cockpit, Data Hub, Cost Analytics, Optimization, Agentic AI, Forecast, Commitments, Unit Economics, Governance, Savings, Simulations, Reports. No MVP, áreas P2+ podem aparecer apenas em roadmap, não fingir funcionalidade.

## Shell
Header: logo FinOps AI, workspace, última atualização, base de custos, status do processamento, botão importar, acesso ao assistente. Filtro global: período, provider, account, projeto, moeda, cost basis. Adicionar topo de 'Dados de demonstração' no workspace demo.

## Páginas MVP
**Data Hub:** drag-drop, arquivos recentes, preview, schema detection, mapping editável, erros por severidade, modal de commit.
**Cockpit:** gastos mês, variação vs mês anterior, forecast, oportunidades, realized savings (somente se medido), custo alocado, distribuição, séries, drilldowns.
**Cost Analytics:** tabela por recurso/serviço, pivot, filtros, comparação de períodos, export.
**Optimization:** lista evidenciável com prioridade, economia e risco, ficha detalhada da oportunidade, ações revisão/descartar.
**Forecast:** histórico vs cenário projetado, intervalo se justificável, seleção de baseline, sazonalidade, budgets.
**Simulations:** hipóteses editáveis, diff antes/depois, prevenção dupla contagem, custo total e premissas.
**Savings:** pipeline de estados com histórico; não usar progresso artificial.
**Assistant:** chat com referências internas e modal de consentimento para IA externa.
**Settings:** dados locais, moeda, regras, threshold, configuração IA, privacidade, export/import config.

## Acessibilidade
Cards e badges não depender apenas de cor; explicação hover/click para cada KPI; datas/valores pt-BR visuais; carregamento, erro e vazio distintos; navegação teclado; tabela ampla com scroll sem quebrar cabeçalhos.

## Wireframe descritivo
```
[FinOps AI] [Workspace] [Provider] [Período] [Base: Effective]   [Importar]
[Tabs: Cockpit|Dados|Custos|Otimização|Forecast|Simulação|Savings|IA|Config]
[Gasto] [Δ mês] [Forecast] [Oport. verificadas] [Atribuição]
[Gráfico custo × previsão.......................................]
[Top serviços................] [Oportunidades por categoria.....]
[Tabela: Recurso | Custo | Tendência | Recomendação | Evidência]
```
