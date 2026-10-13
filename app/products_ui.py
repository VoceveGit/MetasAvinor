from __future__ import annotations

import html
from datetime import date

import pandas as pd
import streamlit as st

from app.charts import chart_familia_pizza, familias_agrupadas
from app.constants import MESES_NOME, label_mes
from app.data import (
    load_clientes_parados,
    load_faturamento_por_familia,
    load_faturamento_top_produtos,
    load_preco_medio_produto_vendedor,
)
from app.dates_util import month_bounds
from app.cities_ui import render_cidades_recorrencia
from app.formatting import fmt_brl_cell
from app.table_display import css_sinal, show_data_table
from app.ui import section_header


_HELP_FAM = {
    "Faturamento": "Soma do valor dos itens da família no período.",
    "% do total": "Faturamento da família ÷ faturamento de todas as famílias.",
    "Notas": "Quantas notas fiscais tiveram pelo menos um item da família.",
    "Clientes": "Clientes diferentes que compraram a família.",
    "Peso (kg)": "Soma do peso dos itens vendidos.",
}
_HELP_PROD = {
    "Faturamento": "Soma do valor do produto no período.",
    "% (top)": "Faturamento do produto ÷ soma dos produtos desta lista.",
    "Notas": "Quantas notas fiscais tiveram o produto.",
}
_HELP_PRECO = {
    "Preço médio vendedor": "Faturamento do produto ÷ quantidade vendida, só nas vendas deste vendedor.",
    "Preço médio equipe": "Mesma conta com as vendas de toda a equipe.",
    "Desvio %": (
        "Preço do vendedor ÷ preço da equipe − 1. Vermelho = vendeu mais barato que a média "
        "(ex.: R$ 13 ÷ R$ 15 − 1 = −13%); verde = mais caro."
    ),
    "Faturamento item": "Quanto o vendedor faturou com o produto no período.",
    "Notas": "Notas fiscais do vendedor com o produto.",
}
_HELP_PARADOS = {
    "Status": "🟢 comprou nos últimos 30 dias · 🟡 1 a 2 meses sem comprar · 🔴 3 meses ou mais.",
    "Última compra": "Data da última nota do cliente (com qualquer vendedor).",
    "Dias sem comprar": "Dias corridos desde a última compra até hoje.",
    "Média mensal 3m": "Faturamento dos 3 meses até a última compra ÷ 3 — quanto o cliente comprava por mês.",
}

_PROD_CSS = """
<style>
.prod-kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:.6rem;margin:.2rem 0 1rem}
.prod-kpi{background:#fff;border:1px solid #dfe7e2;border-radius:12px;padding:.65rem .85rem}
.prod-kpi span{display:block;font-size:.8rem;color:#5b6b63;text-transform:uppercase;letter-spacing:.04em}
.prod-kpi strong{font-size:1.3rem;color:#12261d}
.prod-leg{display:flex;flex-direction:column;gap:.55rem;padding-top:1.6rem}
.prod-leg-row{display:grid;grid-template-columns:14px auto minmax(24px,1fr) 108px 62px;gap:.6rem;align-items:center;font-size:1.02rem;color:#1f2d27}
.prod-leg-row i{width:14px;height:14px;border-radius:4px;display:block}
.prod-leg-row .nm{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:260px;font-weight:600}
.prod-leg-row .ln{height:3px;border-radius:2px;opacity:.75;display:block}
.prod-leg-row .vl{font-variant-numeric:tabular-nums;color:#33433b;text-align:right}
.prod-leg-row .pc{font-weight:800;text-align:right;font-variant-numeric:tabular-nums}
.prod-block{font-size:1.12rem;font-weight:700;color:#12261d;margin:1.2rem 0 .35rem;padding-left:.55rem;border-left:4px solid #2f6b55}
.prod-risk{display:flex;flex-wrap:wrap;gap:.5rem;margin:.2rem 0 .6rem}
.prod-risk span{border-radius:999px;padding:.3rem .8rem;font-size:.95rem;font-weight:700}
.prod-risk .tot{background:#fdecea;color:#b42318;border:1px solid #f5c2bd}
.prod-risk .am{background:#fff6dd;color:#8a6100;border:1px solid #f0d998}
.prod-risk .vm{background:#fdecea;color:#b42318;border:1px solid #f5c2bd}
</style>
"""


def _bloco(titulo: str) -> None:
    st.markdown(f'<div class="prod-block">{html.escape(titulo)}</div>', unsafe_allow_html=True)


def _periodo_produtos(ano: int, mes: int) -> tuple[int, int]:
    hoje = date.today()
    anos = [hoje.year - i for i in range(4)]
    c1, c2, _ = st.columns([1, 1.4, 3])
    with c1:
        a = st.selectbox("Ano", anos, index=anos.index(ano) if ano in anos else 0, key="prod_ano")
    with c2:
        meses = list(range(1, 13 if a < hoje.year else hoje.month + 1))
        m = st.selectbox(
            "Mês",
            meses,
            index=meses.index(mes) if mes in meses else len(meses) - 1,
            format_func=lambda x: MESES_NOME[x],
            key="prod_mes",
        )
    return int(a), int(m)


def _legenda_familias(fam: pd.DataFrame) -> str:
    rows = "".join(
        f'<div class="prod-leg-row"><i style="background:{r.cor}"></i>'
        f'<span class="nm" title="{html.escape(str(r.familia))}">{html.escape(str(r.familia))}</span>'
        f'<b class="ln" style="background:{r.cor}"></b>'
        f'<span class="vl">{fmt_brl_cell(r.faturamento)}</span>'
        f'<span class="pc">{r.pct:.1f}%</span></div>'
        for r in familias_agrupadas(fam).itertuples()
    )
    return f'<div class="prod-leg">{rows}</div>'


def _status_parado(dias: int) -> str:
    if dias < 30:
        return "🟢 Ativo"
    if dias < 90:
        return "🟡 1–2 meses"
    return "🔴 3+ meses"


def _render_clientes_parados() -> None:
    _bloco("Clientes que pararam de comprar")
    hoje = date.today()
    df = load_clientes_parados(hoje)
    if df.empty:
        st.info("Sem compras nos últimos 6 meses para analisar.")
        return
    df = df[df["media_3m"] > 0].copy()
    vend_opts = sorted({(int(v), str(n)) for v, n in zip(df["vendedor"], df["vendedor_nome"])}, key=lambda t: t[1])
    c1, c2, _ = st.columns([1.6, 1.4, 2])
    with c1:
        escolha = st.selectbox(
            "Vendedor",
            [0] + [v for v, _ in vend_opts],
            format_func=lambda v: "Todos" if v == 0 else dict(vend_opts).get(v, str(v)),
            key="parados_vend",
        )
    with c2:
        ver = st.segmented_control(
            "Mostrar",
            ["Parados", "Todos"],
            default="Parados",
            key="parados_ver",
            help="Parados = 1 mês ou mais sem comprar.",
        ) or "Parados"
    if escolha:
        df = df[df["vendedor"] == escolha]
    parados = df[df["dias"] >= 30]
    am = parados[parados["dias"] < 90]
    vm = parados[parados["dias"] >= 90]
    st.markdown(
        f'<div class="prod-risk"><span class="tot">⚠ {len(parados)} clientes · '
        f'{fmt_brl_cell(parados["media_3m"].sum())}/mês em risco</span>'
        f'<span class="am">🟡 {len(am)} com 1–2 meses · {fmt_brl_cell(am["media_3m"].sum())}/mês</span>'
        f'<span class="vm">🔴 {len(vm)} com 3+ meses · {fmt_brl_cell(vm["media_3m"].sum())}/mês</span></div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Valor em risco = soma da **média mensal** de cada cliente parado "
        "(faturamento dos 3 meses até a última compra ÷ 3). "
        "É quanto deixa de entrar por mês se esses clientes não voltarem."
    )
    base = parados if ver == "Parados" else df
    if base.empty:
        st.success("Nenhum cliente parado neste filtro.")
        return
    base = base.sort_values("media_3m", ascending=False)
    tbl = pd.DataFrame({
        "Status": base["dias"].map(_status_parado),
        "Vendedor": base["vendedor_nome"].astype(str),
        "Cliente": base["cliente_nome"].astype(str),
        "Cidade": base["cidade"].fillna("—").astype(str).str.title(),
        "Última compra": base["ult"].map(lambda d: d.strftime("%d/%m/%Y")),
        "Dias sem comprar": base["dias"].astype(int),
        "Média mensal 3m": base["media_3m"],
    })

    def _css_dias(v: float) -> str:
        if v >= 90:
            return "color:#b42318;font-weight:700"
        if v >= 30:
            return "color:#8a6100;font-weight:700"
        return "color:#1f7a4d"

    show_data_table(
        tbl,
        spec={"Dias sem comprar": "int", "Média mensal 3m": "money"},
        helps=_HELP_PARADOS,
        total=["Média mensal 3m"],
        styles={"Dias sem comprar": _css_dias},
        height=min(460, 40 + (len(tbl) + 1) * 35),
    )


def render_produtos_linhas(
    ano: int,
    mes: int,
    vendedor_id: int | None,
) -> None:
    st.markdown(_PROD_CSS, unsafe_allow_html=True)
    section_header(
        "Produtos e famílias",
        "Vendas por linha de produto (família do ERP), produtos mais vendidos, preço médio e clientes parados.",
    )
    ano, mes = _periodo_produtos(ano, mes)

    ini, fim = month_bounds(ano, mes)
    fam = load_faturamento_por_familia(ini, fim, vendedor_id)
    prod = load_faturamento_top_produtos(ini, fim, vendedor_id, limit=30)

    if fam.empty:
        st.warning(f"Sem faturamento por produto em {label_mes(ano, mes)}.")
    else:
        total = float(fam["faturamento"].sum())
        top = fam.iloc[0]
        peso_txt = f"{float(fam['peso_kg'].sum()):,.0f}".replace(",", ".")
        st.markdown(
            f'<div class="prod-kpis">'
            f'<div class="prod-kpi"><span>Faturamento analisado</span><strong>{fmt_brl_cell(total)}</strong></div>'
            f'<div class="prod-kpi"><span>Famílias vendidas</span><strong>{len(fam)}</strong></div>'
            f'<div class="prod-kpi"><span>Família líder</span><strong>{html.escape(str(top["familia"]))}</strong></div>'
            f'<div class="prod-kpi"><span>Peso total</span><strong>{peso_txt} kg</strong></div>'
            f"</div>",
            unsafe_allow_html=True,
        )

        _bloco(f"Mix por família — {MESES_NOME[mes]}/{ano}")
        c1, c2 = st.columns([1, 1.15])
        with c1:
            st.plotly_chart(
                chart_familia_pizza(fam, ""),
                use_container_width=True,
                config={"displayModeBar": False},
            )
        with c2:
            st.markdown(_legenda_familias(fam), unsafe_allow_html=True)

        _bloco("Por família (linha de produto)")
        fam_tbl = fam.rename(
            columns={
                "familia": "Família",
                "faturamento": "Faturamento",
                "pct": "% do total",
                "notas": "Notas",
                "clientes": "Clientes",
                "peso_kg": "Peso (kg)",
            }
        )[["Família", "Faturamento", "% do total", "Notas", "Clientes", "Peso (kg)"]]
        show_data_table(
            fam_tbl,
            spec={"Faturamento": "money", "Notas": "int", "Clientes": "int", "Peso (kg)": "int"},
            helps=_HELP_FAM,
            total=["Faturamento", "Peso (kg)"],
            progress=["% do total"],
            height=min(420, 40 + (len(fam_tbl) + 1) * 35),
        )

    if not prod.empty:
        _bloco("Top produtos (código + descrição)")
        prod_tbl = prod.rename(
            columns={
                "codigo": "Cód.",
                "produto": "Descrição",
                "familia": "Família",
                "faturamento": "Faturamento",
                "pct": "% (top)",
                "notas": "Notas",
            }
        )[["Cód.", "Descrição", "Família", "Faturamento", "% (top)", "Notas"]]
        show_data_table(
            prod_tbl,
            spec={"Faturamento": "money", "Notas": "int"},
            helps=_HELP_PROD,
            total=["Faturamento"],
            progress=["% (top)"],
            height=420,
        )

    _bloco("Preço médio por vendedor e produto")
    preco_all = load_preco_medio_produto_vendedor(ini, fim, limit=120)
    if preco_all.empty:
        st.info("Sem itens suficientes para comparar preço médio no período.")
    else:
        sellers = preco_all.drop_duplicates("vendedor").sort_values("nome")
        opcoes_vend = ["Todos (lista completa)"] + [
            f"{int(r.vendedor)} — {r.nome}" for r in sellers.itertuples()
        ]
        escolha_vend = st.selectbox(
            "Ver vendas de um vendedor",
            opcoes_vend,
            key=f"preco_vend_{ano}_{mes}",
            help="Escolha o vendedor para filtrar a tabela (itens com preço abaixo da média da equipe).",
        )
        if escolha_vend == opcoes_vend[0]:
            preco = preco_all
        else:
            vid = int(escolha_vend.split(" — ")[0])
            nome_v = escolha_vend.split(" — ", 1)[1]
            preco = load_preco_medio_produto_vendedor(
                ini, fim, vendedor_id=vid, only_below_team=True
            )
            if preco.empty:
                preco = load_preco_medio_produto_vendedor(
                    ini, fim, vendedor_id=vid, only_below_team=False
                )
                st.caption(
                    f"**{nome_v}** — todos os produtos do período "
                    "(nenhum ficou abaixo da média da equipe)."
                )
            else:
                st.caption(
                    f"**{nome_v}** — produtos com preço médio abaixo da equipe no período."
                )
            vendas = load_faturamento_top_produtos(ini, fim, vid, limit=25)
            if not vendas.empty:
                st.markdown("##### Vendas do vendedor (top produtos)")
                vendas_tbl = vendas.rename(
                    columns={
                        "codigo": "Cód.",
                        "produto": "Descrição",
                        "familia": "Família",
                        "faturamento": "Faturamento",
                        "pct": "% (top)",
                        "notas": "Notas",
                    }
                )[["Cód.", "Descrição", "Família", "Faturamento", "% (top)", "Notas"]]
                show_data_table(
                    vendas_tbl,
                    spec={"Faturamento": "money", "Notas": "int"},
                    helps=_HELP_PROD,
                    total=["Faturamento"],
                    progress=["% (top)"],
                    height=min(360, 40 + (len(vendas_tbl) + 1) * 35),
                )

        show_data_table(
            preco.rename(
                columns={
                    "vendedor": "Cód.",
                    "nome": "Vendedor",
                    "produto": "Produto",
                    "preco_vendedor": "Preço médio vendedor",
                    "preco_equipe": "Preço médio equipe",
                    "desvio_pct": "Desvio %",
                    "faturamento": "Faturamento item",
                    "notas": "Notas",
                }
            ),
            spec={
                "Preço médio vendedor": "money",
                "Preço médio equipe": "money",
                "Desvio %": "pct",
                "Faturamento item": "money",
                "Notas": "int",
            },
            helps=_HELP_PRECO,
            total=["Faturamento item", "Notas"],
            styles={"Desvio %": css_sinal},
            height=min(480, 40 + (len(preco) + 1) * 35),
        )

    try:
        _render_clientes_parados()
    except Exception as exc:
        st.warning(f"Clientes parados indisponível neste momento: {exc}")

    st.markdown("---")
    try:
        render_cidades_recorrencia(ano, mes, vendedor_id)
    except Exception as exc:
        st.warning(f"Mapa de cidades indisponível neste momento: {exc}")
