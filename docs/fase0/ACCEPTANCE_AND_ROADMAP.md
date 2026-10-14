# Critérios de aceite, QA e execução por marcos

## Gates Fase 0
G0-1: visão, personas, escopo MVP e fora de escopo aprovados.
G0-2: mapeamento de arquivos FOCUS e Azure por fixtures de exemplo; versionamento de schema.
G0-3: contratos de custo e monetização (billed/effective) revisados para não haver dupla contagem.
G0-4: fórmulas/limiares documentados, thresholds configuráveis, plano de testes definido.
G0-5: matriz do que exige telemetria vs pode ser inferido do faturamento aprovada.
G0-6: protocolo de privacidade e Claude opt-in aprovado.
G0-7: arquitetura, isolamento e limites do MVP aprovados.

## Fases de construção
**F1 Fundação e importação:** monorepo, DB migration, SPA shell, upload, identificação, mapeamento, staging, commit idempotente, testes.
**F2 Analytics e cockpit:** séries, dim drilldown, reconciliação, KPIs, estados de qualidade, dashboard.
**F3 Optimization e simulation:** anomalia, candidatos a ação, dados insuficientes, baseline/scenarios, savings pipeline.
**F4 Assistente e reports:** ferramentas seguras, consentimento, relatórios e explicação com proveniência.
**F5 Azure/OCI conectores:** apps read-only, sincronização, operação em produção autorizada separadamente.

## Critérios mensuráveis MVP
AT-001: CSV FOCUS válido é identificado, resumido, importado e reconciliado; reimport mesmo hash não duplica custos.
AT-002: CSV malformado gera rejeições por linha, campos e orientação, preserva origem e não altera base aprovada.
AT-003: 2 moedas não são somadas silenciosamente; a interface bloqueia ou exige taxa de câmbio datada.
AT-004: datasets superpostos em mesmo período não dobram total faturado.
AT-005: dashboard confere com soma manual das fixtures e indica cost basis.
AT-006: sem métricas CPU/RAM, rightsizing aparece como 'insufficient_data', nunca economia comprovada.
AT-007: forecast tem método identificável, horizonte, erro histórico quando disponível e aviso em história curta.
AT-008: oportunidades no mesmo recurso e componente de custo não somam economia duas vezes no cenário.
AT-009: Claude desligado: importação, analytics e simulador continuam funcionando.
AT-010: Claude ligado: resposta referencia outputs das ferramentas, não afirma acesso à cloud ou fatos não carregados.
AT-011: UI mantém navegação, filtro global, tabela e card responsivos; indicadores não dependem só de cor.
AT-012: usuário consegue exportar diagnóstico com dataset hash, status, timestamp, warnings, versão de regras.
AT-013: não existe nenhum endpoint de alterar VM ou remover storage na F1-F4.

## Testes
pytest unit (fórmulas e parse), property tests (invariantes e não dupla contagem), integração DB/import, fixture golden com somas conhecidas, E2E Playwright, scanner secrets, teste de prompt injection e CSV injection, teste de performance e de limites.

## Critério de aceite operacional
Só declarar módulo 'pronto' com screenshots funcionais, resultado dos testes automatizados, riscos residuais, dados mínimos e instruções de execução local. Não contar um mock como engine em produção.
