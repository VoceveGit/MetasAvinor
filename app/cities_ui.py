from __future__ import annotations

import streamlit as st

from app.charts import chart_mapa_cidades_recorrencia
from app.constants import label_mes
from app.data import load_recorrencia_por_cidade
from app.dates_util import month_bounds
from app.formatting import fmt_pct_table
from app.geo_cidades import enrich_coords
from app.table_display import format_dataframe_columns, show_data_table
from app.ui import section_header


def render_cidades_recorrencia(ano: int, mes: int, vendedor_id: int | None) -> None:
    section_header(
        "Cidades e recorrência",
        "Onde há mais recompra no período (notas ÷ clientes), cruzando faturamento com cidade do cadastro.",
    )
    ini, fim = month_bounds(ano, mes)
    df = load_recorrencia_por_cidade(ini, fim, vendedor_id)
    if df.empty:
        st.info(f"Sem vendas com cidade cadastrada em {label_mes(ano, mes)}.")
        return

    geo = enrich_coords(df.head(50))
    mapped = int(geo["lat"].notna().sum())
    st.caption(
        f"Período: {label_mes(ano, mes)} · {len(df)} cidades com venda · "
        f"{mapped} no mapa (coordenadas em cache ou geocódigo OSM)."
    )

    st.plotly_chart(
        chart_mapa_cidades_recorrencia(geo),
        use_container_width=True,
        config={"displayModeBar": False},
    )

    tbl = df[
        ["cidade", "uf", "clientes", "notas", "recorrencia", "faturamento", "pct_faturamento"]
    ].copy()
    tbl["recorrencia"] = tbl["recorrencia"].map(lambda x: f"{float(x):.2f}")
    tbl = tbl.rename(
        columns={
            "cidade": "Cidade",
            "uf": "UF",
            "clientes": "Clientes",
            "notas": "Notas",
            "recorrencia": "Recorrência",
            "faturamento": "Faturamento",
            "pct_faturamento": "% faturamento",
        }
    )
    tbl["% faturamento"] = df["pct_faturamento"].map(fmt_pct_table)
    display = format_dataframe_columns(
        tbl,
        {"Faturamento": "money", "Clientes": "int", "Notas": "int"},
    )
    show_data_table(display, height=min(420, 40 + len(display) * 34))
