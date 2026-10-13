"""Visão geral — layout alinhado aos cards de Ranking (dados reais do ERP + meta do Início)."""

from __future__ import annotations

import hashlib
import html

import pandas as pd
import streamlit as st

from datetime import date, timedelta

from app.charts import chart_acumulado, chart_delta_meses, chart_year_compare
from app.constants import MESES_CURTO, label_mes
from app.data import (
    load_faturamento_diario_mes,
    load_faturamento_mensal,
    load_resumo_ano,
    load_resumo_periodo,
)
from app.dates_util import month_bounds
from app.equipe_grid_logic import premissa_tem_prescricao
from app.formatting import fmt_brl_cell
from app.month_meta import meta_mes_sessao
from app.period_filter import _applied_period_key
from app.plano_metas import (
    mes_corrente,
    mes_fechado,
    meta_empresa_mes,
    metas_colaboradores_mes,
    metas_empresa_ano,
)
from app.premissas import (
    PremissaVendedor,
    _load_all,
    count_premissas_vendedor_mes,
)

_VG_CSS = """
<style>
.vg-page { margin-top: 0.25rem; }
.vg-hero {
    margin: 0 0 1.25rem 0;
}
.vg-hero .eyebrow {
    font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.12em;
    color: #6b7280; font-weight: 600; margin: 0 0 0.35rem 0;
}
.vg-hero h1 {
    font-size: 1.65rem; font-weight: 700; color: #111827; margin: 0;
    letter-spacing: -0.03em;
}
.vg-hero .sub { color: #6b7280; font-size: 0.92rem; margin: 0.35rem 0 0 0; }
.vg-ref-pill {
    display: inline-flex; align-items: center; gap: 0.35rem;
    font-size: 0.78rem; color: #166534; background: #ecfdf5;
    border: 1px solid #bbf7d0; border-radius: 999px; padding: 0.25rem 0.65rem;
    font-weight: 600;
}
.vg-section {
    background: #fff; border: 1px solid #e5e7eb; border-radius: 16px;
    padding: 1.15rem 1.25rem 0.5rem; margin-bottom: 1rem;
    box-shadow: 0 2px 12px rgba(15, 51, 40, 0.05);
}
.vg-section-head {
    display: flex; flex-wrap: wrap; justify-content: space-between;
    align-items: flex-start; gap: 0.75rem; margin-bottom: 0.85rem;
}
.vg-section-head h2 {
    font-size: 1.05rem; font-weight: 700; color: #111827; margin: 0;
}
.vg-section-head p {
    font-size: 0.82rem; color: #6b7280; margin: 0.2rem 0 0 0;
}
.vg-kpi-grid {
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.85rem;
    margin-bottom: 0.5rem;
}
@media (max-width: 960px) { .vg-kpi-grid { grid-template-columns: repeat(2, 1fr); } }
.vg-kpi {
    background: #fff; border: 1px solid #e5e7eb; border-radius: 14px;
    padding: 1rem 1.05rem; position: relative; min-height: 118px;
}
.vg-kpi.accent {
    background: linear-gradient(145deg, #f0fdf4 0%, #ecfdf5 100%);
    border-color: #bbf7d0;
}
.vg-kpi .ico {
    position: absolute; top: 0.85rem; right: 0.85rem;
    width: 2rem; height: 2rem; border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1rem; background: #f3f4f6; color: #374151;
}
.vg-kpi.accent .ico { background: #dcfce7; color: #166534; }
.vg-kpi .lbl {
    font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.06em;
    color: #6b7280; font-weight: 600; padding-right: 2.2rem;
}
.vg-kpi .val {
    font-size: 1.35rem; font-weight: 700; color: #111827;
    margin: 0.35rem 0 0.25rem; line-height: 1.15;
}
.vg-kpi.accent .val { color: #14532d; }
.vg-kpi .foot { font-size: 0.78rem; color: #6b7280; line-height: 1.35; }
.vg-kpi .delta-up { color: #15803d; font-weight: 600; }
.vg-kpi .delta-down { color: #b91c1c; font-weight: 600; }
.vg-meta-grid {
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.85rem;
    margin-bottom: 1rem;
}
@media (max-width: 960px) { .vg-meta-grid { grid-template-columns: repeat(2, 1fr); } }
.vg-meta-row {
    display: grid; grid-template-columns: 1fr 280px; gap: 1rem;
    align-items: stretch;
}
@media (max-width: 900px) { .vg-meta-row { grid-template-columns: 1fr; } }
.vg-where {
    background: linear-gradient(160deg, #ecfdf5 0%, #d1fae5 100%);
    border: 1px solid #a7f3d0; border-radius: 14px; padding: 1.1rem 1.15rem;
}
.vg-where .big { font-size: 2rem; font-weight: 800; color: #14532d; line-height: 1; }
.vg-where .sub { font-size: 0.82rem; color: #166534; margin: 0.25rem 0 0.75rem; }
.vg-where .bar {
    height: 8px; background: rgba(255,255,255,0.65); border-radius: 999px; overflow: hidden;
    margin-bottom: 0.85rem;
}
.vg-where .bar > span {
    display: block; height: 100%; background: #16a34a; border-radius: 999px;
}
.vg-where dl { margin: 0; font-size: 0.82rem; color: #14532d; }
.vg-where dt { font-weight: 600; margin-top: 0.35rem; }
.vg-where dd { margin: 0.1rem 0 0 0; font-weight: 700; }
.st-key-vg_filtros { background:#fff; border:1px solid #e5e7eb; border-radius:14px; padding:.55rem .9rem .35rem; margin-bottom:1rem; }
.st-key-vg_filtros label p { font-size:.72rem !important; text-transform:uppercase; letter-spacing:.05em; color:#6b7280 !important; font-weight:600 !important; }
.vg-mes { border:1px solid #e5e7eb; border-radius:12px; padding:.6rem .7rem .2rem; background:#fff; }
.vg-mes.fechado { background:#f6f8f7; }
.vg-mes.atual { border-color:#3d6b5c; box-shadow:inset 0 0 0 1px #3d6b5c; }
.vg-mes .n { display:flex; justify-content:space-between; font-size:.8rem; font-weight:700; color:#111827; }
.vg-mes .n span:last-child { font-size:.68rem; font-weight:600; color:#6b7280; }
.vg-mes .m { font-size:1rem; font-weight:700; color:#111827; margin-top:.2rem; }
.vg-mes .r { font-size:.72rem; color:#6b7280; }
.vg-mes .bar { height:4px; background:#e6ebe8; border-radius:4px; margin:.35rem 0 .1rem; overflow:hidden; }
.vg-mes .bar i { display:block; height:100%; background:#3d6b5c; animation: vg-grow 1s cubic-bezier(.2,.8,.2,1); }
.vg-where .bar > span { animation: vg-grow 1.1s cubic-bezier(.2,.8,.2,1); transition: width .9s cubic-bezier(.2,.8,.2,1); }
@keyframes vg-grow { from { width: 0; } }
.st-key-vg_anim_mes .barlayer .point path {
    transform-box: fill-box; transform-origin: bottom;
    animation: vg-bar .9s cubic-bezier(.2,.8,.2,1) both;
}
@keyframes vg-bar { from { transform: scaleY(0); } }
.st-key-vg_anim_evo .scatterlayer .trace,
.st-key-vg_anim_mes .scatterlayer .trace { animation: vg-reveal 1.2s cubic-bezier(.3,.7,.2,1) both; }
@keyframes vg-reveal { from { clip-path: inset(0 100% 0 0); } to { clip-path: inset(0 0 0 0); } }
[class*="st-key-vg_mes_btn_"] button { min-height:1.7rem; padding:0 .4rem; font-size:.75rem; }
</style>
"""


def _fmt_brl_short(v: float) -> str:
    if abs(v) >= 1_000_000:
        return f"R$ {v / 1_000_000:.2f} mi".replace(".", ",")
    if abs(v) >= 1_000:
        return f"R$ {v / 1_000:.1f} mil".replace(".", ",")
    return fmt_brl_cell(v)


def _pct_delta(atual: float, anterior: float) -> tuple[str, str]:
    if anterior == 0:
        return "—", "neutral"
    d = (atual - anterior) / anterior * 100
    kind = "up" if d > 0 else "down" if d < 0 else "neutral"
    sign = "+" if d > 0 else ""
    cls = "delta-up" if kind == "up" else "delta-down" if kind == "down" else ""
    return f'<span class="{cls}">{sign}{d:.1f}% vs. ano comparado</span>', kind


def _kpi_card(
    label: str,
    value: str,
    foot: str,
    icon: str,
    accent: bool = False,
) -> str:
    cls = "vg-kpi accent" if accent else "vg-kpi"
    return (
        f'<div class="{cls}"><span class="ico">{html.escape(icon)}</span>'
        f'<div class="lbl">{html.escape(label)}</div><div class="val">{value}</div>'
        f'<div class="foot">{foot}</div></div>'
    )


def _h(s: str) -> str:
    """HTML numa linha só: linha em branco/indentação viraria bloco de código no Markdown."""
    return "".join(line.strip() for line in s.splitlines())


def _count_ritmo_equipe(ano: int, mes: int) -> tuple[int, int]:
    """Colaboradores com premissa salva: quantos com meta de fat > 0 (ritmo) vs resto."""
    suffix = f":{ano}:{mes:02d}"
    data = _load_all()
    allowed = {f.name for f in PremissaVendedor.__dataclass_fields__.values()}
    no_ritmo = 0
    no_ritmo_ok = 0
    for key, raw in data.items():
        if not key.endswith(suffix) or key.startswith("empresa:"):
            continue
        prem = PremissaVendedor(**{k: v for k, v in raw.items() if k in allowed})
        if not premissa_tem_prescricao(prem):
            continue
        if prem.meta_faturamento_rs > 0 or prem.ticket_meta > 0:
            no_ritmo_ok += 1
        else:
            no_ritmo += 1
    return no_ritmo_ok, no_ritmo


_DIAS_SEM = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")


def _meta_mes(ano: int, mes: int, vid: int | None) -> float:
    if vid is None:
        return meta_empresa_mes(ano, mes)
    mc = metas_colaboradores_mes(ano, mes).get(int(vid))
    return float(mc.final) if mc else 0.0


def _abrir_progresso(ano: int, mes: int) -> None:
    st.session_state["vend_modo"] = "Mês"
    st.session_state["vend_ano"] = ano
    st.session_state["vend_mes"] = mes
    st.session_state.pop(_applied_period_key("vend"), None)
    st.session_state["main_nav_page"] = "Progresso"


def _cards_meses(ano: int, vid: int | None, fat_mes: dict[int, float], metas: dict[int, float]) -> None:
    st.markdown(
        _h(f"""<div class="vg-section-head"><div><h2>Metas mês a mês · {ano}</h2>
        <p>Meta do plano (Início) e quanto já foi realizado. Clique para analisar o mês no Progresso.</p>
        </div></div>"""),
        unsafe_allow_html=True,
    )
    for linha in (range(1, 7), range(7, 13)):
        cols = st.columns(6, gap="small")
        for col, m in zip(cols, linha):
            meta = metas.get(m, 0.0)
            real = fat_mes.get(m, 0.0)
            if mes_fechado(ano, m):
                cls, tag = "fechado", "fechado"
            elif (ano, m) == mes_corrente():
                cls, tag = "atual", "em andamento"
            else:
                cls, tag = "", "a vir"
            if cls:
                pct = real / meta * 100 if meta > 0 else 0
                pct_txt = ">999%" if pct > 999 else f"{pct:.0f}%"
                r = f"Realizado {_fmt_brl_short(real)} · {pct_txt}"
            else:
                pct, r = 0, "ainda não começou"
            with col:
                st.markdown(
                    f'<div class="vg-mes {cls}"><div class="n"><span>{MESES_CURTO[m]}</span><span>{tag}</span></div>'
                    f'<div class="m">{_fmt_brl_short(meta) if meta > 0 else "—"}</div><div class="r">{r}</div>'
                    f'<div class="bar"><i style="width:{min(pct, 100):.0f}%"></i></div></div>',
                    unsafe_allow_html=True,
                )
                st.button(
                    "Analisar mês",
                    key=f"vg_mes_btn_{ano}_{m}",
                    on_click=_abrir_progresso,
                    args=(ano, m),
                    disabled=not cls,
                    use_container_width=True,
                )


def _anim_token(*parts) -> str:
    """Muda quando o filtro muda: novo nome de animação/chave faz a barra e o gráfico crescerem de novo."""
    return hashlib.md5("|".join(map(str, parts)).encode()).hexdigest()[:8]


def _semanas_mes(ano: int, mes: int) -> list[tuple[date, date]]:
    """Semanas (seg–dom) do mês, cortadas nas bordas: [(início, fim exclusivo)]."""
    ini, fim = month_bounds(ano, mes)
    out, d = [], ini
    while d < fim:
        nxt = min(d - timedelta(days=d.weekday()) + timedelta(days=7), fim)
        out.append((d, nxt))
        d = nxt
    return out


def _semana_atual_idx(semanas: list[tuple[date, date]]) -> int:
    hoje = date.today()
    for i, (a, b) in enumerate(semanas):
        if a <= hoje < b:
            return i
    return len(semanas) - 1 if semanas and hoje >= semanas[-1][1] else 0


def _serie_evolucao(
    modo: str,
    ano: int,
    mes: int,
    vid: int | None,
    filtros: dict,
    meta_mes: float,
    fat_mes: dict[int, float],
    metas: dict[int, float],
    semana: int = 0,
) -> tuple[list[str], list[float], list[float], str, str]:
    """(eixo x, realizado acumulado, meta acumulada, título do eixo, nome do período)."""
    hoje = date.today()
    if modo == "Ano":
        ultimo = 12 if ano < hoje.year else (hoje.month if ano == hoje.year else 0)
        x = [MESES_CURTO[m] for m in range(1, 13)]
        real, meta, acc_r, acc_m = [], [], 0.0, 0.0
        for m in range(1, 13):
            acc_m += metas.get(m, 0.0)
            meta.append(acc_m)
            if m <= ultimo:
                acc_r += fat_mes.get(m, 0.0)
                real.append(acc_r)
        return x, real, meta, "Mês", str(ano)

    ini, fim = month_bounds(ano, mes)
    n_days = max((fim - ini).days, 1)
    df_dia = load_faturamento_diario_mes(
        ano, mes, vid, filtros["apenas_positivos"], filtros["excluir_sem_vendedor"]
    )
    por_dia = (
        {pd.Timestamp(r.dia).date(): float(r.faturamento) for r in df_dia.itertuples()}
        if not df_dia.empty
        else {}
    )
    meta_dia = meta_mes / n_days
    if modo == "Semana":
        semanas = _semanas_mes(ano, mes)
        w_ini, w_fim = semanas[min(max(semana, 0), len(semanas) - 1)]
        dias = [w_ini + timedelta(days=i) for i in range((w_fim - w_ini).days)]
        x = [f"{_DIAS_SEM[d.weekday()]} {d.day:02d}" for d in dias]
        titulo, nome = "Dia da semana", f"semana {w_ini:%d/%m}–{dias[-1]:%d/%m}"
    else:
        dias = [ini + timedelta(days=i) for i in range(n_days)]
        x = [f"{d.day:02d}" for d in dias]
        titulo, nome = "Dia do mês", label_mes(ano, mes)
    real, meta, acc_r = [], [], 0.0
    for i, d in enumerate(dias, start=1):
        meta.append(meta_dia * i)
        if d <= hoje:
            acc_r += por_dia.get(d, 0.0)
            real.append(acc_r)
    return x, real, meta, titulo, nome


def render_visao_geral(filtros: dict, vendedores: pd.DataFrame) -> None:
    st.markdown(_VG_CSS, unsafe_allow_html=True)

    ano_meta, mes_meta, _taxa = meta_mes_sessao()
    ref_txt = f"Mês de referência: {label_mes(ano_meta, mes_meta)} (Início)"
    st.markdown(
        _h(f"""<div class="vg-hero" style="display:flex;flex-wrap:wrap;justify-content:space-between;align-items:flex-start;gap:.75rem;">
        <div><div class="eyebrow">Painel gerencial</div><h1>Visão geral</h1>
        <p class="sub">Seus resultados e metas, lado a lado.</p></div>
        <span class="vg-ref-pill">✓ {html.escape(ref_txt)}</span></div>"""),
        unsafe_allow_html=True,
    )

    anos_opts = [ano_meta + 1, ano_meta, ano_meta - 1, ano_meta - 2, ano_meta - 3]
    with st.container(key="vg_filtros"):
        fc1, fc2, fc3, fc4 = st.columns([1, 1, 1, 1.6], vertical_alignment="bottom")
        with fc1:
            ano_focus = st.selectbox("Ano em destaque", anos_opts, index=1, key="visao_ano_focus")
        with fc2:
            comparar = st.selectbox(
                "Comparar com",
                ["Nenhum"] + [str(a) for a in anos_opts],
                index=3,
                key="visao_ano_comp",
            )
        with fc3:
            modo_vis = st.selectbox(
                "Gráfico mensal",
                ["Sobreposto", "Lado a lado", "Só o ano"],
                key="visao_modo_sel",
            )
        with fc4:
            opcoes = ["Todos"] + [f"{r.vendedor} — {r.nome}" for r in vendedores.itertuples()]
            escolha = st.selectbox("Vendedor", opcoes, key="visao_vendedor")
    ano_ghost = None if comparar == "Nenhum" else int(comparar)
    if ano_ghost == ano_focus:
        ano_ghost = None
    modo_chart = {
        "Sobreposto": "Fantasma atrás (overlay)",
        "Lado a lado": "Lado a lado",
        "Só o ano": "Só ano em foco",
    }[modo_vis]
    vid = None if escolha == "Todos" else int(escolha.split(" — ")[0])
    pos, sem_vend = filtros["apenas_positivos"], filtros["excluir_sem_vendedor"]

    res = load_resumo_ano(ano_focus, vid, pos, sem_vend)
    res_g = load_resumo_ano(ano_ghost, vid, pos, sem_vend) if ano_ghost else None
    pairs = [
        ("Faturamento no ano", "faturamento", _fmt_brl_short, True, "💰"),
        ("Clientes no ano", "clientes", lambda v: f"{int(v):,}".replace(",", "."), False, "👥"),
        ("Notas no ano", "notas", lambda v: f"{int(v):,}".replace(",", "."), False, "📄"),
        ("Ticket médio / nota", "ticket_nota", _fmt_brl_short, False, "🧾"),
    ]
    cards_html = ""
    for label, key, fmt, accent, icon in pairs:
        foot = ""
        if res_g:
            d_html, _ = _pct_delta(res[key], res_g[key])
            foot = f"{ano_ghost}: <strong>{fmt(res_g[key])}</strong><br>{d_html}"
        cards_html += _kpi_card(f"{label} ({ano_focus})", fmt(res[key]), foot, icon, accent=accent)
    st.markdown(
        _h(f"""<div class="vg-section"><div class="vg-section-head"><div><h2>Resumo executivo</h2>
        <p>Resultados anuais — dados do ERP com os filtros do topo.</p></div></div>
        <div class="vg-kpi-grid">{cards_html}</div></div>"""),
        unsafe_allow_html=True,
    )

    anos = tuple(sorted({ano_focus, ano_ghost, ano_meta} - {None}))
    df = load_faturamento_mensal(anos, vid, pos, sem_vend)
    st.markdown("##### Faturamento mês a mês")
    tok_mes = _anim_token(ano_focus, ano_ghost, modo_chart, vid, pos, sem_vend)
    with st.container(key="vg_anim_mes"):
        st.plotly_chart(
            chart_year_compare(df, ano_focus, ano_ghost, modo_chart),
            use_container_width=True,
            config={"displayModeBar": False},
            key=f"vg_mes_{tok_mes}",
        )
        if ano_ghost:
            st.plotly_chart(
                chart_delta_meses(df, ano_ghost, ano_focus),
                use_container_width=True,
                config={"displayModeBar": False},
                key=f"vg_delta_{tok_mes}",
            )

    fat_mes = {
        int(r.mes): float(r.faturamento or 0)
        for r in df[df["ano"] == ano_meta].itertuples()
    } if not df.empty else {}
    if vid is None:
        metas = metas_empresa_ano(ano_meta)
    else:
        metas = {m: _meta_mes(ano_meta, m, vid) for m in range(1, 13)}
    meta_mes = metas.get(mes_meta, 0.0)
    meta_anual = sum(metas.values())

    with st.container(border=True):
        _cards_meses(ano_meta, vid, fat_mes, metas)

    m_ini, m_fim = month_bounds(ano_meta, mes_meta)
    real_mes = float(load_resumo_periodo(m_ini, m_fim, vid, pos, sem_vend)["faturamento"])
    pm, py = (12, ano_meta - 1) if mes_meta == 1 else (mes_meta - 1, ano_meta)
    p_ini, p_fim = month_bounds(py, pm)
    fat_prev = float(load_resumo_periodo(p_ini, p_fim, vid, pos, sem_vend)["faturamento"])
    if fat_prev > 0:
        d_mes = (real_mes - fat_prev) / fat_prev * 100
        fat_mes_delta = (
            f'<span class="{"delta-up" if d_mes >= 0 else "delta-down"}">'
            f"{'+' if d_mes >= 0 else ''}{d_mes:.1f}% vs. mês anterior</span>"
        )
    else:
        fat_mes_delta = "Sem base no mês anterior"
    pct_meta = (real_mes / meta_mes * 100) if meta_mes > 0 else 0.0
    falta_meta = max(meta_mes - real_mes, 0) if meta_mes > 0 else 0.0
    n_prem = count_premissas_vendedor_mes(ano_meta, mes_meta)
    ritmo, atencao = _count_ritmo_equipe(ano_meta, mes_meta)
    colab_foot = (
        f"<strong>{ritmo}</strong> no ritmo · <strong>{atencao}</strong> precisam de atenção"
        if n_prem > 0
        else "Salve as metas do mês em Início"
    )
    meta_anual_txt = f"de {_fmt_brl_short(meta_anual)} no ano" if meta_anual > 0 else "informe a meta anual em Início"
    cards = (
        _kpi_card("Meta do mês", _fmt_brl_short(meta_mes) if meta_mes > 0 else "—", meta_anual_txt, "🎯", accent=True)
        + _kpi_card("Faturamento realizado", _fmt_brl_short(real_mes), fat_mes_delta, "💳")
        + _kpi_card(
            "Meta atingida",
            f"{pct_meta:.0f}%" if meta_mes > 0 else "—",
            f"{_fmt_brl_short(falta_meta)} para a meta" if meta_mes > 0 else "Sem meta do mês",
            "🚩",
        )
        + _kpi_card("Colaboradores ativos", str(n_prem), colab_foot, "👤")
    )
    st.markdown(
        _h(f"""<div class="vg-section"><div class="vg-section-head"><div><h2>Acompanhamento de metas</h2>
        <p>Meta do plano (Início) · realizado no ERP.</p></div>
        <div style="font-size:.82rem;color:#6b7280;font-weight:600;">{html.escape(label_mes(ano_meta, mes_meta))}</div></div>
        <div class="vg-meta-grid">{cards}</div></div>"""),
        unsafe_allow_html=True,
    )

    if meta_mes <= 0:
        st.info("Defina a **meta anual** em **Início** para acompanhar o progresso aqui.")
        return

    col_c, col_s = st.columns([3, 1])
    with col_c:
        h1, h_sem, h2 = st.columns([1.3, 1.1, 1.25], vertical_alignment="bottom")
        with h1:
            st.markdown("##### Evolução do faturamento")
        with h2:
            modo_evo = st.segmented_control(
                "Período",
                ["Semana", "Mês", "Ano"],
                default="Mês",
                key="vg_evo_modo",
                label_visibility="collapsed",
            ) or "Mês"
        semana_i = 0
        if modo_evo == "Semana":
            semanas = _semanas_mes(ano_meta, mes_meta)
            sem_key = f"vg_semana_{ano_meta}_{mes_meta}"
            with h_sem:
                semana_i = st.selectbox(
                    "Semana",
                    list(range(len(semanas))),
                    index=_semana_atual_idx(semanas),
                    format_func=lambda i: (
                        f"Semana {i + 1} · {semanas[i][0]:%d}–"
                        f"{semanas[i][1] - timedelta(days=1):%d/%m}"
                    ),
                    key=sem_key,
                    label_visibility="collapsed",
                )
        x, real_acc, meta_acc, x_title, nome = _serie_evolucao(
            modo_evo, ano_meta, mes_meta, vid, filtros, meta_mes, fat_mes, metas, semana_i
        )
        st.caption(f"Acumulado do realizado vs. ritmo da meta · {nome}.")
        tok_evo = _anim_token(modo_evo, semana_i, vid, ano_meta, mes_meta, pos, sem_vend)
        with st.container(key="vg_anim_evo"):
            st.plotly_chart(
                chart_acumulado(x, real_acc, meta_acc, x_title),
                use_container_width=True,
                config={"displayModeBar": False},
                key=f"vg_evo_{tok_evo}",
            )
        st.markdown(
            f"<style>@keyframes vg-grow-{tok_evo} {{ from {{ width: 0; }} }}"
            f".vg-where .bar > span {{ animation-name: vg-grow-{tok_evo}; }}</style>",
            unsafe_allow_html=True,
        )
    real_p = real_acc[-1] if real_acc else 0.0
    meta_p = meta_acc[-1] if meta_acc else 0.0
    pct_p = real_p / meta_p * 100 if meta_p > 0 else 0.0
    ritmo_hoje = meta_acc[len(real_acc) - 1] if real_acc else 0.0
    status = (
        "↗ Acima do ritmo da meta." if real_p >= ritmo_hoje else "↘ Abaixo do ritmo: acelere para alcançar."
    )
    sub_p = {"Semana": "da meta da semana", "Ano": "da meta do ano"}.get(modo_evo, "da meta do mês")
    with col_s:
        st.markdown(
            _h(f"""<div class="vg-where"><div class="big">{pct_p:.0f}%</div>
            <div class="sub">{sub_p} alcançada</div>
            <div class="bar"><span style="width:{min(100, max(0, pct_p)):.1f}%;"></span></div>
            <dl><dt>Realizado</dt><dd>{html.escape(_fmt_brl_short(real_p))}</dd>
            <dt>Meta do período</dt><dd>{html.escape(_fmt_brl_short(meta_p))}</dd>
            <dt>Falta</dt><dd>{html.escape(_fmt_brl_short(max(meta_p - real_p, 0)))}</dd></dl>
            <p style="font-size:.78rem;color:#166534;margin:.85rem 0 0;">{status}</p></div>"""),
            unsafe_allow_html=True,
        )

