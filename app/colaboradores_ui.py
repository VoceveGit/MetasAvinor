from __future__ import annotations

import streamlit as st

from app.constants import label_mes
from app.data import load_grid_metas_colaboradores, load_ranking_periodo
from app.dates_util import month_bounds
from app.equipe_grid_logic import aplicar_premissa_salva, loader_rows_to_state, premissa_tem_prescricao
from app.meta_resolve import resolve_meta_mes_cob
from app.formatting import fmt_brl_cell
from app.grid_snapshot import load_grid_snapshot, row_for_vendedor
from app.pacing_service import build_pacing_cob, build_pacing_fat, meta_periodo_display
from app.meta_proporcional import enrich_row_proporcional
from app.pacing_ui import PacingView, meta_drum_html, render_pacing_controls
from app.premissas import get_premissa, vendedor_tem_premissa

_COLAB_CSS = """
<style>
.colab-page { margin-top: 0.25rem; }
.colab-page h1.colab-title {
    font-size: 1.75rem; font-weight: 700; color: #1a3d32; margin: 0 0 0.25rem 0;
}
.colab-page .colab-sub { color: #6b7280; font-size: 0.95rem; margin-bottom: 1rem; }
.colab-hero-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1.5rem; align-items: stretch; }
@media (max-width: 900px) { .colab-hero-row { grid-template-columns: 1fr; } }
.colab-card-dark {
    background: linear-gradient(145deg, #1a4d3e 0%, #0f3328 100%);
    color: #fff; border-radius: 16px; padding: 1.35rem 1.45rem;
    box-shadow: 0 8px 24px rgba(15, 51, 40, 0.25);
}
.colab-card-dark.colab-card-stretch {
    min-height: 330px;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
}
.colab-card-spacer { flex: 1 1 auto; min-height: 1rem; }
.colab-realizado-col-marker {
    display: none !important;
    height: 0 !important;
}
div[data-testid="column"]:has(.colab-realizado-col-marker) {
    min-height: 332px !important;
    box-sizing: border-box !important;
}
div[data-testid="column"]:has(.colab-realizado-col-marker) .colab-card-dark.colab-card-stretch {
    min-height: 308px !important;
    height: 100% !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:has(.colab-ritmo-card-anchor) {
    background: #eef6e8 !important;
    border-color: #b8d4b0 !important;
    border-radius: 16px !important;
    padding: 0.35rem 0.5rem 0.5rem !important;
    min-height: 332px !important;
    box-sizing: border-box !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:has(.colab-ritmo-card-anchor) [data-testid="stSegmentedControl"] {
    margin: 0 !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:has(.colab-ritmo-card-anchor) [data-testid="stSegmentedControl"] > div {
    background: #d4e8cf !important;
    border-radius: 10px !important;
    padding: 3px !important;
    border: 1px solid #a8c9a0 !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:has(.colab-ritmo-card-anchor) [data-testid="stSegmentedControl"] button {
    border-radius: 8px !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    color: #1a4d3e !important;
    border: none !important;
    background: transparent !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:has(.colab-ritmo-card-anchor) [data-testid="stSegmentedControl"] button[aria-checked="true"],
[data-testid="stVerticalBlockBorderWrapper"]:has(.colab-ritmo-card-anchor) [data-testid="stSegmentedControl"] button[aria-pressed="true"] {
    background: #1a4d3e !important;
    color: #fff !important;
}
.colab-ritmo-card-anchor {
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
    border: 0 !important;
}
.colab-ritmo-card {
    color: #1a3d32;
    box-sizing: border-box;
}
.colab-light-head-inline {
    font-weight: 700;
    font-size: 1.05rem;
    color: #1a3d32;
    margin: 0;
    line-height: 1.3;
}
.colab-card-dark .tag-row {
    display: flex; justify-content: space-between; align-items: flex-start; gap: 0.5rem;
}
.colab-badge {
    font-size: 0.62rem; text-transform: uppercase; letter-spacing: 0.08em;
    font-weight: 700; padding: 0.25rem 0.5rem; border-radius: 6px;
    border: 1px solid rgba(255,255,255,0.35); opacity: 0.95;
}
.colab-card-dark .tag {
    font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.06em;
    opacity: 0.9; font-weight: 600;
}
.colab-big { font-size: 2.15rem; font-weight: 700; line-height: 1.1; margin: 0.4rem 0 0.25rem; }
.colab-footer-metrics {
    display: flex; justify-content: space-between; gap: 1rem; margin-top: 1.15rem;
    padding-top: 1rem; border-top: 1px solid rgba(255,255,255,0.22);
}
.colab-footer-metrics .fm-label {
    font-size: 0.92rem; opacity: 0.92; margin-bottom: 0.35rem; display: block;
}
.colab-footer-metrics .fm-value {
    font-size: 1.2rem; font-weight: 700; display: block;
}
.colab-light-head {
    display: flex; align-items: center; gap: 0.45rem; font-weight: 700;
    font-size: 1.05rem; color: #1a3d32; margin-bottom: 0.85rem;
}
.colab-light-body {
    display: grid; grid-template-columns: 148px 1fr; gap: 1rem; align-items: center;
}
@media (max-width: 500px) { .colab-light-body { grid-template-columns: 1fr; } }
.colab-ring {
    width: 140px; height: 140px; border-radius: 50%;
    background: conic-gradient(#1a4d3e var(--pct), #f5e6d8 0);
    display: flex; align-items: center; justify-content: center; margin: 0 auto;
}
.colab-ring-inner {
    width: 108px; height: 108px; border-radius: 50%; background: #eef6e8;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    font-weight: 700; font-size: 1.65rem; color: #1a4d3e; line-height: 1.1;
}
.colab-ring-inner span.sub { font-size: 0.72rem; font-weight: 500; color: #4b5563; margin-top: 0.15rem; }
.colab-meta-primary .mp-label { font-size: 0.88rem; color: #4b5563; margin-bottom: 0.2rem; }
.colab-meta-primary .mp-value { font-size: 1.75rem; font-weight: 700; color: #0f3328; }
.colab-meta-row {
    display: flex; justify-content: space-between; align-items: baseline;
    padding: 0.55rem 0; border-top: 1px solid #c5dcc0; font-size: 0.92rem;
}
.colab-meta-row .mr-val { font-weight: 700; font-size: 1.05rem; }
.colab-meta-row.dim .mr-val { font-weight: 600; color: #374151; }
.colab-meta-ref {
    margin-top: 0.65rem; font-size: 0.85rem; color: #4b5563;
    background: rgba(255,255,255,0.55); padding: 0.45rem 0.65rem; border-radius: 8px;
}
.colab-section-wrap {
    margin: 2rem 0 1rem 0;
    padding: 0.65rem 0.85rem;
    background: linear-gradient(90deg, #ebe4d8 0%, #f5efe3 100%);
    border-left: 4px solid #1a4d3e;
    border-radius: 0 10px 10px 0;
}
.colab-section-wrap .colab-section-num {
    font-size: 0.72rem; font-weight: 800; color: #1a4d3e; letter-spacing: 0.14em;
    text-transform: uppercase;
}
.colab-section-wrap .colab-section-title {
    font-size: 1.05rem; font-weight: 700; color: #1f2937; margin-top: 0.15rem;
}
.colab-section-wrap .colab-section-hint {
    font-size: 0.82rem; color: #6b7280; margin-top: 0.2rem;
}
.colab-grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-bottom: 1rem; }
@media (max-width: 1000px) { .colab-grid-3 { grid-template-columns: 1fr; } }
.colab-metric-card {
    background: #fff; border-radius: 14px; padding: 1.15rem 1.25rem;
    border: 1px solid #ebe3d5; box-shadow: 0 2px 12px rgba(92, 61, 46, 0.06);
}
.colab-metric-card .mc-head {
    display: flex; align-items: center; gap: 0.55rem; font-weight: 700;
    color: #1f2937; font-size: 1rem; margin-bottom: 0.75rem;
}
.colab-icon {
    width: 32px; height: 32px; border-radius: 10px; display: flex;
    align-items: center; justify-content: center; font-size: 1rem; flex-shrink: 0;
}
.colab-icon.blue { background: #dbeafe; color: #1d4ed8; }
.colab-icon.green { background: #d1fae5; color: #047857; }
.colab-icon.amber { background: #fef3c7; color: #b45309; }
.colab-metric-card .mc-big { font-size: 1.85rem; font-weight: 700; color: #111827; }
.colab-metric-card .mc-sub { font-size: 0.9rem; color: #6b7280; margin-top: 0.3rem; line-height: 1.35; }
.colab-flow {
    display: flex; align-items: stretch; gap: 0.5rem; margin: 0.85rem 0 0.65rem;
    background: #f8fafc; border-radius: 12px; padding: 0.65rem 0.75rem; border: 1px solid #e2e8f0;
}
.colab-flow .flow-box {
    flex: 1; text-align: center; padding: 0.35rem 0.25rem;
}
.colab-flow .flow-box.hl { background: #eff6ff; border-radius: 8px; border: 1px solid #bfdbfe; }
.colab-flow .flow-num { font-size: 1.15rem; font-weight: 800; color: #1e3a8a; display: block; }
.colab-flow .flow-lbl { font-size: 0.78rem; font-weight: 700; color: #374151; text-transform: uppercase; letter-spacing: 0.04em; }
.colab-flow .flow-hint { font-size: 0.72rem; color: #6b7280; margin: 0.25rem 0 0; line-height: 1.25; }
.colab-flow .flow-arrow {
    display: flex; align-items: center; font-size: 1.35rem; color: #3b82f6; font-weight: 700; padding: 0 0.15rem;
}
.colab-stat-row {
    display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.5rem;
}
.colab-stat-chip {
    flex: 1; min-width: 42%; background: #f3f4f6; border-radius: 8px; padding: 0.5rem 0.6rem;
    font-size: 0.85rem; color: #374151;
}
.colab-stat-chip strong { color: #111827; font-size: 0.95rem; }
.colab-legend {
    font-size: 0.78rem; color: #6b7280; margin-top: 0.55rem; line-height: 1.4;
    padding-top: 0.5rem; border-top: 1px dashed #e5e7eb;
}
.colab-bar-segs { margin: 0.55rem 0 0.35rem; }
.colab-hist-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; }
@media (max-width: 900px) { .colab-hist-row { grid-template-columns: 1fr; } }
.colab-hist-card {
    background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 0.9rem 1rem;
    display: flex; justify-content: space-between; align-items: center;
}
.colab-hist-card .val { font-size: 1.25rem; font-weight: 700; color: #111827; }
.colab-hist-card .lbl { font-size: 0.85rem; color: #6b7280; }
</style>
"""


def load_vendedor_grid_row(vid: int, ano: int, mes: int, taxa: float) -> dict | None:
    """Linha completa do vendedor (snapshot/premissas) — usada também no Ranking."""
    return _load_row(vid, ano, mes, taxa)


def _bar_segs(pct: float, fill: str = "#1a4d3e", empty: str = "#e5e7eb") -> str:
    pct = max(0.0, min(float(pct), 100.0))
    filled = int(round(pct / 10.0))
    return "".join(
        f'<span style="display:inline-block;width:8%;height:10px;margin-right:2px;border-radius:3px;'
        f'background:{fill if i < filled else empty};"></span>'
        for i in range(10)
    )


def _f(row: dict, key: str, default: float = 0.0) -> float:
    v = row.get(key)
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _load_row(vid: int, ano: int, mes: int, taxa: float) -> dict | None:
    snap_row = row_for_vendedor(ano, mes, vid)
    if snap_row:
        from app.equipe_grid_logic import recalc_row_formulas_only

        return enrich_row_proporcional(recalc_row_formulas_only(dict(snap_row), taxa), ano, mes)
    snap = load_grid_snapshot(ano, mes)
    if snap:
        for row in snap:
            if int(row.get("vendedor", 0)) == vid:
                from app.equipe_grid_logic import recalc_row_formulas_only

                return enrich_row_proporcional(
                    recalc_row_formulas_only(dict(row), taxa), ano, mes
                )
    df = load_grid_metas_colaboradores(ano, mes, taxa)
    row_df = df.loc[df["vendedor"] == vid]
    if row_df.empty:
        return None
    state = loader_rows_to_state(row_df, ano, mes, taxa)
    row = aplicar_premissa_salva(state[0], ano, mes, taxa)
    return enrich_row_proporcional(row, ano, mes)


def _meta_em_uso(meta_man: float, meta_calc: float, modo: str) -> float:
    if modo == "Manual" and meta_man > 0:
        return meta_man
    if meta_calc > 0:
        return meta_calc
    return meta_man


def _section_header(num: str, title: str, hint: str) -> None:
    st.markdown(
        f"""
        <div class="colab-section-wrap">
          <div class="colab-section-num">{num}</div>
          <div class="colab-section-title">{title}</div>
          <div class="colab-section-hint">{hint}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_hero_v2(
    meta_calc: float,
    meta_man: float,
    meta_prop: float,
    vendedor_id: int,
    view: PacingView,
    modo: str,
    toggle_key: str,
    cob_meta_mes: int,
    cob_prop: int | None = None,
):
    """Hero: origem da meta + acumulado (igual Ranking)."""
    col_l, col_r = st.columns(2, gap="medium")
    meta_opts = ["Manual", "Calculada"]
    if meta_prop > 0:
        meta_opts.append("Proporcional")

    with col_r:
        ritmo_card = st.container(border=True)
        with ritmo_card:
            st.markdown('<div class="colab-ritmo-card-anchor"></div>', unsafe_allow_html=True)
            st.markdown(
                '<p class="colab-light-head-inline">🎯 Ritmo da meta</p>',
                unsafe_allow_html=True,
            )
            meta_sel = st.segmented_control(
                "Origem da meta",
                meta_opts,
                default=modo if modo in meta_opts else meta_opts[0],
                key=f"{toggle_key}_meta",
            )
            acumulado = st.checkbox(
                "Acumulado do mês",
                value=False,
                disabled=view.lente == "Mensal",
                key=f"{toggle_key}_acum",
            )

    meta_ref = meta_sel or modo
    row_stub = {
        "meta_prop_mes_rs": meta_prop,
        "cob_prop_sug": cob_prop,
        "cobertura_meta_clientes": cob_meta_mes,
        "tx_conv_projetada_pct": 0,
        "cobertura_meta_pct": 0,
    }
    meta_mes_prescrita, _, cob_uso = resolve_meta_mes_cob(
        meta_ref if meta_ref in meta_opts else "Manual",
        row_stub,
        meta_man,
        meta_calc,
        0,
    )
    if cob_uso <= 0:
        cob_uso = cob_meta_mes
    modo_pacing = (
        "Real"
        if acumulado and view.lente in ("Semanal", "Diário")
        else "Calculada"
    )
    modo_atual = meta_ref
    pf = build_pacing_fat(meta_mes_prescrita, view, vendedor_id, modo_pacing)
    pc = build_pacing_cob(cob_uso, view, vendedor_id, modo_pacing)
    meta_periodo = meta_periodo_display(meta_mes_prescrita, modo_pacing, view.lente, pf)
    real = pf.realizado_periodo
    ating = (real / meta_periodo * 100) if meta_periodo > 0 else 0
    falta = max(meta_periodo - real, 0)
    pct_style = f"--pct: {min(ating, 100):.1f}%;"

    real_label = {
        "Mensal": "Realizado no mês",
        "Semanal": f"Realizado · {view.period_label}",
        "Diário": f"Realizado · {view.period_label}",
    }[view.lente]
    planejada_periodo = meta_periodo_display(
        meta_mes_prescrita,
        "Manual" if meta_man > 0 else "Calculada",
        view.lente,
        pf,
    )
    if acumulado and view.lente in ("Semanal", "Diário"):
        meta_periodo_html = meta_drum_html(
            planejada_periodo,
            meta_periodo,
            "Real",
            pf.ajuste_tone,
            fmt_brl_cell,
        )
    else:
        meta_periodo_html = (
            f'<div class="meta-drum-stack"><div class="meta-drum-main">'
            f'{fmt_brl_cell(meta_periodo) if meta_periodo > 0 else "—"}</div></div>'
        )

    uso_label = f"Meta do período ({modo_atual.lower()})"
    primary_label = "Meta prescrita do mês"
    secondary_label = "Meta planejada no período"
    planejada_show = planejada_periodo

    with col_l:
        st.markdown('<div class="colab-realizado-col-marker"></div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="colab-card-dark colab-card-stretch">
              <div class="tag-row">
                <div class="tag">💼 {real_label}</div>
                <div class="colab-badge">{view.lente}</div>
              </div>
              <div class="colab-big">{fmt_brl_cell(real)}</div>
              <div style="font-size:0.92rem;opacity:0.92;">{view.period_label}</div>
              <div class="colab-card-spacer"></div>
              <div class="colab-footer-metrics">
                <div>
                  <span class="fm-label">{uso_label}</span>
                  <span class="fm-value">{fmt_brl_cell(meta_periodo) if meta_periodo > 0 else "—"}</span>
                </div>
                <div style="text-align:right;">
                  <span class="fm-label">Falta no período</span>
                  <span class="fm-value">{fmt_brl_cell(falta) if meta_periodo > 0 else "—"}</span>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    ajuste_html = ""
    if view.lente != "Mensal" and pf.ajuste_label:
        ajuste_html = f'<div class="colab-meta-ref">{pf.ajuste_label}</div>'

    with ritmo_card:
        st.markdown(
            f"""
            <div class="colab-ritmo-card">
              <div class="colab-light-body">
                <div class="colab-ring" style="{pct_style}">
                  <div class="colab-ring-inner">
                    <span>{ating:.0f}%</span>
                    <span class="sub">do período</span>
                  </div>
                </div>
                <div>
                  <div class="colab-meta-primary">
                    <div class="mp-label">{primary_label}</div>
                    <div class="mp-value">{fmt_brl_cell(meta_mes_prescrita) if meta_mes_prescrita > 0 else "—"}</div>
                  </div>
                  <div class="colab-meta-row dim">
                    <span>Meta no período</span>
                  </div>
                  {meta_periodo_html}
                  <div class="colab-meta-row dim">
                    <span>{secondary_label}</span>
                    <span class="mr-val">{fmt_brl_cell(planejada_show) if planejada_show > 0 else "—"}</span>
                  </div>
                  <div class="colab-meta-row dim">
                    <span>Cobertura no período</span>
                    <span class="mr-val">{pc.clientes_periodo} / {pc.meta_periodo_planejada:.0f}</span>
                  </div>
                  {ajuste_html}
                  <div class="colab-meta-ref">
                    Modo <strong>{modo_atual}</strong> · {view.lente.lower()}.
                    Ticket médio segue o prescrito do mês (comparado ao realizado no período).
                  </div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_caminho(r: dict):
    cart = int(_f(r, "carteira"))
    oport = int(_f(r, "oportunidades_mes"))
    ocalc = int(_f(r, "oport_calc_pos"))
    conv = _f(r, "conv_meta_pct")
    tx_hist = _f(r, "tx_conv_hist_pct")
    cob = int(_f(r, "cobertura_meta_clientes"))
    tx_proj = _f(r, "tx_conv_projetada_pct")
    dif = int(_f(r, "diff_carteira_cob"))
    cob_media = _f(r, "cob_media_clientes_3m")
    ticket = _f(r, "ticket_meta")
    ticket_hist = _f(r, "ticket_historico")
    dif_ticket = ticket - ticket_hist if ticket > 0 and ticket_hist > 0 else 0
    pct_ticket = (dif_ticket / ticket_hist * 100) if ticket_hist > 0 else 0
    pct_cob = (cob / cart * 100) if cart > 0 and cob > 0 else 0
    bar_segs = _bar_segs(pct_cob)
    clientes_mes = int(_f(r, "clientes_mes"))
    pct_oport = (clientes_mes / ocalc * 100) if ocalc > 0 else 0
    if ocalc <= 0 and conv > 0 and tx_hist > 0:
        pct_oport = min(tx_hist / conv * 100, 100)
    bar_oport = _bar_segs(pct_oport, fill="#1d4ed8", empty="#e5e7eb")
    real_mes = _f(r, "realizado_mes")
    ticket_real = (real_mes / clientes_mes) if clientes_mes > 0 and real_mes > 0 else 0
    if ticket > 0 and ticket_real > 0:
        pct_ticket_prog = min(ticket_real / ticket * 100, 100)
        ticket_prog_lbl = (
            f"Ticket do mês {fmt_brl_cell(ticket_real)} vs meta {fmt_brl_cell(ticket)} "
            f"({pct_ticket_prog:.0f}%)"
        )
    elif ticket > 0 and ticket_hist > 0:
        pct_ticket_prog = min(ticket_hist / ticket * 100, 100)
        ticket_prog_lbl = (
            f"Histórico {fmt_brl_cell(ticket_hist)} vs prescrito {fmt_brl_cell(ticket)} "
            f"({pct_ticket_prog:.0f}%)"
        )
    else:
        pct_ticket_prog = 0
        ticket_prog_lbl = "Defina o ticket no Início para acompanhar."
    bar_ticket = _bar_segs(pct_ticket_prog, fill="#b45309", empty="#e5e7eb")
    oport_prog_lbl = (
        f"Positivações no mês ({clientes_mes:,}) vs calculadas ({ocalc:,}) — {pct_oport:.0f}%"
        if ocalc > 0
        else f"Conversão histórica {tx_hist:.1f}% vs meta {conv:.1f}%"
    )

    _section_header(
        "01",
        "O caminho até o resultado",
        "Como as premissas do Início (azuis) viram meta em R$: oportunidade → cobertura → ticket × recorrência.",
    )
    st.markdown(
        f"""
        <div class="colab-grid-3">
          <div class="colab-metric-card">
            <div class="mc-head">
              <span class="colab-icon blue">◆</span> Oportunidades
            </div>
            <div class="mc-big">{oport:,}</div>
            <div class="mc-sub">Leads na carteira (rotas + base ativa).</div>
            <div class="colab-flow">
              <div class="flow-box">
                <span class="flow-num">{oport:,}</span>
                <span class="flow-lbl">Identificadas</span>
                <p class="flow-hint">Volume bruto de oportunidades no mês</p>
              </div>
              <div class="flow-arrow">→</div>
              <div class="flow-box hl">
                <span class="flow-num">{ocalc:,}</span>
                <span class="flow-lbl">Calculadas</span>
                <p class="flow-hint">Oport. × conversão % que você prescreveu</p>
              </div>
            </div>
            <div class="colab-bar-segs">{bar_oport}</div>
            <div class="mc-sub" style="margin-top:0.25rem;">{oport_prog_lbl}</div>
            <div class="colab-stat-row">
              <div class="colab-stat-chip">TX conv. histórica <strong>{tx_hist:.2f}%</strong></div>
              <div class="colab-stat-chip">Conversão meta <strong>{conv:.1f}%</strong></div>
            </div>
            <div class="colab-legend">
              <strong>Identificadas</strong> vêm do motor (histórico/rotas).
              <strong>Calculadas</strong> = cobertura × recorrência (ex.: 30 clientes × 2 itens = 60), só na carteira ativa.
            </div>
          </div>
          <div class="colab-metric-card">
            <div class="mc-head">
              <span class="colab-icon green">◎</span> Cobertura da carteira
            </div>
            <div class="mc-big">{cob} / {cart}</div>
            <div class="mc-sub">Clientes que você pretende visitar/vender na carteira de {cart}.</div>
            <div class="colab-bar-segs">{bar_segs}</div>
            <div class="mc-sub">{pct_cob:.0f}% da carteira · <strong>{dif}</strong> clientes acima da meta de cobertura</div>
            <div class="colab-stat-row">
              <div class="colab-stat-chip">Cobertura média 3m <strong>{cob_media:.0f}</strong></div>
              <div class="colab-stat-chip">TX conv. projetada <strong>{tx_proj:.0f}%</strong></div>
            </div>
            <div class="colab-legend">
              <strong>Cobertura</strong> = carteira × TX projetada. A <strong>diferença</strong> mostra folga
              ou gap versus o tamanho da carteira.
            </div>
          </div>
          <div class="colab-metric-card">
            <div class="mc-head">
              <span class="colab-icon amber">₿</span> Valor de cada venda
            </div>
            <div class="mc-big">{fmt_brl_cell(ticket) if ticket > 0 else "—"}</div>
            <div class="mc-sub">Ticket médio que você definiu para o mês.</div>
            <div class="colab-bar-segs">{bar_ticket}</div>
            <div class="mc-sub" style="margin-top:0.25rem;">{ticket_prog_lbl}</div>
            <div class="colab-stat-row">
              <div class="colab-stat-chip">Ticket histórico <strong>{fmt_brl_cell(ticket_hist)}</strong></div>
              <div class="colab-stat-chip">Variação <strong>{pct_ticket:+.1f}%</strong></div>
            </div>
            <div class="colab-stat-row">
              <div class="colab-stat-chip">Diferença R$ <strong>{fmt_brl_cell(dif_ticket)}</strong></div>
            </div>
            <div class="colab-legend">
              Compare o ticket <strong>prescrito</strong> com o <strong>histórico 3 meses</strong> para ver se a meta é agressiva ou conservadora.
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_historico(r: dict):
    fat = _f(r, "faturamento_media_3m") or _f(r, "fat_media_3m")
    pos = _f(r, "positivacao_media_3m")
    tx_cob = _f(r, "cobertura_hist_pct")
    rec = _f(r, "recorrencia_media")
    rec_meta = _f(r, "recorrencia_meta")
    real = _f(r, "realizado_mes")
    _section_header(
        "02",
        "Sua base histórica",
        "Referência dos últimos meses — não é meta, serve para calibrar o que você prescreveu.",
    )
    st.markdown(
        f"""
        <div class="colab-hist-row">
          <div class="colab-hist-card">
            <div><div class="lbl">Faturamento médio</div><div class="val">{fmt_brl_cell(fat)}</div></div>
            <span class="lbl">MÉDIA 3M</span>
          </div>
          <div class="colab-hist-card">
            <div><div class="lbl">Positivação média</div><div class="val">{pos:,.0f}</div></div>
            <span class="lbl">HISTÓRICO</span>
          </div>
          <div class="colab-hist-card">
            <div><div class="lbl">TX cobertura (média)</div><div class="val">{tx_cob:.1f}%</div></div>
            <span class="lbl">HISTÓRICO</span>
          </div>
        </div>
        <div class="colab-hist-row" style="margin-top:0.75rem;">
          <div class="colab-hist-card">
            <div><div class="lbl">Recorrência média</div><div class="val">{rec:.1f}</div></div>
            <span class="lbl">itens ÷ clientes (carteira)</span>
          </div>
          <div class="colab-hist-card">
            <div><div class="lbl">Recorrência meta</div><div class="val">{rec_meta:.1f}</div></div>
            <span class="lbl">PRESCRITO</span>
          </div>
          <div class="colab-hist-card">
            <div><div class="lbl">Realizado (mês)</div><div class="val">{fmt_brl_cell(real)}</div></div>
            <span class="lbl">ERP</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_aba_colaboradores(ano: int, mes: int, taxa: float) -> None:
    from app.main import APP_VERSION

    st.markdown(_COLAB_CSS, unsafe_allow_html=True)
    st.caption(f"Layout colaboradores · **v{APP_VERSION}**")
    st.markdown(
        f"""
        <div class="colab-page">
          <h1 class="colab-title">Pessoas &amp; resultados</h1>
          <p class="colab-sub">Desempenho em perspectiva · {label_mes(ano, mes)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    ini, fim = month_bounds(ano, mes)
    ranking = load_ranking_periodo(ini, fim, 120)
    if ranking.empty:
        st.info("Sem faturamento no mês para listar colaboradores.")
        return

    opcoes = [f"{int(r.vendedor):03d} — {r.nome}" for r in ranking.itertuples()]
    escolha = st.selectbox("Colaborador", opcoes, key=f"colab_sel_{ano}_{mes}")
    vid = int(escolha.split(" — ")[0])

    r = _load_row(vid, ano, mes, taxa)
    if r is None:
        st.warning("Colaborador sem linha na tabela de metas (sem movimento no mês?).")
        return

    prem = get_premissa(vid, ano, mes)
    if vendedor_tem_premissa(vid, ano, mes) and not premissa_tem_prescricao(prem):
        st.warning(
            "Há registro salvo, mas sem valores prescritos — salve a tabela no **Início**."
        )

    meta_calc = float(r.get("meta_formula") or 0)
    meta_man = float(r.get("meta_manual") or 0)
    default_modo = "Manual" if meta_man > 0 else "Calculada"
    toggle_key = f"colab_ritmo_{ano}_{mes}_{vid}"
    cob_meta = int(_f(r, "cobertura_meta_clientes"))

    view = render_pacing_controls(ano, mes, "colab")
    meta_prop = float(r.get("meta_prop_mes_rs") or 0)
    cob_prop = r.get("cob_prop_sug")
    _render_hero_v2(
        meta_calc,
        meta_man,
        meta_prop,
        vid,
        view,
        default_modo,
        toggle_key,
        cob_meta,
        cob_prop=int(cob_prop) if cob_prop is not None else None,
    )
    _render_caminho(r)
    _render_historico(r)

    st.caption(
        "Dados da tabela salva no Início (ou ERP se ainda não salvou). "
        "Premissas em `premissas_local.json` + snapshot em `grid_snapshot_local.json`."
    )
