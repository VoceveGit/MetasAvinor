-- MetasAvinor · MySQL EXTRACTOR (não Postgres)
-- Rode EXPLAIN nas queries de app/data.py antes/depois.
-- Ajuste nomes se o schema local for diferente.

-- Faturamento: filtro por data + vendedor (ranking, tops, peso 3m)
CREATE INDEX idx_fat_data_vendedor
    ON faturamento_avinor (data, vendedor, valor_total_faturado);

-- Carteira / join cliente
CREATE INDEX idx_fat_vendedor_data
    ON faturamento_avinor (vendedor, data);

-- Base clientes (cobertura, tops cidade)
CREATE INDEX idx_bc_cliente ON base_clientes_avinor (Cliente);
