from __future__ import annotations

import pandas as pd
import streamlit as st

from app.brl_input import brl_text_input
from app.data import (
    load_carteira_ativos,
    load_metricas_vendedor_trimestre,
    load_oportunidades_rotas_equipe,
    load_panorama_metas_equipe,
    load_ranking_periodo,
)
from app.dates_util import month_bounds
from app.meta_frigosol import montar_bloco_frigosol
from app.plano_metas import meta_empresa_mes
from app.premissas import (
    PremissaEmpresa,
    PremissaVendedor,
    count_premissas_vendedor_mes,
    get_premissa_empresa,
    save_premissa,
    save_premissa_empresa,
    vendedor_tem_premissa,
)


def _fmt_brl_short(v: float) -> str:
    if abs(v) >= 1_000_000:
        return f"R$ {v/1_000_000:.2f} mi"
    if abs(v) >= 1_000:
        return f"R$ {v/1_000:.1f} mil"
    return f"R$ {v:,.0f}"


@st.fragment
def render_meta_empresa_mes(
    ano: int,
    mes: int,
    taxa: float,
    key_prefix: str = "emp",
    expanded: bool = True,
    embedded: bool = False,
    defer_analytics: bool = False,
    somente_meta_empresa: bool = False,
) -> None:
    """Meta empresa (+ limites de canal, se Avinor não usar somente_meta_empresa)."""
    emp = get_premissa_empresa(ano, mes)
    falta_key = f"{key_prefix}_falta_{ano}_{mes}"

    def _body() -> None:
        st.caption(
            "Na planilha Frigosol isso fica no PAINEL (meta total e tetos). "
            "Salve aqui; a soma da equipe você vê na aba **Visão geral** (após configurar)."
            if defer_analytics
            else "Salve para gravar; use o botão abaixo para somar metas da equipe."
        )
        if somente_meta_empresa:
            meta_anual = brl_text_input(
                "Meta anual da empresa (R$)",
                float(emp.meta_empresa_anual_rs),
                key=f"{key_prefix}_meta_anual_{ano}_{mes}",
            )
            meta_emp = brl_text_input(
                "Meta do mês (R$) — opcional se usar anual",
                float(emp.meta_empresa_rs),
                key=f"{key_prefix}_meta_{ano}_{mes}",
            )
            if meta_anual > 0:
                st.caption(
                    f"Referência mensal (anual ÷ 12): **{_fmt_brl_short(meta_anual / 12)}** "
                    "— usada nas colunas amarelas da grade."
                )
            lim_tel = lim_ext = lim_gr = 0.0
        else:
            e0, e1, e2, e3, e4 = st.columns(5)
            with e0:
                meta_anual = brl_text_input(
                    "Meta anual (R$)",
                    float(emp.meta_empresa_anual_rs),
                    key=f"{key_prefix}_meta_anual_{ano}_{mes}",
                )
            with e1:
                meta_emp = brl_text_input(
                    "Meta empresa mês (R$)",
                    float(emp.meta_empresa_rs),
                    key=f"{key_prefix}_meta_{ano}_{mes}",
                )
            with e2:
                lim_tel = brl_text_input(
                    "Limite televendas (R$)",
                    float(emp.limite_televendas_rs),
                    key=f"{key_prefix}_tel_{ano}_{mes}",
                )
            with e3:
                lim_ext = brl_text_input(
                    "Limite externo (R$)",
                    float(emp.limite_externo_rs),
                    key=f"{key_prefix}_ext_{ano}_{mes}",
                )
            with e4:
                lim_gr = brl_text_input(
                    "Limite grandes redes (R$)",
                    float(emp.limite_grandes_redes_rs),
                    key=f"{key_prefix}_gr_{ano}_{mes}",
                )
        if st.button(
            "Salvar meta da empresa",
            type="primary",
            key=f"{key_prefix}_save_{ano}_{mes}",
        ):
            save_premissa_empresa(
                ano,
                mes,
                PremissaEmpresa(
                    meta_empresa_anual_rs=meta_anual,
                    meta_empresa_rs=meta_emp,
                    limite_televendas_rs=lim_tel,
                    limite_externo_rs=lim_ext,
                    limite_grandes_redes_rs=lim_gr,
                ),
            )
            st.session_state[falta_key] = False
            st.success("Premissas salvas. Rode **Atualizar conferência** no Início ou vá às outras abas.")
            st.rerun()

        emp_ref = meta_empresa_mes(ano, mes)
        if defer_analytics:
            if emp_ref > 0:
                st.caption(f"Meta mensal de referência: **{_fmt_brl_short(emp_ref)}**")
            return

        if emp_ref > 0 and st.button(
            "Calcular FALTA / soma das metas da equipe",
            key=f"{key_prefix}_calc_falta_{ano}_{mes}",
        ):
            st.session_state[falta_key] = True

        if emp_ref > 0 and st.session_state.get(falta_key):
            with st.spinner("Somando metas da equipe…"):
                pano = load_panorama_metas_equipe(ano, mes, taxa)
            if not pano.empty:
                soma = float(pano["meta_sugerida"].sum())
                falta = emp_ref - soma
                m1, m2 = st.columns(2)
                m1.metric("Soma metas vendedores", _fmt_brl_short(soma))
                m2.metric(
                    "FALTA / SOBRA",
                    _fmt_brl_short(falta),
                    delta="OK" if abs(falta) < 1 else "Ajustar alavancas",
                )

    if embedded:
        _body()
    else:
        with st.expander(
            "Meta da empresa e limites por canal (premissas do mês)",
            expanded=expanded,
        ):
            _body()


def _oportunidades_vendedor(vendedor_id: int) -> int | None:
    df = load_oportunidades_rotas_equipe()
    row = df.loc[df["vendedor"] == vendedor_id]
    if row.empty:
        return None
    return int(row.iloc[0]["oportunidades_mes"])


def aplicar_premissas_sugeridas_pendentes(ano: int, mes: int, taxa: float) -> int:
    ini, fim = month_bounds(ano, mes)
    ranking = load_ranking_periodo(ini, fim, 80)
    if ranking.empty:
        return 0
    salvos = 0
    for r in ranking.itertuples():
        if vendedor_tem_premissa(int(r.vendedor), ano, mes):
            continue
        vid = int(r.vendedor)
        hist = load_metricas_vendedor_trimestre(vid, ano, mes)
        cart = (
            int(r.carteira)
            if getattr(r, "carteira", None) is not None and pd.notna(r.carteira)
            else load_carteira_ativos(vid)
        )
        oport_rotas = _oportunidades_vendedor(vid)
        bloco = montar_bloco_frigosol(
            cart, hist, PremissaVendedor(), taxa, oportunidades_rotas=oport_rotas
        )
        save_premissa(
            vid,
            ano,
            mes,
            PremissaVendedor(
                oportunidades_mes=0,
                conversao_meta_pct=round(bloco.conversao_meta * 100, 1),
                meta_cobertura_qtd=bloco.cobertura_meta,
                meta_recorrencia=bloco.recorrencia_meta,
                meta_positivacao=bloco.positivacoes_meta,
                tx_conv_projetada_pct=round(bloco.conversao_meta * 100, 1),
                ticket_meta=bloco.ticket_meta,
                taxa_cobertura=taxa,
            ),
        )
        salvos += 1
    return salvos

@st.fragment
def render_premissas_vendedores_checklist(
    ano: int,
    mes: int,
    taxa: float,
    key_prefix: str = "chk_vend",
) -> None:
    ini, fim = month_bounds(ano, mes)
    ranking = load_ranking_periodo(ini, fim, 80)
    if ranking.empty:
        st.info("Sem vendedores com venda no mês para gravar premissas.")
        return
    total = len(ranking)
    com_prem = sum(
        1 for r in ranking.itertuples() if vendedor_tem_premissa(int(r.vendedor), ano, mes)
    )
    pendentes = total - com_prem
    st.caption(
        f"**{com_prem}** de **{total}** com premissa salva em {ano}/{mes:02d}. "
        "Salvar grava sugestão do motor (histórico + rotas + cobertura padrão)."
    )
    if pendentes > 0:
        nomes_pend = [
            r.nome
            for r in ranking.itertuples()
            if not vendedor_tem_premissa(int(r.vendedor), ano, mes)
        ]
        txt = ", ".join(nomes_pend[:12])
        if len(nomes_pend) > 12:
            txt += f" … (+{len(nomes_pend) - 12})"
        st.write("Pendentes:", txt)
    if st.button(
        f"Salvar premissas sugeridas ({pendentes} pendente(s))",
        type="primary",
        key=f"{key_prefix}_batch_{ano}_{mes}",
        disabled=pendentes == 0,
    ):
        n = aplicar_premissas_sugeridas_pendentes(ano, mes, taxa)
        load_panorama_metas_equipe.clear()
        st.success(f"{n} colaborador(es) atualizados.")
        st.rerun()
    st.caption(
        "Meta em R$ de cada colaborador: tabela da seção **2 · Metas do mês**."
    )


@st.fragment
def render_rotas_upload(key_prefix: str = "chk_rotas") -> None:
    from app.rotas_oportunidades import rotas_file_info, save_rotas_workbook

    info = rotas_file_info()
    if info["presente"]:
        dt = info["atualizado_em"]
        dt_s = dt.strftime("%d/%m/%Y %H:%M") if dt else "—"
        st.caption(f"Arquivo atual: {dt_s}")
    up = st.file_uploader(
        "Enviar ROTAS AVINOR (.xlsx)",
        type=["xlsx"],
        key=f"{key_prefix}_file",
    )
    if up is not None and st.button(
        "Salvar planilha de rotas",
        type="primary",
        key=f"{key_prefix}_save",
    ):
        path = save_rotas_workbook(up.getvalue())
        load_oportunidades_rotas_equipe.clear()
        load_panorama_metas_equipe.clear()
        st.success(f"Salvo em `{path}`.")
        st.rerun()
