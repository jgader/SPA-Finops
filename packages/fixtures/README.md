# Fixtures sintéticas — FinOps AI F1

Todos os arquivos em `data/` são **sintéticos**, gerados programaticamente pelos scripts em
`generators/`. Nenhum dado real de organização, subscription, conta ou recurso aparece aqui
— nomes como `demo-sub-0001`, `demo-vm-003` são fictícios por construção.

Para regenerar (determinístico, mesma saída sempre):

```
python packages/fixtures/generators/generate_all.py
```

| Arquivo | Propósito | Critério de aceite relacionado |
|---|---|---|
| `focus_clean_baseline.csv` | Caminho feliz: 2 meses, múltiplos serviços, 1 moeda | AT-001 |
| `focus_malformed.csv` | Linhas com erro: campo ausente, decimal inválido, moeda inválida, categoria inválida, duplicata exata | AT-002, seção 7-bis (bloqueio total) |
| `focus_overlap_reimport.csv` | Cópia byte-a-byte de `focus_clean_baseline.csv` | AT-001 — dedup por hash idêntico |
| `focus_same_period_different_hash.csv` | Mesmo scope+period do baseline, 1 valor diferente (hash diferente) | AT-004 — detecção de sobreposição financeira |
| `focus_multicurrency.csv` | BRL e USD na mesma importação, sem FX | AT-003 — captura correta, nunca coagida |
| `focus_mixed_granularity.csv` | Linhas com uso diário e uso mensal no mesmo dataset | granularity=mixed (ajuste 3) |
| `focus_perf_100k.csv` | 100.000 linhas sintéticas | Meta de performance (seção 13 do plano) |
| `azure_cost_analysis_equivalent.csv` | Export nativo Azure Cost Analysis, billing_account distinto do baseline | Adapter concreto 2 — importação correta, sem overlap |
