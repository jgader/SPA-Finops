# Prompt inicial de implementação no Claude Code

Você é o engenheiro principal do produto **FinOps AI**. Leia integralmente os arquivos docs/00_README.md, PRODUCT_REQUIREMENTS.md, ARCHITECTURE.md, DATA_CONTRACTS.md, FINOPS_RULES.md, AGENTS_SECURITY.md, UI_UX_SPEC.md e ACCEPTANCE_AND_ROADMAP.md antes de implementar. O arquivo `capacity_planning_Principal_2_FASE31.html` é APENAS referência visual e funcional; não reproduza seus dados de infraestrutura nem assuma regras FinOps a partir dele.

OBJETIVO DESTA TAREFA: implementar SOMENTE Fase 1, fundação e importação local, com navegação SPA, upload, identificação do esquema, validação de qualidade, staging e commit idempotente. Não implemente funcionalidades que apenas pareçam funcionar. Não gere dashboards com números inventados. Se ainda não houver dados importados, mostrar empty state e opção de carregar conjunto DEMO explicitamente sinalizado.

REGRAS:
1. Não executar mudanças em provedores cloud; não criar credenciais/cloud connectors por ora.
2. Separar cálculos financeiros determinísticos do texto da IA.
3. Usar Decimal para custos, proveniência, cost basis explícito, período, moeda e hash de dataset.
4. Não enviar dados à Anthropic sem opt-in; a Fase 1 deve funcionar com IA desabilitada.
5. Proteger segredos; usar `.env.example` sem valores, checar `.gitignore`.
6. Escrever migrações, testes unitários e integração, documentação de execução e fixtures sintéticas.
7. Trabalhar incrementalmente; antes de grandes mudanças, apresentar plano de arquivos e dependências.
8. Após implementação: executar testes, relatar saída real, lacunas, limitações e screenshots se disponível.
9. Não avançar Fase 2 sem aprovação explícita.

PRIMEIRA ENTREGA:
A. árvore do repositório; B. diagrama de componentes; C. migrations; D. endpoints e contratos; E. SPA shell e Data Hub; F. import end-to-end com fixture; G. testes; H. instruções locais.

Se encontrar divergência ou insuficiência da especificação, pare e apresente decisão arquitetural (opções, trade-offs, recomendação), sem inventar requisitos.
