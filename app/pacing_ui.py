"""Calendário + filtros de ritmo (mês / semana / dia)."""

from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import date, timedelta

import streamlit as st

from app.constants import MESES_NOME, label_mes
from app.dates_util import business_days_between, month_bounds
from app.pacing import (
    day_bounds,
    days_in_month,
    week_for_date,
    weeks_in_month,
)

_PACING_CSS = """
<style>
[class*="st-key-cal_box_"] {
    max-width: 360px; background: #fff; border: 1px solid #e3e9e6; border-radius: 16px;
    padding: 0.85rem 0.9rem 0.7rem; box-shadow: 0 6px 22px rgba(18, 38, 29, 0.07);
    gap: 0.15rem !important; margin: 0.4rem 0 0.6rem;
}
[class*="st-key-cal_box_"] .cal-head {
    display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.45rem;
}
[class*="st-key-cal_box_"] .cal-head strong { font-size: 1rem; color: #1f2d27; }
[class*="st-key-cal_box_"] .cal-head span { font-size: 0.72rem; color: #6b7a73; }
[class*="st-key-cal_box_"] .cal-wd {
    display: grid; grid-template-columns: repeat(7, 1fr); margin-bottom: 0.55rem;
}
[class*="st-key-cal_box_"] .cal-wd span {
    text-align: center; font-size: 0.68rem; color: #8a9891; font-weight: 600; text-transform: uppercase;
}
[class*="st-key-cal_box_"] [data-testid="stHorizontalBlock"] { gap: 0 !important; }
[class*="st-key-cal_box_"] [data-testid="stColumn"] { min-width: 0 !important; }
[class*="st-key-cal_box_"] button {
    min-height: 2.1rem !important; height: 2.1rem; padding: 0 !important; border: none !important;
    border-radius: 10px !important; font-size: 0.82rem !important; font-weight: 600 !important;
    transition: background 0.12s ease;
}
[class*="st-key-cal_box_"] button[kind="tertiary"] { background: transparent !important; color: #1f2d27; }
[class*="st-key-cal_box_"] button[kind="tertiary"]:hover { background: #eef2ef !important; }
[class*="st-key-cal_box_"] button[kind="secondary"] {
    background: #e3efe9 !important; color: #1f4d3a !important; border-radius: 0 !important;
}
[class*="st-key-cal_box_"] button[kind="primary"] {
    background: #2f6b55 !important; color: #fff !important; border-radius: 10px !important;
    box-shadow: 0 3px 10px rgba(47, 107, 85, 0.35) !important;
}
.meta-drum-stack { position: relative; min-height: 2.6rem; }
.meta-drum-main {
    font-size: 1.75rem; font-weight: 700; color: #0f3328;
    transition: transform 0.45s ease, opacity 0.35s ease;
}
.meta-drum-sub {
    font-size: 0.82rem; color: #6b7280; margin-top: 0.15rem;
    transition: transform 0.45s ease, opacity 0.35s ease;
}
.meta-drum-real .meta-drum-main { color: #1f4d3a; animation: meta-drum-in 0.5s ease; }
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
    peso_periodo: float = 1.0
    peso_acum: float = 1.0


def _pesos_dias_uteis(ano: int, mes: int, ini: date, fim_exclusive: date) -> tuple[float, float]:
    """Fração da meta do mês no período e do dia 1 até o fim do período (por dias úteis)."""
    start, end = month_bounds(ano, mes)
    total = business_days_between(start, end)
    if total <= 0:
        return 1.0, 1.0
    return (
        business_days_between(ini, fim_exclusive) / total,
        business_days_between(start, fim_exclusive) / total,
    )


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
        peso, peso_acum = _pesos_dias_uteis(ano, mes, week.ini, week.fim_exclusive)
        return PacingView(
            lente=lente,
            ini=week.ini,
            fim_exclusive=week.fim_exclusive,
            selected_day=selected,
            week_label=week.label,
            period_label=week.label,
            period_index=week.index,
            n_periods=len(weeks),
            peso_periodo=peso,
            peso_acum=peso_acum,
        )
    d_ini, d_fim = day_bounds(ano, mes, selected.day)
    peso, peso_acum = _pesos_dias_uteis(ano, mes, d_ini, d_fim)
    return PacingView(
        lente=lente,
        ini=d_ini,
        fim_exclusive=d_fim,
        selected_day=selected,
        week_label=week.label,
        period_label=selected.strftime("%d/%m/%Y"),
        period_index=selected.day - 1,
        n_periods=n_days,
        peso_periodo=peso,
        peso_acum=peso_acum,
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
    hoje = date.today()
    pad = _sunday_col(start)
    cells: list[int | None] = [None] * pad + list(range(1, n_days + 1))
    while len(cells) % 7 != 0:
        cells.append(None)

    def bkey(day_num: int, row_i: int) -> str:
        return f"{key_prefix}_cal_{ano}_{mes}_{day_num}_{row_i}"

    extra_css = []
    for row_i in range(0, len(cells), 7):
        semana = [
            c for c in cells[row_i:row_i + 7]
            if c and week.ini <= date(ano, mes, c) < week.fim_exclusive
        ]
        if semana:
            extra_css.append(
                f".st-key-{bkey(semana[0], row_i)} button{{border-radius:10px 0 0 10px !important}}"
                f".st-key-{bkey(semana[-1], row_i)} button{{border-radius:0 10px 10px 0 !important}}"
            )
        for col_i, c in enumerate(cells[row_i:row_i + 7]):
            if c and col_i in (0, 6):
                extra_css.append(f".st-key-{bkey(c, row_i)} button{{color:#9aa7a1 !important}}")
            if c and date(ano, mes, c) == hoje:
                extra_css.append(
                    f".st-key-{bkey(c, row_i)} button{{box-shadow:inset 0 -3px 0 #b7d96b !important}}"
                )

    wd_html = "".join(f"<span>{w}</span>" for w in _WD)
    with st.container(key=f"cal_box_{key_prefix}"):
        st.markdown(
            f"<style>{''.join(extra_css)}</style>"
            f'<div class="cal-head"><strong>{html.escape(MESES_NOME[mes])} {ano}</strong>'
            f"<span>{html.escape(week.label)} · dia {selected.day:02d}</span></div>"
            f'<div class="cal-wd">{wd_html}</div>',
            unsafe_allow_html=True,
        )
        for row_i in range(0, len(cells), 7):
            cols = st.columns(7, gap=None)
            for col_i, col in enumerate(cols):
                day_num = cells[row_i + col_i]
                if day_num is None:
                    continue
                d = date(ano, mes, day_num)
                if day_num == selected.day:
                    kind = "primary"
                elif week.ini <= d < week.fim_exclusive:
                    kind = "secondary"
                else:
                    kind = "tertiary"
                with col:
                    if st.button(
                        f"{day_num}",
                        key=bkey(day_num, row_i),
                        type=kind,
                        use_container_width=True,
                    ):
                        st.session_state[dk] = d.isoformat()
                        if not defer_rerun:
                            st.rerun()


def render_pacing_controls(
    ano: int,
    mes: int,
    key_prefix: str = "pacing",
    defer_apply: bool = True,
    always_calendar: bool = False,
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

    if always_calendar or lente in ("Semanal", "Diário"):
        _render_calendar_picker(
            ano, mes, selected, week, key_prefix, dk, defer_rerun=use_apply
        )
    pending = _pacing_snapshot(key_prefix, ano, mes, default_day)
    snap_key = _applied_snap_key(key_prefix)
    if snap_key not in st.session_state:
        st.session_state[snap_key] = dict(pending)

    if use_apply:
        dirty = pending != st.session_state[snap_key]
        if st.button(
            "Atualizar cards",
            type="primary" if dirty else "secondary",
            key=f"{key_prefix}_pacing_apply_{ano}_{mes}",
            icon=":material/refresh:",
            use_container_width=True,
        ):
            st.session_state[snap_key] = dict(pending)
            st.rerun()
        if dirty:
            st.caption("Período alterado — clique **Atualizar cards**.")
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
