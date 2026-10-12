from __future__ import annotations

import streamlit as st

from app.constants import label_mes
from app.formatting import fmt_brl_cell
from app.premissas import get_premissa_empresa
from app.month_meta import caption_historico_vs_meta, select_mes_planejamento
from app.metas_equipe_ui import render_metas_equipe_tabela
from app.premissas_ui import (
    render_meta_empresa_mes,
    render_premissas_vendedores_checklist,
    render_rotas_upload,
)
from app.readiness import ReadinessCheck, avaliar_preparacao_mes
from app.ui import panel_box, section_header

_STATUS_ICON = {"ok": "🟢", "warn": "🟡", "fail": "🔴", "na": "⚪"}


def _checks_cache_key(ano: int, mes: int) -> str:
    return f"inicio_checks_{ano}_{mes}"


def _render_check(c: ReadinessCheck, ano: int, mes: int, taxa: float) -> None:
    icon = _STATUS_ICON.get(c.status, "⚪")
    with st.expander(f"{icon} {c.titulo}", expanded=c.status in ("fail", "warn")):
        st.markdown(f"**Na planilha Frigosol:** {c.passo_planilha}")
        st.markdown(f"**No Avinor:** {c.fonte_avinor}")
        st.markdown(f"**Para que serve:** {c.para_que_serve}")
        st.info(c.situacao)
        if c.se_faltar:
            st.warning(f"**Se faltar ou estiver errado:** {c.se_faltar}")
        if c.id == "produtos_familia" and c.status == "ok":
            st.success("Abra a aba **Produtos & linhas** para ver gráficos.")


@st.fragment
def _bloco_configuracao_mes(ano: int, mes: int, taxa: float) -> None:
    section_header(
        "1 · Configurar o mês",
        "Meta da empresa, rotas e (opcional) premissas em lote.",
    )
    render_meta_empresa_mes(
        ano,
        mes,
        taxa,
        key_prefix=f"cfg_emp_{ano}_{mes}",
        embedded=True,
        defer_analytics=True,
        somente_meta_empresa=True,
    )
    with st.expander("Planilha de rotas (oportunidades)", expanded=False):
        render_rotas_upload(key_prefix=f"cfg_rotas_{ano}_{mes}")
    with st.expander("Premissas em lote (opcional)", expanded=False):
        render_premissas_vendedores_checklist(
            ano, mes, taxa, key_prefix=f"cfg_vend_{ano}_{mes}"
        )


def render_inicio_preparacao() -> None:
    section_header(
        "Início — configure o mês",
        "Tabela de metas aqui. Análise nas outras abas (incluindo **Colaboradores**).",
    )

    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        ano = st.selectbox(
            "Ano de referência",
            [2026, 2025, 2024],
            index=0,
            key="inicio_ano",
        )
    with c2:
        mes = select_mes_planejamento(
            "inicio_mes",
            label="Mês da meta (prescrição)",
            help_text="Out., nov. e dez. — feche o mês atual antes de planejar o próximo.",
        )
    with c3:
        taxa = st.slider(
            "TX conversão projetada padrão (%)",
            50,
            100,
            90,
            1,
            key="inicio_taxa_pct",
            help="Usado quando a coluna TX conv. projetada estiver vazia (ex.: 90%).",
        )
        taxa = taxa / 100.0
        st.session_state["inicio_taxa"] = taxa
        caption_historico_vs_meta(ano, mes)

    emp_mes = get_premissa_empresa(ano, mes)
    if emp_mes.meta_empresa_rs <= 0:
        for m_ant in (9, 8, 7):
            if m_ant == mes:
                continue
            emp_ant = get_premissa_empresa(ano, m_ant)
            if emp_ant.meta_empresa_rs > 0:
                st.warning(
                    f"Meta da empresa ({fmt_brl_cell(emp_ant.meta_empresa_rs)}) está salva em "
                    f"**{label_mes(ano, m_ant)}**. Para **{label_mes(ano, mes)}**, salve de novo em "
                    "**Configurar o mês**."
                )
                break

    panel_box(
        "Fluxo",
        "**1** meta empresa + rotas · **2** tabela (edite e salve) · **3** checklist. "
        "Depois: **Colaboradores** (um por um), **Ranking** (todos).",
    )

    _bloco_configuracao_mes(ano, mes, taxa)
    st.markdown("---")
    render_metas_equipe_tabela(ano, mes, taxa)

    st.markdown("---")
    section_header(
        "3 · Conferência (checklist)",
        "Valida se está pronto para analisar.",
    )

    ck_key = _checks_cache_key(ano, mes)
    col_a, col_b = st.columns([1, 2])
    with col_a:
        rodar = st.button(
            "Atualizar conferência do checklist",
            type="primary",
            key="inicio_run_checks",
        )
    with col_b:
        st.caption("Lê ERP + rotas + premissas salvas.")

    if rodar:
        try:
            with st.spinner("Conferindo dados…"):
                st.session_state[ck_key] = avaliar_preparacao_mes(ano, mes)
        except Exception as e:
            st.error("Não foi possível rodar a conferência.")
            st.code(str(e))
            return

    checks: list[ReadinessCheck] | None = st.session_state.get(ck_key)
    if checks is None:
        st.info("Configure acima e clique em **Atualizar conferência do checklist**.")
    else:
        aplicaveis = [c for c in checks if c.status != "na"]
        ok = sum(1 for c in aplicaveis if c.status == "ok")
        st.progress(
            ok / len(aplicaveis) if aplicaveis else 0,
            text=f"{ok} de {len(aplicaveis)} itens OK para {label_mes(ano, mes)}",
        )
        for c in checks:
            _render_check(c, ano, mes, taxa)
