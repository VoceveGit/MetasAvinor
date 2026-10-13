from pathlib import Path

import pandas as pd
import streamlit as st
from mysql.connector import Error

from app.charts import chart_top_vendedores
from app.constants import label_mes
from app.data import load_ranking_periodo, load_vendedores
from app.dates_util import month_bounds
from app.month_meta import meta_mes_sessao
from app.neon_store import storage_backend_label
from app.period_filter import _applied_period_key, _snap_dict, periodo_selector
from app.products_ui import render_produtos_linhas
from app.colaboradores_ui import render_aba_colaboradores
from app.setup_home import render_inicio_preparacao
from app.table_display import show_data_table
from app.ranking_ui import (
    render_painel_equipe_mes,
    render_tabela_acompanhamento,
)
from app.ui import (
    inject_styles,
    render_fixed_nav,
    render_top_toolbar,
    section_header,
)
from app.visao_geral_ui import render_visao_geral

def _app_version() -> str:
    vf = Path(__file__).resolve().parent.parent / "VERSION"
    if vf.is_file():
        return vf.read_text(encoding="utf-8").strip() or "dev"
    return "dev"


APP_VERSION = _app_version()
APP_ROOT = Path(__file__).resolve().parent.parent


def _ensure_ranking_period_defaults(ano_meta: int, mes_meta: int) -> None:
    """Abre o Ranking já no mês da meta (Início), sem cair no gráfico legado."""
    if "vend_modo" not in st.session_state:
        st.session_state["vend_modo"] = "Mês"
    if "vend_ano" not in st.session_state:
        st.session_state["vend_ano"] = ano_meta
    if "vend_mes" not in st.session_state:
        st.session_state["vend_mes"] = mes_meta
    applied = _applied_period_key("vend")
    if applied not in st.session_state:
        ini, fim = month_bounds(ano_meta, mes_meta)
        st.session_state[applied] = _snap_dict(ini, fim, label_mes(ano_meta, mes_meta))


def tab_ranking(filtros: dict):
    section_header(
        "Progresso da equipe",
        "Meta do plano × realizado, por colaborador. Escolha mês, semana ou dia no calendário.",
    )
    ano_meta, mes_meta, taxa = meta_mes_sessao()
    _ensure_ranking_period_defaults(ano_meta, mes_meta)

    rank_modo = st.session_state.get("vend_modo", "Mês")
    rank_ano = int(st.session_state.get("vend_ano", ano_meta))
    rank_mes = int(st.session_state.get("vend_mes", mes_meta))

    ini, fim = month_bounds(rank_ano, rank_mes)
    label_per = label_mes(rank_ano, rank_mes)

    if rank_modo != "Mês":
        with st.expander("Gráfico de outro período (não é o painel de cards)", expanded=True):
            ini, fim, label_per = periodo_selector("vend", defer_apply=True)
            df = load_ranking_periodo(ini, fim, 50)
            if df.empty:
                st.info("Sem vendas no período selecionado.")
                return
            total = float(df["faturamento"].sum())
            st.caption(f"Período: {label_per} · Faturamento total: {_fmt_brl(total)}")
            st.plotly_chart(
                chart_top_vendedores(df.head(12)),
                use_container_width=True,
                config={"displayModeBar": False},
            )
            _ranking_tabela_resumo(df, False, total)
        st.caption("Para o painel de cards, volte o período para **Mês**.")
        return

    df = load_ranking_periodo(ini, fim, 50)
    if df.empty:
        st.info("Sem vendas no período selecionado.")
        return

    total = float(df["faturamento"].sum())

    st.caption(f"Painel de **{label_per}**.")
    acomp = render_painel_equipe_mes(rank_ano, rank_mes, taxa)
    if not acomp.empty:
        with st.expander("Tabela detalhada (exportar / conferir números)"):
            render_tabela_acompanhamento(acomp)

    st.caption("Metas e premissas: aba **Início**.")


def _ranking_tabela_resumo(df: pd.DataFrame, com_meta: bool, total: float) -> None:
    show = df.copy()
    if com_meta:
        show["atingimento_meta_pct"] = show["atingimento_meta"]
    show["pct_faturamento_pct"] = show["pct_faturamento"]
    show["tx_cobertura_pct"] = show["tx_cobertura"].apply(
        lambda x: float(x) * 100 if pd.notna(x) else None
    )
    cols = ["vendedor", "nome", "faturamento", "pct_faturamento_pct", "carteira", "clientes", "notas"]
    spec: dict[str, str] = {
        "Cód.": "text",
        "Vendedor": "text",
        "Faturamento": "money",
        "% do período": "pct",
        "Carteira": "int",
        "Clientes período": "int",
        "Notas": "int",
        "Cobertura": "pct",
        "Recorrência": "float",
    }
    if com_meta:
        cols = [
            "vendedor",
            "nome",
            "faturamento",
            "meta",
            "atingimento_meta_pct",
            "pct_faturamento_pct",
            "carteira",
            "clientes",
            "notas",
            "tx_cobertura_pct",
            "tx_recorrencia",
        ]
        spec["Meta"] = "money"
        spec["Ating. meta"] = "pct"
    else:
        cols = cols + ["tx_cobertura_pct", "tx_recorrencia"]

    tbl = show[cols].rename(
        columns={
            "vendedor": "Cód.",
            "nome": "Vendedor",
            "faturamento": "Faturamento",
            "meta": "Meta",
            "atingimento_meta_pct": "Ating. meta",
            "pct_faturamento_pct": "% do período",
            "carteira": "Carteira",
            "clientes": "Clientes período",
            "notas": "Notas",
            "tx_cobertura_pct": "Cobertura",
            "tx_recorrencia": "Recorrência",
        }
    )
    tot_row = {
        "Cód.": "",
        "Vendedor": "TOTAL DO PERÍODO",
        "Faturamento": total,
        "% do período": 100.0,
        "Carteira": int(df["carteira"].sum()),
        "Clientes período": int(df["clientes"].sum()),
        "Notas": int(df["notas"].sum()),
        "Cobertura": None,
        "Recorrência": None,
    }
    if com_meta:
        tot_row["Meta"] = float(df["meta"].sum())
        tot_row["Ating. meta"] = (
            total / float(df["meta"].sum()) * 100 if float(df["meta"].sum()) > 0 else None
        )
    tbl = pd.concat([tbl, pd.DataFrame([tot_row])], ignore_index=True)
    show_data_table(
        tbl,
        spec=spec,
        height=min(520, 38 + len(tbl) * 36),
    )


def main():
    st.set_page_config(
        page_title="Metas Avinor",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_styles()

    try:
        vendedores = load_vendedores()
    except Error as e:
        st.error(
            "Não foi possível conectar ao banco. Crie/edite o arquivo "
            "`.env` na pasta **MetasAvinor** com `TEST_DB_USER` e `TEST_DB_PASSWORD`."
        )
        st.code(str(e))
        return

    page = render_fixed_nav(APP_VERSION, str(APP_ROOT))
    filtros = render_top_toolbar()

    if page == "Início":
        render_inicio_preparacao()
    elif page == "Visão geral":
        render_visao_geral(filtros, vendedores)
    elif page == "Produtos & linhas":
        p_ano, p_mes, _ = meta_mes_sessao()
        render_produtos_linhas(p_ano, p_mes, None)
    elif page == "Colaboradores":
        c_ano, c_mes, c_taxa = meta_mes_sessao()
        render_aba_colaboradores(c_ano, c_mes, c_taxa)
    else:
        tab_ranking(filtros)

    st.caption(
        f"v{APP_VERSION} · {APP_ROOT} — EXTRACTOR read-only · estado em {storage_backend_label()}"
    )


if __name__ == "__main__":
    main()
