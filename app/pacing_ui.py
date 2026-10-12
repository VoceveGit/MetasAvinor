"""Calendário + filtros de ritmo (mês / semana / dia)."""

from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import date, timedelta

import streamlit as st

from app.constants import MESES_NOME, label_mes
from app.dates_util import month_bounds
from app.pacing import (
    day_bounds,
    days_in_month,
    week_for_date,
    weeks_in_month,
)

_PACING_CSS = """
<style>
.pacing-cal-anchor { height: 0; overflow: hidden; margin: 0; padding: 0; }
.pacing-cal-panel {
    max-width: 420px; background: linear-gradient(165deg, #f8fafc 0%, #fff 45%, #f0f9ff 100%);
    border-radius: 16px; padding: 1rem 1.15rem 0.9rem;
    border: 1px solid #dbeafe; box-shadow: 0 4px 20px rgba(21, 101, 192, 0.08);
    margin: 0.5rem 0 0.75rem;
}
.pacing-cal-panel .cal-title {
    text-align: center; font-weight: 800; font-size: 1.08rem; color: #0f172a;
    margin-bottom: 0.5rem; letter-spacing: 0.02em;
}
.pacing-cal-panel .cal-sub {
    text-align: center; font-size: 0.75rem; color: #64748b; margin-bottom: 0.65rem;
}
.pacing-cal-panel .cal-wd {
    display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px;
    margin-bottom: 0.35rem; padding: 0.35rem 0.25rem; border-radius: 10px;
    background: #f3f4f6;
}
.pacing-cal-panel .cal-wd span {
    text-align: center; font-size: 0.72rem; color: #6b7280; font-weight: 500;
}
.pacing-cal-panel .cal-wd span.we { font-weight: 800; color: #374151; }
div[data-testid="stVerticalBlock"]:has(.pacing-cal-anchor) [data-testid="stHorizontalBlock"] {
    gap: 0.25rem !important;
}
div[data-testid="stVerticalBlock"]:has(.pacing-cal-anchor) [data-testid="column"] button {
    min-height: 2.15rem !important; border-radius: 999px !important;
    font-size: 0.82rem !important; font-weight: 600 !important;
    border: none !important; padding: 0.2rem !important;
}
div[data-testid="stVerticalBlock"]:has(.pacing-cal-anchor) button[kind="primary"] {
    background: #1565c0 !important; color: #fff !important;
    box-shadow: 0 0 0 2px #fff, 0 0 0 3px #1565c0 !important;
}
div[data-testid="stVerticalBlock"]:has(.pacing-cal-anchor) button[kind="secondary"] {
    background: #e3f2fd !important; color: #1565c0 !important;
}
div[data-testid="stVerticalBlock"]:has(.pacing-cal-anchor) button[kind="tertiary"] {
    background: transparent !important; color: #9ca3af !important;
}
.pacing-cal-hint { font-size: 0.78rem; color: #6b7280; margin-top: 0.35rem; }
.meta-drum-stack { position: relative; min-height: 2.6rem; }
.meta-drum-main {
    font-size: 1.75rem; font-weight: 700; color: #0f3328;
    transition: transform 0.45s ease, opacity 0.35s ease;
}
.meta-drum-sub {
    font-size: 0.82rem; color: #6b7280; margin-top: 0.15rem;
    transition: transform 0.45s ease, opacity 0.35s ease;
}
.meta-drum-real .meta-drum-main { color: #c2410c; animation: meta-drum-in 0.5s ease; }
.meta-drum-behind .meta-drum-main { color: #dc2626; }
.meta-drum-ahead .meta-drum-main { color: #047857; }
@keyframes meta-drum-in {
    0% { transform: translateY(18px) rotateX(70deg); opacity: 0; }
    100% { transform: translateY(0) rotateX(0); opacity: 1; }
}
</style>
"""

_WD = ("Do", "Se", "Te", "Qu", "Qu", "Se", "Sá")


@dataclass
class PacingView:
    lente: str
    ini: date
    fim_exclusive: date
    selected_day: date
    week_label: str
    period_label: str
    period_index: int
    n_periods: int


def _day_key(prefix: str, ano: int, mes: int) -> str:
    return f"{prefix}_pacing_day_{ano}_{mes}"


def _lente_key(prefix: str) -> str:
    return f"{prefix}_pacing_lente"


def _applied_snap_key(prefix: str) -> str:
    return f"{prefix}_pacing_applied_snap"


def _pacing_snapshot(prefix: str, ano: int, mes: int, default_day: date) -> dict:
    dk = _day_key(prefix, ano, mes)
    return {
        "lente": st.session_state.get(_lente_key(prefix), "Mensal") or "Mensal",
        "day": st.session_state.get(dk, default_day.isoformat()),
    }


def pacing_view_from_lente_day(ano: int, mes: int, lente: str, selected: date) -> PacingView:
    start, end = month_bounds(ano, mes)
    n_days = days_in_month(ano, mes)
    weeks = weeks_in_month(ano, mes)
    week = week_for_date(ano, mes, selected)
    lente = lente or "Mensal"

    if lente == "Mensal":
        return PacingView(
            lente=lente,
            ini=start,
            fim_exclusive=end,
            selected_day=selected,
            week_label=week.label,
            period_label=label_mes(ano, mes),
            period_index=0,
            n_periods=1,
        )
    if lente == "Semanal":
        return PacingView(
            lente=lente,
            ini=week.ini,
            fim_exclusive=week.fim_exclusive,
            selected_day=selected,
            week_label=week.label,
            period_label=week.label,
            period_index=week.index,
            n_periods=len(weeks),
        )
    d_ini, d_fim = day_bounds(ano, mes, selected.day)
    return PacingView(
        lente=lente,
        ini=d_ini,
        fim_exclusive=d_fim,
        selected_day=selected,
        week_label=week.label,
        period_label=selected.strftime("%d/%m/%Y"),
        period_index=selected.day - 1,
        n_periods=n_days,
    )


def _sunday_col(d: date) -> int:
    return (d.weekday() + 1) % 7


def _render_calendar_picker(
    ano: int,
    mes: int,
    selected: date,
    week,
    key_prefix: str,
    dk: str,
    defer_rerun: bool = False,
) -> None:
    n_days = days_in_month(ano, mes)
    start, _ = month_bounds(ano, mes)
    title = f"{MESES_NOME[mes]} {ano}"
    wd_html = "".join(
        f'<span class="{"we" if i in (0, 6) else ""}">{w}</span>' for i, w in enumerate(_WD)
    )
    st.markdown(
        f"""
        <div class="pacing-cal-panel">
          <div class="pacing-cal-title">{html.escape(title)}</div>
          <div class="cal-sub">Toque no dia · semana em destaque</div>
          <div class="cal-wd">{wd_html}</div>
        </div>
        <div class="pacing-cal-anchor"></div>
        """,
        unsafe_allow_html=True,
    )

    pad = _sunday_col(start)
    cells: list[int | None] = [None] * pad + list(range(1, n_days + 1))
    while len(cells) % 7 != 0:
        cells.append(None)

    for row_i in range(0, len(cells), 7):
        cols = st.columns(7)
        for col_i, col in enumerate(cols):
            day_num = cells[row_i + col_i]
            with col:
                if day_num is None:
                    st.write("")
                    continue
                d = date(ano, mes, day_num)
                in_week = week.ini <= d < week.fim_exclusive
                is_sel = day_num == selected.day
                if is_sel:
                    kind = "primary"
                elif in_week:
                    kind = "secondary"
                else:
                    kind = "tertiary"
                if st.button(
                    f"{day_num:02d}",
                    key=f"{key_prefix}_cal_{ano}_{mes}_{day_num}_{row_i}",
                    type=kind,
                    use_container_width=True,
                ):
                    st.session_state[dk] = d.isoformat()
                    if not defer_rerun:
                        st.rerun()

    st.markdown(
        f'<p class="pacing-cal-hint">{html.escape(week.label)} · dia {selected.day:02d}</p>',
        unsafe_allow_html=True,
    )


def render_pacing_controls(
    ano: int,
    mes: int,
    key_prefix: str = "pacing",
    defer_apply: bool = True,
) -> PacingView:
    st.markdown(_PACING_CSS, unsafe_allow_html=True)
    start, end = month_bounds(ano, mes)
    n_days = days_in_month(ano, mes)
    weeks = weeks_in_month(ano, mes)
    hoje = date.today()
    default_day = hoje if start <= hoje < end else start

    dk = _day_key(key_prefix, ano, mes)
    if dk not in st.session_state:
        st.session_state[dk] = default_day.isoformat()

    try:
        selected = date.fromisoformat(st.session_state[dk])
    except ValueError:
        selected = default_day
    if selected.month != mes or selected.year != ano:
        selected = default_day
        st.session_state[dk] = selected.isoformat()

    lente = st.segmented_control(
        "Período no mês da meta",
        ["Mensal", "Semanal", "Diário"],
        default=st.session_state.get(_lente_key(key_prefix), "Mensal"),
        key=f"{key_prefix}_lente_seg",
    )
    st.session_state[_lente_key(key_prefix)] = lente or "Mensal"
    lente = lente or "Mensal"

    week = week_for_date(ano, mes, selected)
    use_apply = defer_apply and key_prefix in ("rank", "colab")

    if lente in ("Semanal", "Diário"):
        _render_calendar_picker(
            ano, mes, selected, week, key_prefix, dk, defer_rerun=use_apply
        )
    pending = _pacing_snapshot(key_prefix, ano, mes, default_day)
    snap_key = _applied_snap_key(key_prefix)
    if snap_key not in st.session_state:
        st.session_state[snap_key] = dict(pending)

    if use_apply:
        dirty = pending != st.session_state[snap_key]
        btn_col, hint_col = st.columns([1, 2])
        with btn_col:
            if st.button(
                "Atualizar cards",
                type="primary" if dirty else "secondary",
                key=f"{key_prefix}_pacing_apply_{ano}_{mes}",
            ):
                st.session_state[snap_key] = dict(pending)
                st.rerun()
        with hint_col:
            if dirty:
                st.caption("Calendário alterado — clique **Atualizar cards**.")
        snap = st.session_state[snap_key]
    else:
        snap = pending

    try:
        selected_applied = date.fromisoformat(snap["day"])
    except ValueError:
        selected_applied = default_day
    if selected_applied.month != mes or selected_applied.year != ano:
        selected_applied = default_day

    return pacing_view_from_lente_day(ano, mes, snap["lente"], selected_applied)


def meta_drum_html(
    planejada: float,
    real_ajustada: float,
    modo: str,
    tone: str,
    fmt_fn,
) -> str:
    if modo != "Real" or abs(real_ajustada - planejada) < 0.5:
        return f'<div class="meta-drum-stack"><div class="meta-drum-main">{fmt_fn(planejada)}</div></div>'
    cls = "meta-drum-real"
    if tone == "behind":
        cls += " meta-drum-behind"
    elif tone == "ahead":
        cls += " meta-drum-ahead"
    return (
        f'<div class="meta-drum-stack {cls}">'
        f'<div class="meta-drum-sub">Planejado: {fmt_fn(planejada)}</div>'
        f'<div class="meta-drum-main">{fmt_fn(real_ajustada)}</div>'
        f"</div>"
    )
