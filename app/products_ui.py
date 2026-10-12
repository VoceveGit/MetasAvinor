from __future__ import annotations

import pandas as pd
import streamlit as st

from app.charts import chart_familia_pizza, chart_top_familias_barras
from app.constants import MESES_NOME, label_mes
from app.data import (
    load_faturamento_por_familia,
    load_faturamento_top_produtos,
    load_preco_medio_produto_vendedor,
)
from app.dates_util import month_bounds
from app.cities_ui import render_cidades_recorrencia
from app.formatting import fmt_brl_cell
from app.table_display import show_data_table
from app.ui import section_header


def render_produtos_linhas(
    ano: int,
    mes: int,
    vendedor_id: int | None,
) -> None:
    section_header(
        "Produtos e famílias",
        "Vendas por linha de produto (campo família do ERP) e ranking de itens — "
        "equivalente analítico ao que na Frigosol se divide em abas BOI/SUINO/etc.",
    )

    ini, fim = month_bounds(ano, mes)
    fam = load_faturamento_por_familia(ini, fim, vendedor_id)
    prod = load_faturamento_top_produtos(ini, fim, vendedor_id, limit=30)

    if fam.empty:
        st.warning(f"Sem faturamento por produto em {label_mes(ano, mes)}.")
        return

    total = float(fam["faturamento"].sum())
    st.caption(
        f"Período: {label_mes(ano, mes)} · "
        f"Total analisado: {fmt_brl_cell(total)} · "
        f"{len(fam)} famílias · origem: `faturamento_avinor` (itens da nota)."
    )

    c1, c2 = st.columns([1, 1])
    with c1:
        st.plotly_chart(
            chart_familia_pizza(fam, f"Mix por família — {MESES_NOME[mes]}/{ano}"),
            use_container_width=True,
            config={"displayModeBar": False},
        )
    with c2:
        st.plotly_chart(
            chart_top_familias_barras(fam),
            use_container_width=True,
            config={"displayModeBar": False},
        )

    fam_tbl = fam.rename(
        columns={
            "familia": "Família",
            "faturamento": "Faturamento",
            "pct": "% do total",
            "notas": "Notas",
            "clientes": "Clientes",
            "peso_kg": "Peso (kg)",
        }
    )[["Família", "Faturamento", "% do total", "Notas", "Clientes", "Peso (kg)"]]
    st.markdown("#### Por família (linha de produto)")
    show_data_table(
        fam_tbl,
        spec={
            "Faturamento": "money",
            "% do total": "pct",
            "Notas": "int",
            "Clientes": "int",
            "Peso (kg)": "int",
        },
        height=min(400, 40 + len(fam_tbl) * 36),
    )

    st.markdown("#### Top produtos (código + descrição)")
    prod_tbl = prod.rename(
        columns={
            "codigo": "Cód.",
            "produto": "Descrição",
            "familia": "Família",
            "faturamento": "Faturamento",
            "pct": "% (top)",
            "notas": "Notas",
        }
    )[["Cód.", "Descrição", "Família", "Faturamento", "% (top)", "Notas"]]
    show_data_table(
        prod_tbl,
        spec={"Faturamento": "money", "% (top)": "pct", "Notas": "int"},
        height=420,
    )

    st.markdown("#### Preço médio por vendedor e produto")
    preco_all = load_preco_medio_produto_vendedor(ini, fim, limit=120)
    if preco_all.empty:
        st.info("Sem itens suficientes para comparar preço médio no período.")
    else:
        sellers = preco_all.drop_duplicates("vendedor").sort_values("nome")
        opcoes_vend = ["Todos (lista completa)"] + [
            f"{int(r.vendedor)} — {r.nome}" for r in sellers.itertuples()
        ]
        escolha_vend = st.selectbox(
            "Ver vendas de um vendedor",
            opcoes_vend,
            key=f"preco_vend_{ano}_{mes}",
            help="Escolha o vendedor para filtrar a tabela (itens com preço abaixo da média da equipe).",
        )
        if escolha_vend == opcoes_vend[0]:
            preco = preco_all
        else:
            vid = int(escolha_vend.split(" — ")[0])
            nome_v = escolha_vend.split(" — ", 1)[1]
            preco = load_preco_medio_produto_vendedor(
                ini, fim, vendedor_id=vid, only_below_team=True
            )
            if preco.empty:
                preco = load_preco_medio_produto_vendedor(
                    ini, fim, vendedor_id=vid, only_below_team=False
                )
                st.caption(
                    f"**{nome_v}** — todos os produtos do período "
                    "(nenhum ficou abaixo da média da equipe)."
                )
            else:
                st.caption(
                    f"**{nome_v}** — produtos com preço médio abaixo da equipe no período."
                )
            vendas = load_faturamento_top_produtos(ini, fim, vid, limit=25)
            if not vendas.empty:
                st.markdown("##### Vendas do vendedor (top produtos)")
                vendas_tbl = vendas.rename(
                    columns={
                        "codigo": "Cód.",
                        "produto": "Descrição",
                        "familia": "Família",
                        "faturamento": "Faturamento",
                        "pct": "% (top)",
                        "notas": "Notas",
                    }
                )[["Cód.", "Descrição", "Família", "Faturamento", "% (top)", "Notas"]]
                show_data_table(
                    vendas_tbl,
                    spec={"Faturamento": "money", "% (top)": "pct", "Notas": "int"},
                    height=min(360, 40 + len(vendas_tbl) * 32),
                )

        show_data_table(
            preco.rename(
                columns={
                    "nome": "Vendedor",
                    "produto": "Produto",
                    "preco_vendedor": "Preço médio vendedor",
                    "preco_equipe": "Preço médio equipe",
                    "desvio_pct": "Desvio %",
                    "faturamento": "Faturamento item",
                    "notas": "Notas",
                }
            ),
            spec={
                "Preço médio vendedor": "money",
                "Preço médio equipe": "money",
                "Desvio %": "pct",
                "Faturamento item": "money",
                "Notas": "int",
            },
            height=min(480, 40 + len(preco) * 32),
        )

    st.markdown("---")
    try:
        render_cidades_recorrencia(ano, mes, vendedor_id)
    except Exception as exc:
        st.warning(f"Mapa de cidades indisponível neste momento: {exc}")

    st.caption(
        "Metas por família ainda não estão no motor Frigosol; use esta visão para "
        "acompanhar mix e evolução. Premissas de meta continuam por vendedor (Avinor unificada)."
    )
