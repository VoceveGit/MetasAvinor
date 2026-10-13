"""Início · 1 — meta do ano: histórico, sugestão, sazonalidade e divisão pelos 12 meses."""

from __future__ import annotations

import html
from datetime import date

import streamlit as st

from app.brl_input import brl_text_input, format_br_number
from app.constants import MESES_CURTO, MESES_NOME
from app.data import load_fat_empresa_mensal
from app.plano_metas import (
    COMP_DESLIGADA,
    COMP_GERAL,
    compensacao_mes,
    get_config_ano,
    mes_corrente,
    mes_fechado,
    mes_salvo,
    meses_restantes,
    meta_plano_mes,
    metas_empresa_ano,
    pesos_meses,
    save_config_ano,
    sugestao_meta_anual,
)
from app.ui import section_header

_CSS = """
<style>
.plano-anos{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:.35rem 0 1.1rem}
.plano-ano{background:#fff;border:1px solid var(--avinor-border);border-radius:14px;padding:14px 16px}
.plano-ano .k{font-size:11.5px;color:var(--avinor-muted);font-weight:700;text-transform:uppercase;letter-spacing:.05em;display:flex;justify-content:space-between;align-items:center;gap:8px}
.plano-ano .v{font-size:24px;font-weight:700;color:var(--avinor-fg);margin-top:6px;line-height:1.1}
.plano-ano .s{font-size:12.5px;color:var(--avinor-muted);margin-top:4px}
.plano-ano.sug{background:#12261d;border-color:#12261d}
.plano-ano.sug .k,.plano-ano.sug .s{color:#b4c2ba}
.plano-ano.sug .v{color:#d4f574}
.plano-q{position:relative;display:inline-flex;flex:0 0 auto;width:17px;height:17px;border-radius:50%;border:1.5px solid currentColor;font-size:10.5px;font-weight:700;align-items:center;justify-content:center;cursor:help;text-transform:none;letter-spacing:0}
[data-testid="stElementContainer"]:has(.plano-anos),[data-testid="stElementContainer"]:has(.plano-meses){position:relative;z-index:30}
[data-tip]{position:relative}
[data-tip]::after{content:attr(data-tip);position:absolute;z-index:50;top:calc(100% + 8px);width:min(340px,80vw);padding:11px 13px;border-radius:10px;background:#12261d;border:1px solid #35574a;color:#e8efe9;font-size:12.5px;font-weight:500;line-height:1.5;text-align:left;text-transform:none;letter-spacing:0;white-space:pre-line;box-shadow:0 10px 28px rgba(18,38,29,.28);opacity:0;visibility:hidden;transform:translateY(-4px);transition:opacity .15s ease .12s,transform .15s ease .12s,visibility 0s linear .27s;pointer-events:none}
[data-tip]:hover::after{opacity:1;visibility:visible;transform:translateY(0);transition-delay:.12s,.12s,0s}
.plano-q[data-tip]::after{right:-10px}
.plano-mes[data-tip]::after{left:0}
.plano-mes:nth-child(6n+4)[data-tip]::after,.plano-mes:nth-child(6n+5)[data-tip]::after,.plano-mes:nth-child(6n)[data-tip]::after{left:auto;right:0}
.plano-meses{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:8px;margin:.6rem 0 .35rem}
.plano-mes{border:1px solid var(--avinor-border);border-radius:12px;padding:10px 12px;background:#fff;cursor:help}
.plano-mes.fechado{background:#f3f5f4}
.plano-mes.atual{border-color:#3d6b5c;box-shadow:inset 0 0 0 1px #3d6b5c}
.plano-mes .n{font-size:12.5px;font-weight:700;color:var(--avinor-fg);display:flex;justify-content:space-between;align-items:baseline;gap:6px}
.plano-mes .tag{font-size:10.5px;font-weight:600;color:var(--avinor-muted)}
.plano-mes .m{font-size:15.5px;font-weight:700;margin-top:5px;color:var(--avinor-fg)}
.plano-mes .r{font-size:11.5px;color:var(--avinor-muted);margin-top:2px}
.plano-mes .bar{height:4px;border-radius:4px;background:#e6ebe8;margin-top:7px;overflow:hidden}
.plano-mes .bar i{display:block;height:100%;background:#3d6b5c;border-radius:4px;animation:plano-grow 1s cubic-bezier(.2,.8,.2,1)}
@keyframes plano-grow{from{width:0}}
.plano-mes .c{font-size:11px;margin-top:5px;font-weight:600}
.plano-mes .c.up{color:#a16207}
.plano-mes .c.down{color:#15803d}
.plano-soma{font-size:13px;color:var(--avinor-muted);margin:.2rem 0 .4rem}
.plano-soma strong{color:var(--avinor-fg)}
@media (max-width:1100px){.plano-anos{grid-template-columns:repeat(2,minmax(0,1fr))}.plano-meses{grid-template-columns:repeat(4,minmax(0,1fr))}}
</style>
"""

_HELP_SAZONAL = (
    "Ligada: cada mês recebe a fatia que teve no faturamento dos dois anos anteriores "
    "(média). Meses que vendem mais ganham meta maior. Desligada: meta anual ÷ 12."
)
_HELP_COMP = (
    "Só muda o que aparece na tela; o plano salvo não muda.\n\n"
    "Ligada: a falta (ou a sobra) da empresa nos meses fechados é somada aos meses que faltam, "
    "pelo peso de cada mês.\n\n"
    "A compensação por colaborador (Individual / Geral) fica no Progresso."
)


def mi(v: float) -> str:
    v = float(v or 0)
    if abs(v) >= 1_000_000:
        return f"R$ {v / 1_000_000:.1f} mi".replace(".", ",")
    if abs(v) >= 1_000:
        return f"R$ {v / 1_000:.0f} mil"
    return f"R$ {v:.0f}"


def pct_br(v: float, dec: int = 1, sinal: bool = False) -> str:
    fmt = f"{{:{'+' if sinal else ''}.{dec}f}}%"
    return fmt.format(float(v or 0)).replace(".", ",")


def _attr(tip: str) -> str:
    """Texto para atributo HTML: linha em branco dentro do HTML encerraria o bloco no Markdown."""
    return html.escape(tip, quote=True).replace("\n", "&#10;")


def _q(tip: str) -> str:
    return f'<span class="plano-q" data-tip="{_attr(tip)}">?</span>'


def _pct_meta(real: float, meta: float) -> str:
    if meta <= 0:
        return "—"
    pct = real / meta * 100
    return ">999%" if pct > 999 else pct_br(pct, 0)


def _faixa_label(meses: list[int]) -> str:
    if not meses:
        return ""
    if len(meses) == 1:
        return MESES_CURTO[meses[0]]
    return f"{MESES_CURTO[meses[0]]}–{MESES_CURTO[meses[-1]]}"


def _cards_anos(ano: int, real_ano: float, meta_ano: float) -> None:
    sug = sugestao_meta_anual(ano)
    restantes = meses_restantes(ano)
    fechados = [m for m in range(1, 13) if m not in restantes]
    g = sug.crescimento * 100

    tip_sug = (
        f"Conta: {_faixa_label(fechados) or 'nenhum mês'} de {ano} já fechados = {mi(sug.realizado_fechado)}. "
        f"{_faixa_label(restantes)} de {ano - 1} = {mi(sug.base_restante)} × (1 {pct_br(g, 1, True)}) "
        f"= {mi(sug.projecao_restante)}. Soma = {mi(sug.sugestao)}.\n\n"
        f"Em palavras: o que já foi vendido fica como está; nos meses que faltam, a sugestão pede "
        f"o mesmo crescimento que a empresa teve de {ano - 2} para {ano - 1}."
    )
    tip_real = (
        f"Faturamento de {ano} até hoje, somando todas as notas com valor positivo."
    )
    pct_meta = f" · {_pct_meta(real_ano, meta_ano)} da meta" if meta_ano > 0 else ""
    cards = [
        ("", f"Faturado {ano - 2}", mi(sug.fat_ano_menos_2), "ano fechado", ""),
        (
            "",
            f"Faturado {ano - 1}",
            mi(sug.fat_ano_menos_1),
            f"{pct_br(g, 1, True)} sobre {ano - 2}",
            "",
        ),
        ("", f"Realizado {ano}", mi(real_ano), f"até {date.today():%d/%m}{pct_meta}", tip_real),
        (
            "sug",
            "Meta sugerida",
            mi(sug.sugestao),
            f"{pct_br(g, 1, True)} nos meses que faltam",
            tip_sug,
        ),
    ]
    parts = []
    for cls, k, v, s, tip in cards:
        q = _q(tip) if tip else ""
        parts.append(
            f'<div class="plano-ano {cls}"><div class="k"><span>{html.escape(k)}</span>{q}</div>'
            f'<div class="v">{v}</div><div class="s">{html.escape(s)}</div></div>'
        )
    st.markdown(f'<div class="plano-anos">{"".join(parts)}</div>', unsafe_allow_html=True)


def _faixa_meses(ano: int, meta_anual: float, sazonal: bool, comp_modo: str) -> None:
    fat = load_fat_empresa_mensal((ano,))
    metas = metas_empresa_ano(ano, meta_anual, sazonal)
    pesos = pesos_meses(ano, sazonal)
    corrente = mes_corrente()
    comps: dict[int, float] = {}
    if comp_modo != COMP_DESLIGADA:
        comps = {m: compensacao_mes(ano, m, comp_modo).total_mes for m in meses_restantes(ano)}

    cells = []
    for m in range(1, 13):
        meta = metas[m] + comps.get(m, 0.0)
        real = fat.get((ano, m), 0.0)
        base = meta_plano_mes(ano, m, meta_anual, sazonal)
        if mes_fechado(ano, m):
            cls, tag = "fechado", "fechado"
        elif (ano, m) == corrente:
            cls, tag = "atual", "em andamento"
        else:
            cls, tag = "", "a vir"
        if mes_salvo(ano, m):
            tag += " · salvo"
        if cls in ("fechado", "atual"):
            pct = real / meta * 100 if meta > 0 else 0
            r = f"Realizado {mi(real)} · {_pct_meta(real, meta)}"
            bar = min(pct, 100)
        else:
            r = f"{pct_br(pesos[m] * 100)} do ano"
            bar = 0
        tip = (
            f"{MESES_NOME[m]}: meta do ano {mi(meta_anual)} × {pct_br(pesos[m] * 100)} = {mi(base)}."
        )
        if abs(metas[m] - base) >= 1:
            tip += f" Com ajustes manuais: {mi(metas[m])}."
        c_html = ""
        if comps.get(m):
            d = comps[m]
            c_html = (
                f'<div class="c {"up" if d > 0 else "down"}">'
                f'{"+" if d > 0 else "−"}{mi(abs(d))} compensação</div>'
            )
            tip += (
                f" Compensação: {'+' if d > 0 else '−'}{mi(abs(d))} "
                f"({'a equipe ficou devendo' if d > 0 else 'a equipe vendeu a mais'} nos meses fechados)."
            )
        if cls in ("fechado", "atual"):
            tip += f" Realizado: {mi(real)}."
        cells.append(
            f'<div class="plano-mes {cls}" data-tip="{_attr(tip)}">'
            f'<div class="n"><span>{MESES_CURTO[m]}</span><span class="tag">{tag}</span></div>'
            f'<div class="m">{mi(meta)}</div><div class="r">{r}</div>'
            f'<div class="bar"><i style="width:{bar:.0f}%"></i></div>{c_html}</div>'
        )
    st.markdown(f'<div class="plano-meses">{"".join(cells)}</div>', unsafe_allow_html=True)

    soma = sum(metas.values())
    extra = ""
    if meta_anual > 0 and abs(soma - meta_anual) >= 1_000:
        dif = soma - meta_anual
        extra = (
            f" · {'+' if dif > 0 else '−'}{mi(abs(dif))} de ajustes manuais nas metas dos colaboradores"
        )
    st.markdown(
        f'<div class="plano-soma">Soma dos 12 meses: <strong>{mi(soma)}</strong>{extra}</div>',
        unsafe_allow_html=True,
    )


def _usar_sugestao(key: str, valor: float) -> None:
    st.session_state[key] = format_br_number(round(valor, -3), 0)


@st.fragment
def render_plano_anual(ano: int) -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
    section_header(
        "1 · Meta do ano",
        "Defina só a meta anual. A meta de cada mês e de cada colaborador sai dela.",
    )
    meta_salva, saz_salva = get_config_ano(ano)
    fat = load_fat_empresa_mensal((ano,))
    _cards_anos(ano, sum(fat.values()), meta_salva)

    key_meta = f"plano_meta_{ano}"
    sug = sugestao_meta_anual(ano)
    c1, c2, c3 = st.columns([2.2, 1.3, 1.1], vertical_alignment="top")
    with c1:
        meta_in = brl_text_input(
            f"Meta anual {ano} (R$)",
            meta_salva,
            key=key_meta,
            help_text="Digite o valor do ano. Ao sair do campo, formata (ex.: 100.800.000).",
        )
    with c2:
        st.markdown('<div style="height:1.85rem"></div>', unsafe_allow_html=True)
        saz_in = st.toggle(
            "Sazonalidade",
            value=saz_salva,
            key=f"plano_saz_{ano}",
            help=_HELP_SAZONAL,
        )
    with c3:
        st.markdown('<div style="height:1.7rem"></div>', unsafe_allow_html=True)
        st.button(
            "Usar sugestão",
            key=f"plano_usar_sug_{ano}",
            on_click=_usar_sugestao,
            args=(key_meta, sug.sugestao),
            help=f"Preenche {mi(sug.sugestao)} no campo. Ainda é preciso salvar.",
            use_container_width=True,
        )

    pendente = abs(meta_in - meta_salva) >= 1 or saz_in != saz_salva
    piso = sug.fat_ano_menos_1 * 0.1
    meta_baixa = piso > 0 and meta_in < piso
    b1, b2 = st.columns([1, 3], vertical_alignment="center")
    with b1:
        salvar = st.button(
            "Salvar meta do ano",
            type="primary",
            key=f"plano_save_{ano}",
            disabled=not pendente or meta_in <= 0 or meta_baixa,
            use_container_width=True,
        )
    with b2:
        if meta_baixa:
            st.caption(
                f"⚠️ {mi(meta_in)} parece incompleto: {ano - 1} faturou {mi(sug.fat_ano_menos_1)}. "
                "Digite o valor inteiro (ex.: 100.800.000)."
            )
        elif pendente:
            st.caption("Prévia na tela. Clique em **Salvar meta do ano** para valer no painel.")
        elif meta_salva > 0:
            st.caption(
                f"Meta de {ano} salva: **{mi(meta_salva)}** · "
                f"sazonalidade {'ligada' if saz_salva else 'desligada'}."
            )
    if salvar:
        save_config_ano(ano, meta_in, saz_in)
        st.rerun(scope="app")

    if meta_baixa:
        meta_in = meta_salva
    comp_on = st.toggle(
        "Mostrar compensação",
        value=False,
        key=f"plano_comp_{ano}",
        help=_HELP_COMP,
    )
    _faixa_meses(ano, meta_in, saz_in, COMP_GERAL if comp_on else COMP_DESLIGADA)
    if comp_on:
        st.caption(
            "Os meses que faltam mostram a meta + o que a empresa ficou devendo (ou vendeu a mais) "
            "nos meses fechados, diluído pelo peso de cada mês. É só visão."
        )
