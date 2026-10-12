"""Acompanhamento realizado vs premissas salvas (Ranking)."""

from __future__ import annotations

import html
import pandas as pd
import streamlit as st

from app.colaboradores_ui import load_vendedor_grid_row
from app.data import load_vendedor_realizado_intervalo
from app.pacing_service import (
    build_pacing_cob,
    build_pacing_fat,
    build_pacing_fat_equipe,
    meta_periodo_display,
)
from app.pacing_ui import PacingView, render_pacing_controls
from app.constants import label_mes
from app.data import (
    load_grid_metas_colaboradores,
    load_ranking_periodo,
    load_realizado_vendedores_batch,
    load_tops_ranking_batch,
    meta_vendedor_periodo_mes,
)
from app.equipe_grid_logic import (
    aplicar_premissa_salva,
    premissa_tem_prescricao,
    recalc_row_formulas_only,
)
from app.grid_snapshot import load_grid_snapshot
from app.dates_util import month_bounds
from app.formatting import fmt_brl_cell, fmt_pct_table
from app.meta_proporcional import aplicar_colunas_proporcionais, meta_empresa_mensal_ref
from app.meta_resolve import resolve_meta_mes_cob
from app.premissas import get_premissa, get_premissa_empresa, vendedor_tem_premissa
from app.table_display import show_data_table
from datetime import date


def _ticket_realizado_interval(
    view: PacingView,
    acumulado: bool,
    m_ini: date,
    m_fim: date,
) -> tuple[date, date, str]:
    """
    Ticket médio = faturamento ÷ vendas (notas), no mesmo recorte do realizado exibido.
    Meta de ticket é mensal — não divide por semana.
    """
    if view.lente == "Mensal":
        return m_ini, m_fim, "Mês"
    if acumulado:
        return m_ini, view.fim_exclusive, "Acum."
    return view.ini, view.fim_exclusive, "Período"


def _ticket_realizado_valor(iv: dict) -> float:
    fat = float(iv.get("faturamento") or 0)
    if fat <= 0:
        return 0.0
    notas = int(iv.get("notas") or 0)
    clientes = int(iv.get("clientes") or 0)
    denom = notas if notas > 0 else clientes
    return fat / denom if denom > 0 else 0.0


def _metrics_from_cache(
    vid: int,
    ini: date,
    fim: date,
    metrics_cache: dict,
) -> dict:
    key = (vid, ini.isoformat(), fim.isoformat())
    if key in metrics_cache:
        return metrics_cache[key]
    m = load_vendedor_realizado_intervalo(vid, ini, fim)
    metrics_cache[key] = m
    return m


_RANK_CSS = """
<style>
.rank-page { margin-top: 0.25rem; }
.rank-empresa-hero {
    background: linear-gradient(145deg, #1a4d3e 0%, #0f3328 100%);
    color: #fff; border-radius: 16px; padding: 1.35rem 1.5rem;
    box-shadow: 0 8px 24px rgba(15, 51, 40, 0.22);
    margin-bottom: 1.25rem;
    display: grid; grid-template-columns: 1fr 200px; gap: 1.25rem; align-items: center;
}
@media (max-width: 800px) { .rank-empresa-hero { grid-template-columns: 1fr; } }
.rank-empresa-hero .re-tag {
    font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.08em; opacity: 0.9;
}
.rank-empresa-hero .re-big { font-size: 2rem; font-weight: 700; margin: 0.35rem 0; }
.rank-empresa-hero .re-row {
    display: flex; flex-wrap: wrap; gap: 1.25rem; margin-top: 0.85rem;
    padding-top: 0.85rem; border-top: 1px solid rgba(255,255,255,0.2);
}
.rank-empresa-hero .re-metric span { display: block; font-size: 0.85rem; opacity: 0.9; }
.rank-empresa-hero .re-metric strong { font-size: 1.15rem; }
.rank-ring {
    width: 168px; height: 168px; border-radius: 50%; margin: 0 auto;
    background: conic-gradient(#86efac var(--pct), rgba(255,255,255,0.15) 0);
    display: flex; align-items: center; justify-content: center;
}
.rank-ring-inner {
    width: 130px; height: 130px; border-radius: 50%; background: #0f3328;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    font-weight: 700; font-size: 1.75rem; line-height: 1.1;
}
.rank-ring-inner span.sub { font-size: 0.72rem; font-weight: 500; opacity: 0.85; margin-top: 0.2rem; }
.rank-section-title {
    font-size: 1.05rem; font-weight: 700; color: #1a3d32; margin: 1.25rem 0 0.75rem;
}
.rank-grid {
    display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; margin-bottom: 1rem;
}
@media (max-width: 960px) { .rank-grid { grid-template-columns: 1fr; } }
.rank-vend-card {
    background: #fff; border: 1px solid #ebe3d5; border-radius: 14px;
    padding: 1.1rem 1.2rem; box-shadow: 0 2px 12px rgba(92, 61, 46, 0.06);
}
.rank-vend-card .rv-head {
    display: flex; justify-content: space-between; align-items: flex-start; gap: 0.5rem;
    margin-bottom: 0.65rem;
}
.rank-vend-card .rv-name { font-size: 1.05rem; font-weight: 700; color: #111827; }
.rank-vend-card .rv-cod { font-size: 0.75rem; color: #6b7280; font-weight: 600; }
.rank-vend-card .rv-part {
    font-size: 0.72rem; font-weight: 700; color: #1a4d3e; background: #eef6e8;
    padding: 0.2rem 0.45rem; border-radius: 6px; white-space: nowrap;
}
.rank-vend-card .rv-meta-line {
    font-size: 0.88rem; color: #4b5563; margin-bottom: 0.35rem;
}
.rank-vend-card .rv-meta-line strong { color: #0f3328; font-size: 1.05rem; }
.rank-vend-card .rv-falta { font-size: 0.82rem; color: #6b7280; margin: 0.35rem 0 0.65rem; }
.rank-vend-card .rv-block-title {
    font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em;
    color: #6b7280; font-weight: 700; margin: 0.65rem 0 0.35rem;
}
.rank-vend-card .rv-cob-line { font-size: 0.85rem; color: #374151; margin-top: 0.25rem; }
.rank-vend-card .rv-ref { font-size: 0.75rem; color: #9ca3af; margin-top: 0.5rem; }
.rank-vend-card.warn { border-color: #fcd34d; background: #fffbeb; }
.rank-vend-card .rv-rings {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.5rem;
    margin: 0.65rem 0 0.5rem; align-items: start;
}
@media (max-width: 520px) {
    .rank-vend-card .rv-rings { grid-template-columns: 1fr; }
}
.rv-ring-wrap { text-align: center; }
.rv-ring {
    width: 88px; height: 88px; border-radius: 50%; margin: 0 auto;
    background: conic-gradient(var(--ring-color, #1a4d3e) var(--pct), #e5e7eb 0);
    display: flex; align-items: center; justify-content: center;
}
.rv-ring-inner {
    width: 68px; height: 68px; border-radius: 50%; background: #fff;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    font-weight: 700; font-size: 1.05rem; color: #1a4d3e; line-height: 1.1;
}
.rv-ring-inner span.sub {
    font-size: 0.58rem; font-weight: 600; color: #6b7280; margin-top: 0.12rem;
    text-transform: uppercase; letter-spacing: 0.03em;
}
.rv-ring-lbl {
    font-size: 0.72rem; font-weight: 700; color: #6b7280; margin-top: 0.35rem;
    text-transform: uppercase; letter-spacing: 0.04em;
}
.rv-ring-detail { font-size: 0.75rem; color: #4b5563; margin-top: 0.2rem; line-height: 1.35; }
.rank-vend-card .rv-tops {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.65rem;
    margin-top: 0.85rem; padding-top: 0.75rem; border-top: 1px dashed #e5e7eb;
}
@media (max-width: 700px) {
    .rank-vend-card .rv-tops { grid-template-columns: 1fr; }
}
.rv-top-col .rv-top-title {
    font-size: 0.68rem; font-weight: 800; text-transform: uppercase;
    letter-spacing: 0.06em; color: #6b7280; margin-bottom: 0.35rem;
}
.rv-top-list { margin: 0; padding-left: 1.1rem; font-size: 0.78rem; color: #374151; }
.rv-top-list li { margin-bottom: 0.28rem; line-height: 1.3; }
.rv-top-list .rv-top-val { font-weight: 700; color: #1a4d3e; }
.rv-top-empty { font-size: 0.78rem; color: #9ca3af; }
</style>
"""


def _top_col_html(title: str, rows: list[tuple[str, str]]) -> str:
    if not rows:
        return (
            f'<div class="rv-top-col"><div class="rv-top-title">{html.escape(title)}</div>'
            f'<div class="rv-top-empty">Sem dados no mês</div></div>'
        )
    items = "".join(
        f'<li>{html.escape(name)} — <span class="rv-top-val">{html.escape(val)}</span></li>'
        for name, val in rows
    )
    return (
        f'<div class="rv-top-col"><div class="rv-top-title">{html.escape(title)}</div>'
        f'<ol class="rv-top-list">{items}</ol></div>'
    )


def _clip_label(text: str, max_len: int = 26) -> str:
    t = str(text).strip()
    return t if len(t) <= max_len else t[: max_len - 1] + "…"


def _mini_ring(pct: float, color: str = "#1a4d3e") -> str:
    p = max(0.0, min(float(pct), 100.0))
    return f'--pct: {p:.1f}%; --ring-color: {color};'


def _vend_card_html(c: dict, meta_emp: float) -> str:
    meta = c["meta_uso"]
    real = c["realizado"]
    ating = c["ating"]
    part_label = f"{c['part_emp']:.1f}% da meta empresa" if meta_emp > 0 else "—"
    warn = "" if c["tem_premissa"] and meta > 0 else " warn"
    nome = html.escape(str(c["nome"])[:42])
    acum = bool(c.get("acumulado"))
    pref = "Acumulado " if acum else ""
    cob_txt = (
        f"{pref}{c['clientes_mes']} / {c['cob_meta']} clientes · faltam <strong>{c['falta_cob']}</strong>"
        if c["cob_meta"] > 0
        else "Cobertura não prescrita no Início."
    )
    ajuste = c.get("ajuste_label") or ""
    ajuste_html = (
        f'<div class="rv-ring-detail" style="margin-top:0.35rem;">{html.escape(ajuste)}</div>'
        if ajuste
        else ""
    )
    pct_fat = min(ating, 100)
    pct_cob = min(c["pct_cob"], 100)
    pct_ticket = min(c.get("pct_ticket") or 0, 100)
    ticket_meta = c.get("ticket_meta") or 0
    ticket_real = c.get("ticket_real") or 0
    if ticket_meta > 0:
        t_lbl = html.escape(str(c.get("ticket_periodo_label") or "Mês"))
        ticket_detail = (
            f"{t_lbl} <strong>{html.escape(fmt_brl_cell(ticket_real))}</strong> "
            f"· meta <strong>{html.escape(fmt_brl_cell(ticket_meta))}</strong>"
        )
    else:
        ticket_detail = "Ticket não prescrito no Início."
    tops = (
        _top_col_html("Top clientes", c.get("top_clientes") or [])
        + _top_col_html("Top produtos", c.get("top_produtos") or [])
        + _top_col_html("Top cidades", c.get("top_cidades") or [])
    )
    return f"""<div class="rank-vend-card{warn}">
<div class="rv-head">
<div><div class="rv-name">{nome}</div><div class="rv-cod">Cód. {c['vendedor']:03d}</div></div>
<span class="rv-part">{html.escape(part_label)}</span>
</div>
<div class="rv-meta-line">Realizado <strong>{html.escape(fmt_brl_cell(real))}</strong>
· Meta ({html.escape(str(c['meta_tipo']) + (" · acum." if c.get("acumulado") else ""))}) <strong>{html.escape(fmt_brl_cell(meta) if meta > 0 else "—")}</strong></div>
<div class="rv-rings">
<div class="rv-ring-wrap">
<div class="rv-ring" style="{_mini_ring(pct_fat)}">
<div class="rv-ring-inner"><span>{pct_fat:.0f}%</span><span class="sub">meta R$</span></div>
</div>
<div class="rv-ring-lbl">Faturamento</div>
<div class="rv-ring-detail">Falta <strong>{html.escape(fmt_brl_cell(c['falta']) if meta > 0 else "—")}</strong></div>
{ajuste_html}
</div>
<div class="rv-ring-wrap">
<div class="rv-ring" style="{_mini_ring(pct_ticket, '#b45309')}">
<div class="rv-ring-inner"><span>{pct_ticket:.0f}%</span><span class="sub">ticket</span></div>
</div>
<div class="rv-ring-lbl">Ticket médio</div>
<div class="rv-ring-detail">{ticket_detail}</div>
</div>
<div class="rv-ring-wrap">
<div class="rv-ring" style="{_mini_ring(pct_cob, '#047857')}">
<div class="rv-ring-inner"><span>{pct_cob:.0f}%</span><span class="sub">carteira</span></div>
</div>
<div class="rv-ring-lbl">Cobertura</div>
<div class="rv-ring-detail">{cob_txt}</div>
</div>
</div>
<div class="rv-tops">{tops}</div>
</div>"""


def _pct_ating(real: float, meta: float) -> float | None:
    if meta <= 0:
        return None
    return min(real / meta * 100.0, 999.0)


def _meta_em_uso(meta_man: float, meta_calc: float) -> tuple[float, str]:
    if meta_man > 0:
        return meta_man, "manual"
    if meta_calc > 0:
        return meta_calc, "calculada"
    return 0.0, "—"


def load_acompanhamento_mes(ano: int, mes: int, taxa: float) -> pd.DataFrame:
    ini, fim = month_bounds(ano, mes)
    rank = load_ranking_periodo(ini, fim, 80)
    if rank.empty:
        return pd.DataFrame()

    grid = load_grid_metas_colaboradores(ano, mes, taxa)
    grid_by = {int(r.vendedor): r for r in grid.itertuples()} if not grid.empty else {}

    rows = []
    for r in rank.itertuples():
        vid = int(r.vendedor)
        real = float(r.faturamento)
        meta = meta_vendedor_periodo_mes(
            vid,
            ano,
            mes,
            taxa,
            faturamento_mes=real,
            carteira=int(r.carteira) if pd.notna(r.carteira) else None,
            clientes_mes=int(r.clientes),
        )
        prem = get_premissa(vid, ano, mes)
        conv_p = prem.conversao_meta_pct if prem.conversao_meta_pct > 0 else None
        tx_proj = prem.tx_conv_projetada_pct if prem.tx_conv_projetada_pct > 0 else None
        if tx_proj is None and prem.cobertura_meta_pct > 0:
            tx_proj = prem.cobertura_meta_pct
        g = grid_by.get(vid)
        if conv_p is None and g is not None:
            v = getattr(g, "conv_meta_pct", None)
            if v is not None and not pd.isna(v) and float(v) > 0:
                conv_p = float(v)
        if tx_proj is None and g is not None:
            v = getattr(g, "tx_conv_projetada_pct", None)
            if v is not None and not pd.isna(v) and float(v) > 0:
                tx_proj = float(v)

        cob_real = float(r.tx_cobertura) * 100 if pd.notna(r.tx_cobertura) else None
        ating = _pct_ating(real, meta)

        rows.append(
            {
                "vendedor": vid,
                "nome": r.nome,
                "tem_premissa": premissa_tem_prescricao(prem),
                "realizado": real,
                "meta_rs": meta,
                "ating_meta_pct": ating,
                "conv_meta_pct": float(conv_p) if conv_p is not None else None,
                "tx_proj_pct": float(tx_proj) if tx_proj is not None else None,
                "cobertura_real_pct": cob_real,
            }
        )
    return pd.DataFrame(rows)


def _collect_vendedor_cards(
    ano: int,
    mes: int,
    taxa: float,
    view: PacingView,
    meta_ref: str,
    acumulado: bool,
    include_tops: bool = False,
) -> list[dict]:
    m_ini, m_fim = month_bounds(ano, mes)
    p_ini, p_fim = view.ini, view.fim_exclusive
    rank = load_ranking_periodo(m_ini, m_fim, 120)
    if rank.empty:
        return []

    emp = get_premissa_empresa(ano, mes)
    meta_emp = meta_empresa_mensal_ref(emp)
    vids_pre = [int(r.vendedor) for r in rank.itertuples()]
    ids_t = tuple(vids_pre)
    metrics_cache: dict = {}
    if ids_t:
        for vid, m in load_realizado_vendedores_batch(ids_t, p_ini, p_fim).items():
            metrics_cache[(vid, p_ini.isoformat(), p_fim.isoformat())] = m
        if acumulado and view.lente in ("Semanal", "Diário"):
            for vid, m in load_realizado_vendedores_batch(
                ids_t, m_ini, view.fim_exclusive
            ).items():
                metrics_cache[(vid, m_ini.isoformat(), view.fim_exclusive.isoformat())] = m
        elif view.lente == "Mensal" or not acumulado:
            for vid, m in load_realizado_vendedores_batch(ids_t, m_ini, m_fim).items():
                metrics_cache[(vid, m_ini.isoformat(), m_fim.isoformat())] = m

    vids_set = {int(r.vendedor) for r in rank.itertuples()}
    snap = load_grid_snapshot(ano, mes)
    if snap:
        base_rows = [
            aplicar_premissa_salva(recalc_row_formulas_only(dict(x), taxa), ano, mes, taxa)
            for x in snap
        ]
    else:
        base_rows = []
        for vid in vids_set:
            gr = load_vendedor_grid_row(vid, ano, mes, taxa)
            if gr:
                base_rows.append(gr)
    grid_by_vid: dict[int, dict] = {}
    if base_rows:
        for row in aplicar_colunas_proporcionais(base_rows, ano, mes, emp):
            vid = int(row["vendedor"])
            if vid in vids_set:
                grid_by_vid[vid] = row

    tops_cli: dict[int, list] = {}
    tops_prod: dict[int, list] = {}
    tops_cid: dict[int, list] = {}
    if include_tops and ids_t:
        tops_cli, tops_prod, tops_cid = load_tops_ranking_batch(
            ids_t, p_ini, p_fim, 3
        )

    cards: list[dict] = []
    for r in rank.itertuples():
        vid = int(r.vendedor)
        nome = str(r.nome)
        real = float(r.faturamento)
        clientes_mes = int(r.clientes) if pd.notna(r.clientes) else 0
        carteira = int(r.carteira) if pd.notna(r.carteira) else 0

        row = grid_by_vid.get(vid) or load_vendedor_grid_row(vid, ano, mes, taxa) or {}
        meta_calc = float(row.get("meta_formula") or 0)
        meta_man = float(row.get("meta_manual") or 0)
        meta_mes, meta_tipo, cob_meta = resolve_meta_mes_cob(
            meta_ref, row, meta_man, meta_calc, carteira
        )
        if meta_mes <= 0:
            meta_mes = meta_vendedor_periodo_mes(
                vid, ano, mes, taxa,
                faturamento_mes=real,
                carteira=carteira or None,
                clientes_mes=clientes_mes,
            )
            meta_tipo = "salva"

        modo_pacing = (
            "Real"
            if acumulado and view.lente in ("Semanal", "Diário")
            else "Calculada"
        )

        pf = build_pacing_fat(meta_mes, view, vid, modo_pacing, metrics_cache)
        pc = build_pacing_cob(cob_meta, view, vid, modo_pacing, metrics_cache)
        meta_uso = meta_periodo_display(meta_mes, modo_pacing, view.lente, pf)
        real = pf.realizado_periodo
        ating = _pct_ating(real, meta_uso) or 0
        falta = max(meta_uso - real, 0) if meta_uso > 0 else 0

        cob_meta_uso = pc.meta_periodo_planejada
        clientes_periodo = pc.clientes_periodo
        pct_cob = (clientes_periodo / cob_meta_uso * 100) if cob_meta_uso > 0 else 0
        falta_cob = max(int(round(cob_meta_uso)) - clientes_periodo, 0) if cob_meta_uso > 0 else 0

        part_emp = (real / meta_emp * 100) if meta_emp > 0 else 0
        tem_prem = vendedor_tem_premissa(vid, ano, mes) and premissa_tem_prescricao(
            get_premissa(vid, ano, mes)
        )

        ticket_meta = float(row.get("ticket_meta") or 0)
        t_ini, t_fim, t_lbl = _ticket_realizado_interval(
            view, acumulado and view.lente in ("Semanal", "Diário"), m_ini, m_fim
        )
        iv_ticket = _metrics_from_cache(vid, t_ini, t_fim, metrics_cache)
        ticket_real = _ticket_realizado_valor(iv_ticket)
        pct_ticket = (
            (ticket_real / ticket_meta * 100) if ticket_meta > 0 and ticket_real > 0 else 0
        )

        top_clientes = [
            (_clip_label(n), v) for n, v in tops_cli.get(vid, [])
        ]
        top_produtos = [
            (_clip_label(n), v) for n, v in tops_prod.get(vid, [])
        ]
        top_cidades = [
            (_clip_label(n), v) for n, v in tops_cid.get(vid, [])
        ]

        cards.append(
            {
                "vendedor": vid,
                "nome": nome,
                "realizado": real,
                "meta_uso": meta_uso,
                "meta_tipo": meta_tipo,
                "acumulado": acumulado and view.lente in ("Semanal", "Diário"),
                "ating": ating,
                "falta": falta,
                "clientes_mes": clientes_periodo,
                "cob_meta": int(round(cob_meta_uso)) if cob_meta_uso > 0 else 0,
                "ajuste_label": pf.ajuste_label,
                "carteira": carteira,
                "pct_cob": pct_cob,
                "falta_cob": falta_cob,
                "part_emp": part_emp,
                "ticket_meta": ticket_meta,
                "ticket_real": ticket_real,
                "ticket_periodo_label": t_lbl,
                "pct_ticket": pct_ticket,
                "top_clientes": top_clientes,
                "top_produtos": top_produtos,
                "top_cidades": top_cidades,
                "tem_premissa": tem_prem,
            }
        )
    cards.sort(key=lambda c: c["realizado"], reverse=True)
    return cards


def render_painel_equipe_mes(ano: int, mes: int, taxa: float) -> pd.DataFrame:
    """Painel único: meta empresa + cards por colaborador."""
    st.markdown(_RANK_CSS, unsafe_allow_html=True)
    view = render_pacing_controls(ano, mes, "rank")
    st.caption(
        "**Meta:** de onde vem o valor do mês (azul = prescrito · amarelo = proporcional empresa). "
        "**Acumulado:** só em semana/dia — meta e realizado do dia 1 até o fim do período."
    )
    c_meta, c_acum = st.columns([2, 1])
    with c_meta:
        meta_ref = st.segmented_control(
            "Origem da meta nos cards",
            ["Manual", "Calculada", "Proporcional"],
            default="Manual",
            key=f"rank_meta_ref_{ano}_{mes}",
        )
    with c_acum:
        acumulado = st.checkbox(
            "Acumulado do mês",
            value=False,
            disabled=view.lente == "Mensal",
            key=f"rank_acum_{ano}_{mes}",
            help="Desligado = só a semana/dia. Ligado = meta e realizado acumulados (ex.: sem 2 → 2× fatia).",
        )
    meta_ref = meta_ref or "Manual"
    include_tops = st.checkbox(
        "Mostrar tops (clientes, produtos, cidades) nos cards",
        value=False,
        key=f"rank_tops_{ano}_{mes}",
        help="Desligado por padrão para carregar o painel mais rápido.",
    )
    cards = _collect_vendedor_cards(
        ano, mes, taxa, view, meta_ref, acumulado, include_tops=include_tops
    )
    if not cards:
        st.info("Sem faturamento no mês para montar o painel.")
        return pd.DataFrame()

    emp = get_premissa_empresa(ano, mes)
    meta_emp = meta_empresa_mensal_ref(emp)
    total_real = sum(c["realizado"] for c in cards)
    total_meta = sum(c["meta_uso"] for c in cards if c["meta_uso"] > 0)
    vids = [int(c["vendedor"]) for c in cards]
    modo_emp = (
        "Real"
        if acumulado and view.lente in ("Semanal", "Diário")
        else "Calculada"
    )
    pf_emp = build_pacing_fat_equipe(meta_emp, view, vids, modo_emp)
    meta_emp_view = meta_periodo_display(meta_emp, modo_emp, view.lente, pf_emp)
    falta_emp = max(meta_emp_view - total_real, 0) if meta_emp_view > 0 else 0
    pct_emp = min(total_real / meta_emp_view * 100, 100) if meta_emp_view > 0 else 0
    pct_emp_style = f"--pct: {pct_emp:.1f}%;"

    st.markdown(
        f"""
        <div class="rank-empresa-hero">
          <div>
            <div class="re-tag">Meta da empresa · {label_mes(ano, mes)} · {view.lente}</div>
            <div class="re-big">{fmt_brl_cell(meta_emp_view) if meta_emp_view > 0 else "— (defina no Início)"}</div>
            <div style="font-size:0.9rem;opacity:0.92;">
              Prescrito do mês: {fmt_brl_cell(meta_emp) if meta_emp > 0 else "—"} · Período: {view.period_label}
            </div>
            <div class="re-row">
              <div class="re-metric">
                <span>Realizado equipe</span>
                <strong>{fmt_brl_cell(total_real)}</strong>
              </div>
              <div class="re-metric">
                <span>Falta para meta empresa</span>
                <strong>{fmt_brl_cell(falta_emp) if meta_emp > 0 else "—"}</strong>
              </div>
              <div class="re-metric">
                <span>Soma metas nos cards (filtro atual)</span>
                <strong>{fmt_brl_cell(total_meta) if total_meta > 0 else "—"}</strong>
              </div>
            </div>
          </div>
          <div class="rank-ring" style="{pct_emp_style}">
            <div class="rank-ring-inner">
              <span>{pct_emp:.0f}%</span>
              <span class="sub">da meta empresa</span>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if meta_emp <= 0:
        st.warning("Salve a **meta da empresa** no Início para ver o progresso consolidado.")

    n_prem = sum(1 for c in cards if c["tem_premissa"])
    st.markdown(
        f'<p class="rank-section-title">Colaboradores ({len(cards)}) · '
        f"{n_prem} com premissas salvas</p>",
        unsafe_allow_html=True,
    )

    for i in range(0, len(cards), 2):
        col_a, col_b = st.columns(2, gap="medium")
        with col_a:
            st.markdown(_vend_card_html(cards[i], meta_emp), unsafe_allow_html=True)
        with col_b:
            if i + 1 < len(cards):
                st.markdown(_vend_card_html(cards[i + 1], meta_emp), unsafe_allow_html=True)

    return load_acompanhamento_mes(ano, mes, taxa)


def render_barras_progresso(df: pd.DataFrame) -> None:
    if df.empty:
        return
    st.markdown("##### Atingimento da meta (R$)")
    for _, row in df.sort_values("realizado", ascending=False).iterrows():
        nome = str(row["nome"])[:36]
        meta = float(row["meta_rs"] or 0)
        real = float(row["realizado"] or 0)
        if meta <= 0:
            st.caption(f"**{nome}** — meta não definida (salve premissas no Início).")
            continue
        pct = min(real / meta, 1.0)
        st.markdown(
            f"**{nome}** · {fmt_brl_cell(real)} / {fmt_brl_cell(meta)} "
            f"({fmt_pct_table(row['ating_meta_pct'], 0) if row['ating_meta_pct'] else '—'})"
        )
        st.progress(pct)


def render_tabela_acompanhamento(df: pd.DataFrame, height: int = 420) -> None:
    if df.empty:
        st.info("Sem dados para acompanhamento.")
        return
    show = df.copy()
    show["ating_bar"] = show["ating_meta_pct"].apply(
        lambda p: f"{min(float(p), 100):.0f}%" if p is not None and not pd.isna(p) else "—"
    )
    tbl = show.rename(
        columns={
            "vendedor": "Cód.",
            "nome": "Colaborador",
            "realizado": "Realizado",
            "meta_rs": "Meta (salva)",
            "ating_bar": "Ating. meta",
            "conv_meta_pct": "Conv. meta %",
            "tx_proj_pct": "TX cob. proj. %",
            "cobertura_real_pct": "Cobertura real %",
        }
    )[
        [
            "Cód.",
            "Colaborador",
            "Realizado",
            "Meta (salva)",
            "Ating. meta",
            "Conv. meta %",
            "TX cob. proj. %",
            "Cobertura real %",
        ]
    ]
    tot_meta = float(show["meta_rs"].sum())
    tot_real = float(show["realizado"].sum())
    tot_row = {
        "Cód.": "",
        "Colaborador": "TOTAL",
        "Realizado": tot_real,
        "Meta (salva)": tot_meta,
        "Ating. meta": (
            f"{tot_real / tot_meta * 100:.0f}%" if tot_meta > 0 else "—"
        ),
        "Conv. meta %": None,
        "TX cob. proj. %": None,
        "Cobertura real %": None,
    }
    tbl = pd.concat([tbl, pd.DataFrame([tot_row])], ignore_index=True)
    show_data_table(
        tbl,
        spec={
            "Cód.": "text",
            "Colaborador": "text",
            "Realizado": "money",
            "Meta (salva)": "money",
            "Ating. meta": "text",
            "Conv. meta %": "pct",
            "TX cob. proj. %": "pct",
            "Cobertura real %": "pct",
        },
        height=height,
    )
