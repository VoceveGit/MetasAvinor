# Performance (MetasAvinor)

Stack: **Python + Streamlit + MySQL** (`read_sql` / `pandas`). Não usa Prisma nem Postgres.

## 1. Descobrir gargalo

```bash
cd MetasAvinor
python -m app.db_perf 2026 10
```

Ou no MySQL Workbench, na query de `load_ranking_periodo`:

```sql
EXPLAIN ANALYZE
SELECT vendedor, SUM(valor_total_faturado) ...
FROM faturamento_avinor
WHERE data >= '2026-10-01' AND data < '2026-11-01'
GROUP BY vendedor;
```

- **type = ALL** + muitas linhas → falta índice (`sql/mysql_indexes_recommended.sql`).
- Tempo alto no Streamlit com SQL rápido → rerun / HTML dos cards / `load_vendedor_grid_row` em loop (use snapshot da grade).

## 2. Já feito no app

- `@st.cache_data(ttl=300)` nas consultas pesadas em `app/data.py`.
- Tops do ranking em **batch** (`load_tops_ranking_batch`).
- Grade no ranking via **snapshot** quando existe.
- **Aplicar ritmo** para não recarregar cards a cada clique no calendário.

## 3. Próximos passos (se ainda lento)

- Criar índices do arquivo SQL no banco de leitura.
- Tabela resumo mensal por vendedor (job noturno) se o EXTRACTOR for enorme.
- Não marcar tops nos cards se não precisar.
