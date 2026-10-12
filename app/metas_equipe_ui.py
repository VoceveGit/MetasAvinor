from __future__ import annotations

import streamlit as st

from app.data import (
    load_grid_metas_colaboradores,
    load_panorama_metas_equipe,
    load_preco_medio_produto_vendedor,
)
from app.dates_util import month_bounds
from app.equipe_grid_logic import (
    loader_rows_to_state,
    premissa_from_row,
    recalc_row_formulas_only,
    rows_from_aggrid_df,
)
from app.grid_snapshot import load_grid_snapshot, save_grid_snapshot, snapshot_token
from app.equipe_grid_ui import render_equipe_grid
from app.formatting import fmt_brl_cell
from app.meta_proporcional import aplicar_colunas_proporcionais, meta_empresa_mensal_ref
from app.premissas import get_premissa_empresa, premissas_file_token, save_premissa
from app.table_display import show_data_table
from app.ui import section_header


def salvar_rows_state(rows: list[dict], ano: int, mes: int) -> int:
    n = 0
    for row in rows:
        vid = int(row["vendedor"])
        save_premissa(vid, ano, mes, premissa_from_row(row))
        n += 1
    return n


@st.fragment
def render_metas_equipe_tabela(ano: int, mes: int, taxa: float) -> None:
    section_header(
        "2 · Metas da equipe (tabela PAINEL)",
        "Preencha as colunas azuis; o restante calcula na hora. Clique em **Salvar** para gravar e usar no Ranking.",
    )
    emp = get_premissa_empresa(ano, mes)
    emp_ref = meta_empresa_mensal_ref(emp)
    if emp_ref > 0:
        extra = ""
        if float(emp.meta_empresa_anual_rs or 0) > 0:
            extra = f" (anual {fmt_brl_cell(emp.meta_empresa_anual_rs)} ÷ 12)"
        st.caption(
            f"Meta mensal de referência **{fmt_brl_cell(emp_ref)}**{extra} · "
            "colunas **amarelas** = peso 3 meses + fatia proporcional (somente leitura)."
        )

    df = load_grid_metas_colaboradores(ano, mes, taxa)
    if df.empty:
        st.info("Sem vendedores com faturamento no mês para montar a tabela.")
        return

    state_key = f"grid_state_{ano}_{mes}"
    ver_key = f"{state_key}_ver"
    force_erp_key = f"grid_force_erp_{ano}_{mes}"
    snap_tok = snapshot_token(ano, mes)
    grid_schema = f"{ano}_{mes:02d}_snap_{snap_tok or 0}_prem_{premissas_file_token()}"

    hdr_l, hdr_r = st.columns([3, 1])
    with hdr_r:
        if st.button("Recarregar do ERP", key=f"reload_erp_{ano}_{mes}"):
            st.session_state[force_erp_key] = True

    snap = load_grid_snapshot(ano, mes)
    if snap and snap_tok:
        with hdr_l:
            st.caption(
                "Arquivo **grid_snapshot_local.json** disponível — carrega rápido após salvar. "
                "Use *Recarregar do ERP* para refazer consultas."
            )
    if st.session_state.pop(force_erp_key, False):
        st.session_state[state_key] = loader_rows_to_state(df, ano, mes, taxa)
        st.session_state[ver_key] = grid_schema
    elif (
        state_key not in st.session_state
        or ver_key not in st.session_state
        or st.session_state.get(ver_key) != grid_schema
    ):
        if snap:
            st.session_state[state_key] = [
                recalc_row_formulas_only(dict(x), taxa) for x in snap
            ]
        else:
            st.session_state[state_key] = loader_rows_to_state(df, ano, mes, taxa)
        st.session_state[ver_key] = grid_schema

    rows: list[dict] = [
        recalc_row_formulas_only(dict(x), taxa) for x in st.session_state[state_key]
    ]
    rows = aplicar_colunas_proporcionais(rows, ano, mes, emp)
    st.session_state[state_key] = rows
    agdf_key = f"{state_key}_agdf"

    render_equipe_grid(rows, ano, mes, taxa, state_key)

    if st.button("Salvar premissas da tabela", type="primary", key=f"save_grid_{ano}_{mes}"):
        agdf = st.session_state.get(agdf_key)
        if agdf is None:
            st.error("Tabela ainda não carregou. Aguarde um instante e tente de novo.")
            return
        to_save = rows_from_aggrid_df(rows, agdf, taxa)
        to_save = [recalc_row_formulas_only(dict(x), taxa) for x in to_save]
        n = salvar_rows_state(to_save, ano, mes)
        save_grid_snapshot(ano, mes, to_save)
        st.session_state[state_key] = to_save
        load_grid_metas_colaboradores.clear()
        load_panorama_metas_equipe.clear()
        st.session_state[ver_key] = (
            f"{ano}_{mes:02d}_snap_{snapshot_token(ano, mes)}_prem_{premissas_file_token()}"
        )
        st.success(f"Premissas e tabela completa gravadas para {n} colaborador(es).")
        st.rerun()

    with st.expander("Preço médio por produto", expanded=False):
        ini, fim = month_bounds(ano, mes)
        preco = load_preco_medio_produto_vendedor(ini, fim, limit=40)
        if preco.empty:
            st.info("Sem itens suficientes para comparar preço médio no período.")
        else:
            show_data_table(
                preco.rename(
                    columns={
                        "nome": "Vendedor",
                        "produto": "Produto",
                        "preco_vendedor": "Preço médio vendedor",
                        "preco_equipe": "Preço médio equipe",
                        "desvio_pct": "Desvio %",
                        "faturamento": "Faturamento item",
                    }
                ),
                spec={
                    "Preço médio vendedor": "money",
                    "Preço médio equipe": "money",
                    "Desvio %": "pct",
                    "Faturamento item": "money",
                },
                height=360,
            )
