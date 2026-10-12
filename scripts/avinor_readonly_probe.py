"""Read-only probe for Avinor tables. SELECT only."""
import json
import os
from decimal import Decimal
from datetime import date, datetime

import mysql.connector

TABLES = [
    "base_clientes_avinor",
    "base_pedidos_avinor",
    "deals_avinor",
    "estoque_avinor",
    "faturamento_avinor",
    "pedidos_emissao_avinor",
    "relatorios_avinor",
]


def ser(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if isinstance(o, Decimal):
        return float(o)
    if isinstance(o, bytes):
        return o.decode("utf-8", errors="replace")
    return o


def main():
    conn = mysql.connector.connect(
        host=os.environ.get("TEST_DB_HOST", "45.79.29.86"),
        port=int(os.environ.get("TEST_DB_PORT", "3306")),
        user=os.environ.get("TEST_DB_USER", "gccconsultoria"),
        password=os.environ["TEST_DB_PASSWORD"],
        database=os.environ.get("TEST_DB_NAME", "EXTRACTOR"),
        connection_timeout=30,
    )
    cur = conn.cursor(dictionary=True)
    summary = {}

    for t in TABLES:
        cur.execute(f"DESCRIBE `{t}`")
        cols = [r["Field"] for r in cur.fetchall()]
        cur.execute(f"SELECT COUNT(*) AS c FROM `{t}`")
        n = cur.fetchone()["c"]
        cur.execute(f"SELECT * FROM `{t}` LIMIT 10")
        rows = [{k: ser(v) for k, v in r.items()} for r in cur.fetchall()]
        summary[t] = {"columns": cols, "row_count": n, "sample_rows": rows}

    # Mini verifications aligned with spreadsheet logic (one vendor if possible)
    checks = {}
    try:
        cur.execute(
            """
            SELECT `Vendedor`, `Nome` AS vendedor_nome, COUNT(*) AS carteira
            FROM base_clientes_avinor
            WHERE `Situação` = 'Ativo' OR `Situação` IS NULL
            GROUP BY `Vendedor`, `Nome`
            ORDER BY carteira DESC
            LIMIT 5
            """
        )
        checks["carteira_top_vendedores"] = cur.fetchall()
    except Exception as e:
        checks["carteira_top_vendedores_error"] = str(e)

    # faturamento: sample aggregates - need column names from describe
    fat_cols = summary["faturamento_avinor"]["columns"]
    checks["faturamento_columns"] = fat_cols

    # Find date and value columns in faturamento
    date_candidates = [c for c in fat_cols if "data" in c.lower() or "emiss" in c.lower()]
    value_candidates = [c for c in fat_cols if "total" in c.lower() or "valor" in c.lower() or "fat" in c.lower()]
    checks["faturamento_date_candidates"] = date_candidates
    checks["faturamento_value_candidates"] = value_candidates

    if date_candidates and "Cliente" in fat_cols:
        dc = date_candidates[0]
        # pick a numeric total column
        vc = None
        for c in ["Valor Total", "Total", "Valor", "Vlr Total", "NFP_TOTAL_PRODUTO"]:
            if c in fat_cols:
                vc = c
                break
        if not vc:
            vc = value_candidates[0] if value_candidates else None
        if vc:
            cur.execute(
                f"""
                SELECT `Vendedor`, COUNT(DISTINCT `Cliente`) AS clientes_distintos,
                       COUNT(DISTINCT `Pedido`) AS pedidos_distintos,
                       SUM(`{vc}`) AS soma_valor
                FROM faturamento_avinor
                WHERE `{dc}` >= DATE_SUB(CURDATE(), INTERVAL 3 MONTH)
                GROUP BY `Vendedor`
                ORDER BY soma_valor DESC
                LIMIT 5
                """
            )
            checks["faturamento_3m_by_vendedor_sample"] = [
                {k: ser(v) for k, v in r.items()} for r in cur.fetchall()
            ]

    # deals for opportunities
    deal_cols = summary["deals_avinor"]["columns"]
    checks["deals_columns"] = deal_cols

    cur.close()
    conn.close()

    out_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "avinor_db_summary.json"
    )
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"tables": summary, "checks": checks}, f, ensure_ascii=False, indent=2)
    print("wrote", out_path)


if __name__ == "__main__":
    main()
