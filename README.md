# FinOps AI — F1 (fundação e importação)

Implementação da Fase 1 conforme `docs/PLANO_EXECUCAO_F1.md` v3.1 e
`docs/CHECKLIST_GO_NOGO_F1.md`. Escopo: upload → identificação de esquema →
validação → staging → commit transacional idempotente → dataset consultável.
Nenhuma agregação, KPI, reconciliação, forecast, oportunidade ou IA nesta fase.

## Pré-requisitos
- Python 3.13+, Node 22+, PostgreSQL 16 (local, rodando em `127.0.0.1:5432`).
- Nenhuma credencial de nuvem é necessária. Nenhuma chamada à Claude API é feita em F1.

## Setup local

```bash
# 1. Banco de dados
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'SEU_PASSWORD_LOCAL';"
sudo -u postgres psql -c "CREATE DATABASE finops_ai;"
sudo -u postgres psql -c "CREATE DATABASE finops_ai_test;"

# 2. Ambiente Python
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Variáveis de ambiente (copie e preencha — nunca commitar .env real)
cp .env.example .env
# edite DATABASE_URL e TEST_DATABASE_URL com seu password local

# 4. Migrations
export DATABASE_URL="postgresql+psycopg://postgres:SEU_PASSWORD_LOCAL@127.0.0.1:5432/finops_ai"
alembic upgrade head
DATABASE_URL="postgresql+psycopg://postgres:SEU_PASSWORD_LOCAL@127.0.0.1:5432/finops_ai_test" alembic upgrade head

# 5. Fixtures sintéticas (gera packages/fixtures/data/*.csv)
cd packages/fixtures/generators && python generate_all.py && cd ../../..

# 6. Frontend
cd apps/web && npm install && cd ../..
```

## Rodando os 3 processos (localhost apenas)

```bash
# API
cd services/api
DATABASE_URL=... UPLOAD_STAGING_DIR=/caminho/absoluto/para/data/incoming \
  python -m app.main   # http://127.0.0.1:8000

# Worker (processo separado, fila persistida em tabela)
cd services/worker
DATABASE_URL=... UPLOAD_STAGING_DIR=/caminho/absoluto/para/data/incoming \
  python main.py

# SPA
cd apps/web && npm run dev   # http://127.0.0.1:5173
```

`UPLOAD_STAGING_DIR` **deve ser um caminho absoluto idêntico** para API e worker — são
processos separados e o padrão relativo (`./data/incoming`) resolve diferente conforme o
diretório de onde cada um é iniciado.

## Testes

```bash
source .venv/bin/activate
python -m pytest tests/ -m "not performance and not e2e"   # suíte rápida (~4s, 51 testes)
python -m pytest tests/performance                          # 100k linhas, ~5 medições (~70s)
# e2e requer os 3 processos acima rodando:
python -m pytest tests/e2e/test_data_hub_e2e.py
```

## Estrutura

Ver `docs/PLANO_EXECUCAO_F1.md` seção 2 para a árvore completa e a justificativa de cada
escolha de arquitetura.

## Documentos de decisão (ordem de leitura)

1. `docs/fase0/` — os 9 documentos originais da especificação (inalterados).
2. `docs/AUDITORIA_VIABILIDADE_POV.md` — auditoria de viabilidade e diferenciação (aprovada).
3. `docs/PLANO_EXECUCAO_F1.md` — plano de execução de F1 (v3.1, autorizado).
4. `docs/CHECKLIST_GO_NOGO_F1.md` — checklist de decisão para iniciar a codificação.
5. `docs/RELATORIO_ENTREGA_F1.md` — relatório de entrega desta fase.
