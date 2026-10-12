import os
import mysql.connector

conn = mysql.connector.connect(
    host=os.environ.get("TEST_DB_HOST", "45.79.29.86"),
    port=int(os.environ.get("TEST_DB_PORT", "3306")),
    user=os.environ.get("TEST_DB_USER", "gccconsultoria"),
    password=os.environ["TEST_DB_PASSWORD"],
    database=os.environ.get("TEST_DB_NAME", "EXTRACTOR"),
)
cur = conn.cursor(dictionary=True)

for t, col in [
    ("faturamento_avinor", "data"),
    ("pedidos_emissao_avinor", "Dt.Entrega"),
    ("base_pedidos_avinor", "Dt.Entrega"),
]:
    cur.execute(f"SELECT MIN(`{col}`) mn, MAX(`{col}`) mx, COUNT(*) n FROM `{t}`")
    print(t, cur.fetchone())

cur.execute(
    """
SELECT COUNT(DISTINCT Pedido) AS pedidos
FROM pedidos_emissao_avinor
WHERE `Dt.Entrega` >= '2024-01-01'
"""
)
print("pedidos_emissao distinct 2024+", cur.fetchone())

cur.execute(
    """
SELECT COUNT(DISTINCT pedido) AS pedidos
FROM faturamento_avinor
WHERE pedido > 0 AND data >= '2024-01-01'
"""
)
print("faturamento distinct pedido 2024+", cur.fetchone())

cur.execute(
    """
SELECT COUNT(DISTINCT e.Pedido) AS emissao_pedidos,
       COUNT(DISTINCT CASE WHEN f.pedido IS NOT NULL THEN e.Pedido END) AS matched
FROM pedidos_emissao_avinor e
LEFT JOIN (
    SELECT DISTINCT pedido, cliente FROM faturamento_avinor WHERE pedido > 0
) f ON f.pedido = e.Pedido AND f.cliente = e.Cliente
WHERE e.`Dt.Entrega` >= '2024-01-01'
"""
)
print("emissao->faturamento match by pedido+cliente", cur.fetchone())

cur.execute(
    """
SELECT COUNT(DISTINCT bc.Cliente) AS clientes
FROM base_clientes_avinor bc
INNER JOIN faturamento_avinor f ON f.cliente = bc.Cliente
"""
)
print("base_clientes with faturamento", cur.fetchone())

cur.execute(
    """
SELECT COUNT(*) total,
  SUM(valor_total_faturado < 0) neg,
  SUM(valor_total_faturado > 0) pos,
  SUM(valor_total_faturado = 0) zero
FROM faturamento_avinor WHERE data >= '2024-01-01'
"""
)
print("faturamento sign 2024+", cur.fetchone())

cur.execute(
    """
SELECT DAYOFWEEK(data) dow, COUNT(*) c
FROM faturamento_avinor
WHERE data >= '2026-06-01' AND data < '2026-09-01'
GROUP BY dow ORDER BY dow
"""
)
print("day of week jun-aug 2026", cur.fetchall())

cur.close()
conn.close()
