"""Diagnóstico de performance SQL (MySQL EXTRACTOR — não é Postgres/Prisma)."""

from __future__ import annotations

import time
from typing import Any

import pandas as pd

from app.db import get_connection, read_sql


def explain_mysql(query: str, params: tuple | None = None) -> pd.DataFrame:
    """EXPLAIN da consulta (equivalente ao EXPLAIN do Postgres)."""
    q = query.strip()
    if q.upper().startswith("SELECT"):
        q = f"EXPLAIN {q}"
    else:
        q = f"EXPLAIN {q}"
    return read_sql(q, params)


def explain_analyze_mysql(query: str, params: tuple | None = None) -> pd.DataFrame:
    """MySQL 8.0.18+: EXPLAIN ANALYZE (tempo real por etapa)."""
    q = query.strip()
    if not q.upper().startswith("EXPLAIN"):
        q = f"EXPLAIN ANALYZE {q}"
    return read_sql(q, params)


def timed_read_sql(query: str, params: tuple | None = None) -> tuple[pd.DataFrame, float]:
    t0 = time.perf_counter()
    df = read_sql(query, params)
    return df, time.perf_counter() - t0


def profile_ranking_queries(ano: int, mes: int) -> list[dict[str, Any]]:
    """Queries típicas do Ranking — rode com `python -m app.db_perf` para ver tempos."""
    from app.dates_util import month_bounds

    ini, fim = month_bounds(ano, mes)
    rows: list[dict[str, Any]] = []

    q_rank = """
        SELECT vendedor, MAX(nome) AS nome, SUM(valor_total_faturado) AS faturamento
        FROM faturamento_avinor
        WHERE data >= %s AND data < %s AND valor_total_faturado > 0 AND vendedor > 0
        GROUP BY vendedor
    """
    df, sec = timed_read_sql(q_rank, (ini, fim))
    rows.append({"nome": "ranking_mes", "segundos": round(sec, 3), "linhas": len(df)})

    try:
        ex = explain_mysql(q_rank, (ini, fim))
        rows.append({"nome": "explain_ranking_mes", "tabela": ex.to_dict()})
    except Exception as e:
        rows.append({"nome": "explain_erro", "erro": str(e)})

    return rows


if __name__ == "__main__":
    import sys

    y = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
    m = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    for row in profile_ranking_queries(y, m):
        print(row)
