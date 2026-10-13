from datetime import date, timedelta

import streamlit as st

from app.constants import MESES_NOME, label_mes
from app.dates_util import month_bounds, week_bounds


def _applied_period_key(key_prefix: str) -> str:
    return f"{key_prefix}_period_applied"


def _period_bounds_from_widgets(key_prefix: str) -> tuple[date, date, str]:
    """Lê widgets já renderizados nesta execução (session_state)."""
    modo = st.session_state.get(f"{key_prefix}_modo", "Mês")
    hoje = date.today()

    if modo == "Mês":
        ano = int(st.session_state.get(f"{key_prefix}_ano", hoje.year))
        mes = int(st.session_state.get(f"{key_prefix}_mes", hoje.month))
        ini, fim = month_bounds(ano, mes)
        return ini, fim, label_mes(ano, mes)

    if modo == "Semana":
        ref = st.session_state.get(f"{key_prefix}_semana", hoje)
        if not isinstance(ref, date):
            ref = hoje
        ini, fim = week_bounds(ref)
        return (
            ini,
            fim,
            f"Semana {ini.strftime('%d/%m')} – {(fim - timedelta(days=1)).strftime('%d/%m/%Y')}",
        )

    if modo == "Dia":
        ref = st.session_state.get(f"{key_prefix}_dia", hoje)
        if not isinstance(ref, date):
            ref = hoje
        return ref, ref + timedelta(days=1), ref.strftime("%d/%m/%Y")

    ini = st.session_state.get(f"{key_prefix}_de", hoje.replace(day=1))
    fim_in = st.session_state.get(f"{key_prefix}_ate", hoje)
    if not isinstance(ini, date):
        ini = hoje.replace(day=1)
    if not isinstance(fim_in, date):
        fim_in = hoje
    fim = fim_in + timedelta(days=1)
    if fim <= ini:
        fim = ini + timedelta(days=1)
    return ini, fim, f"{ini.strftime('%d/%m/%Y')} – {fim_in.strftime('%d/%m/%Y')}"


def _snap_dict(ini: date, fim: date, label: str) -> dict:
    return {"ini": ini.isoformat(), "fim": fim.isoformat(), "label": label}


def _render_period_widgets(key_prefix: str) -> None:
    st.markdown("##### Período")
    modo = st.radio(
        "Granularidade",
        ["Mês", "Semana", "Dia", "Intervalo"],
        horizontal=True,
        key=f"{key_prefix}_modo",
    )
    hoje = date.today()

    if modo == "Mês":
        anos = [2026, 2025, 2024, 2023]
        c1, c2 = st.columns(2)
        with c1:
            st.selectbox(
                "Ano",
                anos,
                index=0 if hoje.year in anos else 1,
                key=f"{key_prefix}_ano",
            )
        with c2:
            st.selectbox(
                "Mês",
                list(range(1, 13)),
                index=hoje.month - 1,
                format_func=lambda m: MESES_NOME[m],
                key=f"{key_prefix}_mes",
            )
        return

    if modo == "Semana":
        st.date_input(
            "Qualquer dia da semana",
            value=hoje,
            key=f"{key_prefix}_semana",
        )
        return

    if modo == "Dia":
        st.date_input("Dia", value=hoje, key=f"{key_prefix}_dia")
        return

    c1, c2 = st.columns(2)
    with c1:
        st.date_input("De", value=hoje.replace(day=1), key=f"{key_prefix}_de")
    with c2:
        st.date_input("Até", value=hoje, key=f"{key_prefix}_ate")


def periodo_selector(
    key_prefix: str = "rank",
    defer_apply: bool = True,
) -> tuple[date, date, str]:
    """Retorna (inicio, fim_exclusive, label). Com defer_apply, só muda após **Aplicar período**."""
    _render_period_widgets(key_prefix)
    pending_ini, pending_fim, pending_label = _period_bounds_from_widgets(key_prefix)
    pending = _snap_dict(pending_ini, pending_fim, pending_label)

    applied_key = _applied_period_key(key_prefix)
    if applied_key not in st.session_state:
        st.session_state[applied_key] = pending

    if defer_apply:
        dirty = pending != st.session_state[applied_key]
        if st.button(
            "Aplicar período",
            type="primary" if dirty else "secondary",
            key=f"{key_prefix}_period_apply",
        ):
            st.session_state[applied_key] = dict(pending)
            st.rerun()
        if dirty:
            st.caption(
                "Período alterado — clique **Aplicar período** para recarregar."
            )
        snap = st.session_state[applied_key]
    else:
        snap = pending

    ini = date.fromisoformat(snap["ini"])
    fim = date.fromisoformat(snap["fim"])
    return ini, fim, snap["label"]
