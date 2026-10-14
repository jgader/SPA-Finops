# Agentic FinOps e segurança

## Objetivo
Claude interpreta artefatos e análises já validados, explica variações, pede dados faltantes, compara hipóteses e prepara sumários. NÃO calcula o ledger, NÃO aprova alterações, NÃO inventa saving, NÃO emite comando cloud no MVP.

## Ferramentas autorizadas ao agente (read-only)
`get_dataset_quality(dataset_id)`, `get_cost_breakdown(period,dimensions,filters,cost_basis)`, `get_anomalies(analysis_run_id)`, `get_opportunity(id)`, `get_forecast(scope)`, `get_provenance(metric_id)`, `simulate_scenario(input)` (retorno virtual, não altera baseline), `get_missing_data(scope)`.

## Pipeline
Pergunta → classificação de intenção → verificação de autorização/consentimento → chamada de tools allowlist → respostas com IDs e versão dos resultados → resposta estruturada com fonte, premissas e alertas → log local. Se não houver dados, responder 'não é possível concluir' com checklist de arquivos necessários.

## Controles de dados
- Local-only por padrão. Ao ativar Claude API, exibir aviso sobre envio de dados a serviço externo, resumo dos campos e opção de não enviar linhas brutas.
- Preferir fornecer agregados e dados minimizados à API; mascarar identificadores sensíveis conforme configuração.
- Chave em variável de ambiente no backend ou secret store local, nunca em JS, git ou export.
- Sanitizar CSV como dado, não executar fórmulas ou HTML; proteção CSV formula injection nos relatórios.
- Defesa contra prompt injection contida em dados importados (dados não são instruções).
- Timeouts, limites por chamada, cotas, circuit breaker, audit log e fallback sem IA.
- Endpoint API localhost por padrão, CORS explícito, uploads limitados; cuidado com serviço local exposto na rede.

## Autoexecução (fora do MVP)
Somente com identidades de menor privilégio, separação de leitura/escrita, aprovação humana, plano de mudança, dry-run, janela de manutenção, rollback, logs imutáveis, limites por conta/projeto, segregação de deveres e proteção de produção.

## Prompts e saídas
Saída em JSON validado para parecer: `summary`, `facts[{id,value,source}]`, `hypotheses`, `data_gaps`, `recommendations`, `limitations`. Erro de validação deve impedir publicação da resposta como análise verificada.
