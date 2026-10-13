"""Controles de mês de meta (plano anual)."""

from __future__ import annotations

from datetime import date

import streamlit as st

from app.constants import MESES_NOME, label_mes

MESES_PLANEJAMENTO = tuple(range(1, 13))

# Widgets somem do session_state quando a aba não os desenha; estas chaves guardam a escolha.
_ANO_KEY = "meta_ano_sel"
_MES_KEY = "meta_mes_sel"
_TAXA_KEY = "inicio_taxa"


def default_mes_planejamento() -> int:
    return date.today().month


def _fmt_mes(ano: int, m: int) -> str:
    from app.plano_metas import mes_fechado

    return f"{MESES_NOME[m]} · fechado" if mes_fechado(ano, m) else MESES_NOME[m]


def select_ano_planejamento(key: str, label: str = "Ano") -> int:
    hoje = date.today().year
    opcoes = [hoje + 1, hoje, hoje - 1]
    atual = int(st.session_state.get(_ANO_KEY, hoje))
    if key not in st.session_state:
        st.session_state[key] = atual if atual in opcoes else hoje
    ano = st.selectbox(label, opcoes, key=key)
    st.session_state[_ANO_KEY] = int(ano)
    return int(ano)


def select_mes_planejamento(
    key: str,
    label: str = "Mês da meta",
    help_text: str | None = None,
    ano: int | None = None,
) -> int:
    ano = int(ano or st.session_state.get(_ANO_KEY, date.today().year))
    if key not in st.session_state:
        st.session_state[key] = int(st.session_state.get(_MES_KEY, default_mes_planejamento()))
    mes = st.selectbox(
        label,
        list(MESES_PLANEJAMENTO),
        format_func=lambda m: _fmt_mes(ano, m),
        key=key,
        help=help_text,
    )
    st.session_state[_MES_KEY] = int(mes)
    return int(mes)


def meta_mes_sessao() -> tuple[int, int, float]:
    ano = int(st.session_state.get(_ANO_KEY, date.today().year))
    mes = int(st.session_state.get(_MES_KEY, default_mes_planejamento()))
    taxa = float(st.session_state.get(_TAXA_KEY, 0.9))
    return ano, mes, taxa


def caption_historico_vs_meta(ano: int, mes: int) -> None:
    st.caption(
        f"**Meta prescrita:** {label_mes(ano, mes)}. "
        "Colunas brancas (ticket, cobertura média, etc.) vêm do **histórico** (meses anteriores). "
        "Colunas azuis = o que você define para acompanhar no Progresso."
    )
