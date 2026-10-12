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

print("=== dadoscompany_avinor ===")
cur.execute("SELECT COUNT(*) c FROM dadoscompany_avinor")
print("total", cur.fetchone()["c"])
cur.execute(
    """
SELECT apto_para_venda, COUNT(*) c FROM dadoscompany_avinor
GROUP BY apto_para_venda ORDER BY c DESC
"""
)
print("apto_para_venda", cur.fetchall())
cur.execute(
    "SELECT MIN(data_exportacao) mn, MAX(data_exportacao) mx FROM dadoscompany_avinor"
)
print("export range", cur.fetchone())
cur.execute(
    """
SELECT COUNT(*) total,
  SUM(codigo_do_cliente REGEXP '^[0-9]+$') codigo_numerico,
  SUM(codigo_do_cliente IS NULL OR codigo_do_cliente = '') codigo_vazio
FROM dadoscompany_avinor
"""
)
print("codigo cliente", cur.fetchone())
cur.execute(
    """
SELECT COUNT(DISTINCT d.codigo_do_cliente) dc
FROM dadoscompany_avinor d
INNER JOIN base_clientes_avinor b ON b.Cliente = CAST(d.codigo_do_cliente AS UNSIGNED)
WHERE d.codigo_do_cliente REGEXP '^[0-9]+$'
"""
)
print("CRM codes matching base_clientes", cur.fetchone())
cur.execute(
    """
SELECT COUNT(*) c FROM dadoscompany_avinor d
INNER JOIN base_clientes_avinor b ON b.Cliente = CAST(d.codigo_do_cliente AS UNSIGNED)
WHERE d.apto_para_venda = 'Sim' AND b.`Situação` = 'Ativo'
"""
)
print("apto Sim + Ativo", cur.fetchone())
cur.execute(
    'SELECT id, nome_da_empresa, codigo_do_cliente, apto_para_venda, data_exportacao '
    "FROM dadoscompany_avinor WHERE apto_para_venda = 'Sim' LIMIT 5"
)
print("samples apto Sim", cur.fetchall())

print("\n=== deals_avinor ===")
cur.execute("SELECT COUNT(*) c FROM deals_avinor")
print("total", cur.fetchone()["c"])
cur.execute(
    """
SELECT MIN(data_exportacao) mx_exp, MAX(data_exportacao) mx_exp2,
       MIN(criado_em) mn_criado, MAX(criado_em) mx_criado
FROM deals_avinor
"""
)
print("dates", cur.fetchone())
cur.execute(
    "SELECT pipeline, COUNT(*) c FROM deals_avinor GROUP BY pipeline ORDER BY c DESC"
)
print("pipelines", cur.fetchall())
cur.execute(
    """
SELECT COUNT(*) total,
  SUM(empresa REGEXP '^[0-9]+$') emp_num,
  SUM(codigo_do_pedido IS NOT NULL AND codigo_do_pedido != '') com_pedido,
  SUM(total > 0) com_valor
FROM deals_avinor
"""
)
print("empresa/pedido/valor", cur.fetchone())
cur.execute(
    """
SELECT COUNT(DISTINCT d.id) deals_match
FROM deals_avinor d
INNER JOIN base_clientes_avinor b ON b.Cliente = CAST(d.empresa AS UNSIGNED)
WHERE d.empresa REGEXP '^[0-9]+$'
"""
)
print("deals empresa matches Cliente", cur.fetchone())
cur.execute(
    """
SELECT pessoa_responsavel, COUNT(*) c FROM deals_avinor
WHERE pipeline = 'Vendas'
GROUP BY pessoa_responsavel ORDER BY c DESC LIMIT 8
"""
)
print("vendas por responsavel", cur.fetchall())
cur.execute(
    """
SELECT id, nome, pipeline, fase_do_negocio, total, empresa, pessoa_responsavel, codigo_do_pedido
FROM deals_avinor WHERE pipeline = 'Vendas' AND total > 0 LIMIT 5
"""
)
print("deals vendas com valor", cur.fetchall())

# overlap: client with open-ish deal in Vendas
cur.execute(
    """
SELECT COUNT(DISTINCT d.empresa) emp
FROM deals_avinor d
WHERE d.pipeline = 'Vendas' AND d.grupo_de_fase = 'P'
  AND d.empresa REGEXP '^[0-9]+$'
"""
)
print("empresas com deal Vendas grupo P", cur.fetchone())

cur.close()
conn.close()
