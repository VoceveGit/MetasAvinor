# Deploy no Render + Neon

## Repositório

- GitHub: [VoceveGit/MetasAvinor](https://github.com/VoceveGit/MetasAvinor.git)
- Commits: identidade global `azure` / `azure@vocevecomunicacao.com.br`

## 1. Neon (estado da app)

1. Crie um projeto Postgres no [Neon](https://neon.tech).
2. No SQL Editor, execute `sql/neon_app_state.sql` (tabela + funções `metas_kv_*`).
3. Copie a connection string (`postgresql://...`) para `NEON_DATABASE_URL`.

Premissas e snapshot da grade passam a ficar no Neon (não no disco do Render).
Na primeira subida com Neon vazio, se existir JSON local na máquina de dev, a migração automática copia uma vez.

## 2. Render (Web Service)

1. [Render Dashboard](https://dashboard.render.com) → **New** → **Web Service** → conectar `VoceveGit/MetasAvinor`.
2. **Runtime:** Python 3.11.
3. **Build:** `pip install -r requirements.txt`
4. **Start:**
   ```bash
   streamlit run streamlit_app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true --browser.gatherUsageStats=false
   ```
5. **Environment variables** (Secret):
   - `TEST_DB_*` — MySQL EXTRACTOR (somente leitura)
   - `NEON_DATABASE_URL` — Postgres Neon

Ou importe o `render.yaml` como Blueprint.

## 3. Planilha de rotas

Copie `ROTAS AVINOR.xlsx` para `data/ROTAS AVINOR.xlsx` e faça commit (o `.gitignore` ignora outros `.xlsx`, mas permite este arquivo).

Sem ela, a grade do Início quebra com `FileNotFoundError`. Upload pelo app grava no disco do Render e **some no próximo deploy** — prefira versionar em `data/`.

## 4. MySQL EXTRACTOR

O Render precisa **alcançar** o host MySQL (firewall / allowlist de IP).
Sem isso o painel sobe, mas as consultas ERP falham.

## 5. Cuidados (plano free)

- Cold start após ~15 min sem uso.
- Evite consultas pesadas sem cache; use índices em `sql/mysql_indexes_recommended.sql` no MySQL.
- `connection_limit` baixo no MySQL se necessário.
