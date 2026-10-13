from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from app.brl_input import brl_text_input, format_br_number, int_br_text_input
from app.constants import label_mes
from app.data import (
    load_carteira_ativos,
    load_carteira_clientes,
    load_historico_meta_vendedor,
    load_metricas_vendedor_trimestre,
    load_oportunidades_rotas_equipe,
    load_realizado_dia,
    load_realizado_mes,
)
from app.meta_frigosol import estimate_oportunidades_mes, montar_bloco_frigosol
from app.dates_util import business_days_in_month
from app.formatting import fmt_brl_cell, fmt_pct
from app.premissas import CANAIS_VENDEDOR, PremissaVendedor, get_premissa, save_premissa
from app.table_style import style_meta_table
from app.ui import panel_box, section_header


def _bar_text(pct: float) -> str:
    p = min(max(float(pct), 0), 100)
    filled = int(round(p / 10))
    return "█" * filled + "░" * (10 - filled) + f" {p:.0f}%"


def _tabela_meta_display(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Mês": df["periodo"],
            "Clientes": df["clientes"],
            "Notas": df["notas"],
            "Faturamento": df["faturamento"].map(fmt_brl_cell),
            "Meta sugerida": df["meta_sugerida"].map(fmt_brl_cell),
            "Realizado": df["faturamento"].map(fmt_brl_cell),
            "Atingimento": df["atingimento"].map(fmt_pct),
            "Progresso": df["atingimento"].map(_bar_text),
            "Status": df["bateu"].map(lambda b: "Bateu" if b else "Não bateu"),
            "_bateu": df["bateu"],
        }
    )


def _fmt_brl_short(v: float) -> str:
    if abs(v) >= 1_000_000:
        return f"R$ {v/1_000_000:.2f} mi"
    if abs(v) >= 1_000:
        return f"R$ {v/1_000:.1f} mil"
    return f"R$ {v:,.0f}"


def _linhas_historico_completo(
    vid: int, ano: int, mes: int, taxa: float, meta_final: float | None = None
) -> pd.DataFrame:
    hist_df = load_historico_meta_vendedor(vid, ano, mes, taxa)
    if not meta_final or meta_final <= 0:
        return hist_df
    hist_df = hist_df.copy()
    if len(hist_df) > 0:
        i = len(hist_df) - 1
        hist_df.at[i, "meta_sugerida"] = meta_final
        fat = float(hist_df.at[i, "faturamento"])
        hist_df.at[i, "atingimento"] = (fat / meta_final * 100) if meta_final > 0 else 0
        hist_df.at[i, "bateu"] = fat >= meta_final if meta_final > 0 else False
    return hist_df


def _tabela_frigosol(
    mes_label: str,
    meta_cob: float,
    real_cob: float,
    meta_rec: float,
    real_rec: float,
    meta_pos: float,
    real_pos: float,
    meta_fat: float,
    real_fat: float,
) -> pd.DataFrame:
    def row(nome: str, meta: float, real: float, fmt):
        dif = real - meta
        return {
            "Indicador": nome,
            "Meta (gestor / sugerida)": fmt(meta),
            f"Realizado ({mes_label})": fmt(real),
            "Diferença": fmt(dif),
        }

    return pd.DataFrame(
        [
            row("Cobertura (clientes)", meta_cob, real_cob, lambda x: f"{x:.0f}"),
            row("Recorrência", meta_rec, real_rec, lambda x: f"{x:.2f}"),
            row("Positivação (notas)", meta_pos, real_pos, lambda x: f"{x:.0f}"),
            row("Faturamento (R$)", meta_fat, real_fat, fmt_brl_cell),
        ]
    )


def render_planejamento_colaborador(
    vid: int,
    nome: str,
    ano: int,
    mes: int,
    taxa_slider: float,
) -> None:
    section_header(
        f"{nome}",
        f"Código {vid} · {label_mes(ano, mes)}",
    )

    prem = get_premissa(vid, ano, mes)
    hist = load_metricas_vendedor_trimestre(vid, ano, mes)
    carteira = load_carteira_ativos(vid)
    real_mes = load_realizado_mes(vid, ano, mes)
    real_rec = (
        real_mes["notas"] / real_mes["clientes"] if real_mes["clientes"] else 0.0
    )
    oport_rotas_df = load_oportunidades_rotas_equipe()
    oport_rotas_row = oport_rotas_df.loc[oport_rotas_df["vendedor"] == vid]
    oport_rotas = (
        int(oport_rotas_row.iloc[0]["oportunidades_mes"])
        if not oport_rotas_row.empty
        else None
    )
    bloco_ini = montar_bloco_frigosol(
        carteira, hist, prem, taxa_slider, oportunidades_rotas=oport_rotas
    )
    oport_default = (
        int(prem.oportunidades_mes)
        if prem.oportunidades_mes > 0
        else bloco_ini.oportunidades_mes
    )
    conv_default = (
        prem.conversao_meta_pct
        if prem.conversao_meta_pct > 0
        else round(bloco_ini.tx_conv_oport_hist * 100, 1)
    )

    ating_ini = (
        (real_mes["faturamento"] / bloco_ini.meta_faturamento * 100)
        if bloco_ini.meta_faturamento > 0
        else 0
    )
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Carteira ativa", carteira)
    k2.metric("Faturamento no mês", _fmt_brl_short(real_mes["faturamento"]))
    k3.metric("Meta sugerida (motor)", _fmt_brl_short(bloco_ini.meta_faturamento))
    k4.metric("Atingimento no mês", fmt_pct(ating_ini))

    tab_erp, tab_prem, tab_res = st.tabs(
        [
            "Leitura do ERP",
            "Premissas do gestor",
            "Painel e histórico",
        ]
    )

    with tab_erp:
        panel_box(
            "Dados do mês e médias (somente leitura)",
            "Faturamento e carteira no EXTRACTOR — use como base para ajustar as premissas.",
            variant="readonly",
        )
        e1, e2 = st.columns(2)
        with e1:
            st.metric("Positivou no mês", real_mes["clientes"])
            st.metric("Notas no mês", real_mes["notas"])
            st.metric("Recorrência real", f"{real_rec:.2f}")
            st.metric(
                "Cobertura real",
                f"{real_mes['clientes'] / carteira * 100:.0f}%" if carteira else "—",
            )
            st.metric("Faturamento médio (3m)", _fmt_brl_short(bloco_ini.faturamento_media_3m))
            st.metric("Ticket histórico (3m)", _fmt_brl_short(bloco_ini.ticket_historico))
        with e2:
            st.metric("Cobertura média (3m)", f"{bloco_ini.cobertura_media_3m:.0f} clientes")
            st.metric("Positivação média (3m)", f"{bloco_ini.positivacao_media_3m:.0f}")
            st.metric("Recorrência média (3m)", f"{bloco_ini.recorrencia_media:.2f}")
            st.metric(
                "TX conv. oport. (hist.)",
                f"{bloco_ini.tx_conv_oport_hist * 100:.1f}%",
            )
            st.metric("Oportunidades (rotas/premissa)", bloco_ini.oportunidades_mes)

    with tab_prem:
        panel_box(
            "Parametrizar metas",
            "Equivalente às células que o chefe preenche na planilha. Salvas localmente.",
            variant="param",
        )
        canal = st.selectbox(
            "Canal do vendedor",
            CANAIS_VENDEDOR,
            index=CANAIS_VENDEDOR.index(prem.canal)
            if prem.canal in CANAIS_VENDEDOR
            else 0,
            key=f"canal_{vid}_{ano}_{mes}",
        )
        st.caption(
            "Oportunidades: deixe **0** para usar ROTAS AVINOR (padrão). "
            "Qualquer valor positivo sobrescreve manualmente."
            if bloco_ini.oportunidades_fonte_rotas
            else "Oportunidades: use 0 para estimar (≈ carteira × 1,04 × 4) se a planilha de rotas não estiver disponível."
        )
        oport_mes = float(
            int_br_text_input(
                "Oportunidades no mês",
                int(oport_default),
                key=f"poport_{vid}_{ano}_{mes}",
                help_text="Deixe 0 para usar ROTAS AVINOR. Use pontos de milhar se precisar.",
            )
        )
        conversao_pct = st.number_input(
            "Conversão meta (%) — coluna F da planilha",
            min_value=0.0,
            max_value=100.0,
            value=float(conv_default),
            step=0.5,
            format="%.1f",
            key=f"pconv_{vid}_{ano}_{mes}",
        )
        taxa = st.slider(
            "% cobertura da carteira (meta)",
            0.05,
            1.0,
            float(prem.taxa_cobertura or taxa_slider),
            0.01,
            key=f"taxa_p_{vid}_{ano}_{mes}",
        )
        c1, c2 = st.columns(2)
        with c1:
            ticket_meta = brl_text_input(
                "Ticket médio (meta) — col. P",
                float(prem.ticket_meta or bloco_ini.ticket_historico),
                key=f"pticket_{vid}_{ano}_{mes}",
                decimals=2,
            )
            meta_cob = float(
                int_br_text_input(
                    "Cobertura meta (clientes) — col. I",
                    int(prem.meta_cobertura_qtd or bloco_ini.cobertura_meta),
                    key=f"pcob_{vid}_{ano}_{mes}",
                )
            )
        with c2:
            meta_rec = st.number_input(
                "Recorrência meta — col. R",
                min_value=0.1,
                value=float(prem.meta_recorrencia or bloco_ini.recorrencia_media),
                step=0.05,
                format="%.2f",
                key=f"prec_{vid}_{ano}_{mes}",
            )
            usar_oficial = st.toggle(
                "Travar meta em R$ (sobrescreve fórmula)",
                value=prem.usar_meta_oficial_rs,
                key=f"pof_{vid}_{ano}_{mes}",
            )
            if usar_oficial:
                meta_rs = brl_text_input(
                    "Meta faturamento (R$) — col. S",
                    float(prem.meta_faturamento_rs or bloco_ini.meta_formula),
                    key=f"prs_{vid}_{ano}_{mes}",
                )
            else:
                meta_rs = float(bloco_ini.meta_formula)
                st.text_input(
                    "Meta faturamento (R$) — col. S",
                    value=format_br_number(meta_rs, 0) if meta_rs else "0",
                    disabled=True,
                    key=f"prs_off_{vid}_{ano}_{mes}",
                )
                st.caption(f"Calculada pela fórmula · ≈ {fmt_brl_cell(meta_rs)}")

        if st.button("Salvar premissas deste mês", type="primary", key=f"save_{vid}_{ano}_{mes}"):
            save_premissa(
                vid,
                ano,
                mes,
                PremissaVendedor(
                    canal=canal,
                    oportunidades_mes=oport_mes,
                    conversao_meta_pct=conversao_pct,
                    meta_faturamento_rs=meta_rs,
                    meta_cobertura_qtd=meta_cob,
                    meta_recorrencia=meta_rec,
                    meta_positivacao=oport_mes * (conversao_pct / 100.0),
                    tx_conv_projetada_pct=conversao_pct,
                    ticket_meta=ticket_meta,
                    taxa_cobertura=taxa,
                    usar_meta_oficial_rs=usar_oficial,
                ),
            )
            st.success("Premissas salvas localmente.")

    prem_live = PremissaVendedor(
        canal=canal,
        oportunidades_mes=oport_mes,
        conversao_meta_pct=conversao_pct,
        meta_faturamento_rs=meta_rs,
        meta_cobertura_qtd=meta_cob,
        meta_recorrencia=meta_rec,
        meta_positivacao=oport_mes * (conversao_pct / 100.0),
        ticket_meta=ticket_meta,
        taxa_cobertura=taxa,
        usar_meta_oficial_rs=usar_oficial,
    )
    bloco = montar_bloco_frigosol(
        carteira, hist, prem_live, taxa, oportunidades_rotas=oport_rotas
    )
    meta_fat_final = bloco.meta_faturamento
    meta_formula = bloco.meta_formula

    with tab_res:
        section_header(
            "Painel (espelho da planilha)",
            "Calculado em tempo real com as alavancas da aba Premissas.",
        )
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Carteira": carteira,
                        "Oportunidades": bloco.oportunidades_mes,
                        "TX conv. oport.": f"{bloco.tx_conv_oport_hist * 100:.1f}%",
                        "Conversão meta": f"{bloco.conversao_meta * 100:.1f}%",
                        "Oport. calc. (posit.)": f"{bloco.oport_calc_positivacao:.1f}",
                        "Cob. média 3m": f"{bloco.cobertura_media_3m:.0f}",
                        "Cobertura meta": f"{bloco.cobertura_meta:.0f}",
                        "Dif. cart.×cob.": f"{bloco.diff_carteira_cobertura:.0f}",
                        "Ticket hist.": _fmt_brl_short(bloco.ticket_historico),
                        "Ticket meta": _fmt_brl_short(bloco.ticket_meta),
                        "Rec. média": f"{bloco.recorrencia_media:.2f}",
                        "Rec. meta": f"{bloco.recorrencia_meta:.2f}",
                        "Meta (R$)": _fmt_brl_short(meta_fat_final),
                        "Meta fórmula": _fmt_brl_short(meta_formula),
                    }
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
        if bloco.oportunidades_estimada:
            st.caption(
                f"Oportunidades estimadas ({estimate_oportunidades_mes(carteira)}). "
                "Informe manualmente ou confira a planilha ROTAS AVINOR."
            )
        elif bloco.oportunidades_fonte_rotas and not oport_rotas_row.empty:
            sem = int(oport_rotas_row.iloc[0]["clientes_sem_rota"])
            map_ = int(oport_rotas_row.iloc[0]["clientes_mapeados"])
            st.caption(
                f"Oportunidades pela planilha **ROTAS AVINOR** (Enviar cards × 4 semanas): "
                f"{map_} clientes mapeados"
                + (f", {sem} com fallback estimado (cidade/bairro sem rota)." if sem else ".")
            )

        section_header(
            "Meta × realizado (mês atual)",
            "Comparativo com o que já faturou no período.",
        )
        st.dataframe(
            _tabela_frigosol(
                label_mes(ano, mes),
                meta_cob,
                float(real_mes["clientes"]),
                meta_rec,
                real_rec,
                bloco.positivacoes_meta,
                float(real_mes["notas"]),
                meta_fat_final,
                float(real_mes["faturamento"]),
            ),
            use_container_width=True,
            hide_index=True,
        )

        section_header(
            "Histórico mensal",
            "Últimos 3 meses fechados + mês em andamento.",
        )
        tabela_full = _linhas_historico_completo(vid, ano, mes, taxa, meta_fat_final)
        st.dataframe(
            style_meta_table(_tabela_meta_display(tabela_full)),
            use_container_width=True,
            hide_index=True,
            height=320,
        )

        dias_uteis = business_days_in_month(ano, mes)
        meta_dia = meta_fat_final / dias_uteis if dias_uteis else 0
        hoje = date.today()
        real_hoje = (
            load_realizado_dia(vid, hoje) if hoje.month == mes and hoje.year == ano else 0.0
        )
        ating_mes = (
            (real_mes["faturamento"] / meta_fat_final * 100) if meta_fat_final > 0 else 0
        )

        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Meta fórmula (T×R×C)", _fmt_brl_short(meta_formula))
        p2.metric("Meta em uso", _fmt_brl_short(meta_fat_final))
        p3.metric("Meta / dia útil", _fmt_brl_short(meta_dia))
        p4.metric("Conversão meta", f"{conversao_pct:.1f}%")

        prog = (
            min(1.0, real_mes["faturamento"] / meta_fat_final)
            if meta_fat_final > 0
            else 0.0
        )
        st.progress(
            prog,
            text=f"{_bar_text(ating_mes)} · {_fmt_brl_short(real_mes['faturamento'])} de "
            f"{_fmt_brl_short(meta_fat_final)}",
        )
        if hoje.month == mes and hoje.year == ano and meta_dia > 0:
            st.progress(
                min(1.0, real_hoje / meta_dia),
                text=f"Hoje: {_fmt_brl_short(real_hoje)} · meta do dia {_fmt_brl_short(meta_dia)}",
            )

        with st.expander("Carteira de clientes", expanded=False):
            cart = load_carteira_clientes(vid)
            if cart.empty:
                st.info("Nenhum cliente no cadastro.")
            else:
                show = cart.copy()
                if "ultima_compra" in show.columns:
                    show["ultima_compra"] = pd.to_datetime(show["ultima_compra"]).dt.strftime(
                        "%d/%m/%Y"
                    )
                show["valor_ultima_nota"] = show["valor_ultima_nota"].fillna(0).map(_fmt_brl_short)
                st.dataframe(
                    show[
                        [
                            "cliente",
                            "nome",
                            "cidade",
                            "uf",
                            "situacao",
                            "ultima_compra",
                            "valor_ultima_nota",
                        ]
                    ].rename(
                        columns={
                            "cliente": "Cód.",
                            "nome": "Cliente",
                            "cidade": "Cidade",
                            "uf": "UF",
                            "situacao": "Situação",
                            "ultima_compra": "Última compra",
                            "valor_ultima_nota": "Valor última nota",
                        }
                    ),
                    use_container_width=True,
                    hide_index=True,
                )
