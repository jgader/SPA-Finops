# FinOps AI — Fase 0 | Baseline de especificação
Versão 0.1 | 14/10/2026 | Status: PROPOSTA PARA APROVAÇÃO, não sistema implementado.

## Objetivo
SPA local, com backend e Claude API, que ingere arquivos financeiros e operacionais, detecta lacunas, calcula KPIs e oportunidades, produz forecast e recomendações com evidências e prepara expansão Azure → OCI → AWS/GCP.

## Ordem de leitura
1. PRODUCT_REQUIREMENTS.md; 2. ARCHITECTURE.md; 3. DATA_CONTRACTS.md; 4. FINOPS_RULES.md; 5. AGENTS_SECURITY.md; 6. UI_UX_SPEC.md; 7. ACCEPTANCE_AND_ROADMAP.md; 8. CLAUDE_CODE_BOOTSTRAP.md.

## Decisões
- Interface em português-BR, moeda configurável e datas ISO armazenadas no backend.
- Primeiro modo local, um workspace, sem credenciais cloud, read-only.
- Dados fictícios somente no workspace DEMO, com rótulo persistente.
- FOCUS é padrão FINANCEIRO; inventário, preço de catálogo, contratos, tags e métricas operacionais requerem tabelas próprias.
- Resultados têm proveniência, período, tipo de custo, moeda, premissas e nível de confiabilidade.
- Automação de mudança REAL e conectores de cloud não fazem parte do MVP inicial.

## Documentos oficiais
- https://focus.finops.org/docs/specification/v1-4/datasets/
- https://www.finops.org/framework/
- https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-improved-exports

## Proveniência do anexo
Arquivo de referência: capacity_planning_Principal_2_FASE31.html, fornecido pelo usuário. Referência de experiência, não dependência de código.
