# Metas Avinor

Painel gerencial único (Streamlit): acompanhamento de vendas, comparação de anos e planejamento de metas.

## Requisitos

- Python 3.11+
- Acesso **somente leitura** ao MySQL `EXTRACTOR`

## Configuração

```bash
cd MetasAvinor
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Edite .env com TEST_DB_*
```

## Executar

```bash
streamlit run streamlit_app.py
```

## Deploy (Render + Neon)

Repositório: https://github.com/VoceveGit/MetasAvinor.git

- **Render:** Web Service Python (ver `render.yaml` e `docs/DEPLOY_RENDER.md`)
- **MySQL:** `TEST_DB_*` (EXTRACTOR, leitura)
- **Neon:** `NEON_DATABASE_URL` — premissas e snapshot da grade (`sql/neon_app_state.sql`)

Local sem Neon continua usando `premissas_local.json` e `grid_snapshot_local.json`.
