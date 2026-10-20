from __future__ import annotations

import streamlit as st

from app.constants import label_mes
from app.metas_equipe_ui import render_metas_equipe_tabela
from app.month_meta import select_ano_planejamento, select_mes_planejamento
from app.plano_ui import render_plano_anual
from app.readiness import ReadinessCheck, avaliar_preparacao_mes
from app.ui import section_header

_STATUS_ICON = {"ok": "🟢", "warn": "🟡", "fail": "🔴", "na": "⚪"}


def _checks_cache_key(ano: int, mes: int) -> str:
    return f"inicio_checks_{ano}_{mes}"


def _render_check(c: ReadinessCheck) -> None:
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


def render_inicio_preparacao() -> None:
    h1, h2 = st.columns([4, 1], vertical_alignment="bottom")
    with h1:
        section_header(
            "Início — plano de metas",
            "Meta do ano em cima; metas de cada colaborador, mês a mês, embaixo.",
        )
    with h2:
        ano = select_ano_planejamento("inicio_ano", label="Ano do plano")

    render_plano_anual(ano)

    st.markdown("---")
    section_header(
        "2 · Metas do mês",
        "Cada colaborador já vem com a meta automática. Ajuste quem quiser e salve o mês.",
    )
    c_mes, _ = st.columns([1, 2])
    with c_mes:
        mes = select_mes_planejamento(
            "inicio_mes",
            label="Mês",
            help_text="Meses fechados ficam só para consulta. O mês atual e os próximos são editáveis.",
            ano=ano,
        )
    taxa = 0.9
    st.session_state["inicio_taxa"] = taxa

    render_metas_equipe_tabela(ano, mes, taxa)

    st.markdown("---")
    section_header("3 · Conferência", "Checklist do mês (ERP + rotas + metas salvas).")

    ck_key = _checks_cache_key(ano, mes)
    col_a, col_b = st.columns([1, 2], vertical_alignment="center")
    with col_a:
        rodar = st.button(
            "Atualizar conferência do checklist",
            key="inicio_run_checks",
            use_container_width=True,
        )
    with col_b:
        st.caption(f"Lê ERP + rotas + metas salvas de {label_mes(ano, mes)}.")

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
        return
    aplicaveis = [c for c in checks if c.status != "na"]
    ok = sum(1 for c in aplicaveis if c.status == "ok")
    st.progress(
        ok / len(aplicaveis) if aplicaveis else 0,
        text=f"{ok} de {len(aplicaveis)} itens OK para {label_mes(ano, mes)}",
    )
    for c in checks:
        _render_check(c)
