"""Controles de mês de meta (planejamento Q4)."""

from __future__ import annotations

from datetime import date

import streamlit as st

from app.constants import MESES_NOME, label_mes

# Meses em que o gestor prescreve metas no painel (restante do ano).
MESES_PLANEJAMENTO = (10, 11, 12)


def default_mes_planejamento() -> int:
    hoje = date.today()
    if hoje.month in MESES_PLANEJAMENTO:
        return hoje.month
    return MESES_PLANEJAMENTO[0]


def select_mes_planejamento(
    key: str,
    label: str = "Mês da meta",
    help_text: str | None = None,
) -> int:
    opcoes = list(MESES_PLANEJAMENTO)
    default = default_mes_planejamento()
    idx = opcoes.index(default) if default in opcoes else 0
    return st.selectbox(
        label,
        opcoes,
        index=idx,
        format_func=lambda m: MESES_NOME[m],
        key=key,
        help=help_text,
    )


def meta_mes_sessao() -> tuple[int, int, float]:
    ano = int(st.session_state.get("inicio_ano", 2026))
    mes = int(st.session_state.get("inicio_mes", default_mes_planejamento()))
    taxa = float(st.session_state.get("inicio_taxa", 0.9))
    return ano, mes, taxa


def caption_historico_vs_meta(ano: int, mes: int) -> None:
    st.caption(
        f"**Meta prescrita:** {label_mes(ano, mes)}. "
        "Colunas brancas (ticket, cobertura média, etc.) vêm do **histórico** (meses anteriores). "
        "Colunas azuis = o que você define para acompanhar no Ranking."
    )
