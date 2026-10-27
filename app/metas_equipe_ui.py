from __future__ import annotations

import html
from datetime import datetime

import streamlit as st

from app.constants import MESES_NOME, label_mes
from app.data import (
    load_grid_metas_colaboradores,
    load_panorama_metas_equipe,
)
from app.dates_util import business_days_in_month
from app.equipe_grid_logic import (
    EDITABLE_KEYS,
    _f as _f_num,
    limpar_insercoes,
    loader_rows_to_state,
    meta_final_row,
    premissa_from_row,
    recalc_row_formulas_only,
    rows_from_aggrid_df,
)
from app.equipe_grid_ui import (
    lote_keys_ativos,
    overlay_lotes_ativos,
    render_equipe_grid,
    render_guia_secoes,
)
from app.ritmo_colab_ui import render_tabelas_ritmo
from app.formatting import fmt_brl_cell
from app.grid_snapshot import load_grid_snapshot, save_grid_snapshot, snapshot_token
from app.meta_proporcional import aplicar_colunas_proporcionais
from app.plano_metas import (
    ESCOPO_DIANTE,
    ESCOPO_LABEL,
    ESCOPO_MES,
    get_config_ano,
    mes_editavel,
    mes_salvo,
    meta_empresa_mes,
    meta_plano_mes,
    metas_colaboradores_mes,
    plano_token,
    save_mes,
)
from app.plano_ui import mi, pct_br
from app.premissas import premissas_file_token, save_premissas_lote
_CSS = """
<style>
.metas-previa{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:.4rem 0 .7rem}
.metas-previa .p{background:#fff;border:1px solid var(--avinor-border);border-radius:12px;padding:11px 14px}
.metas-previa .k{font-size:11px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--avinor-muted)}
.metas-previa .v{font-size:20px;font-weight:700;color:var(--avinor-fg);margin-top:4px}
.metas-previa .s{font-size:12px;color:var(--avinor-muted);margin-top:2px}
.metas-previa .s b.up{color:#a16207}.metas-previa .s b.down{color:#15803d}
.metas-previa .p.status.ok{border-color:#bbd7c6;background:#f2f8f4}
.metas-previa .p.status.pend{border-color:#f0d58a;background:#fffaeb}
.metas-previa .p.status.lock{background:#f3f5f4}
.metas-legenda{display:flex;flex-wrap:wrap;gap:14px;font-size:12px;color:var(--avinor-muted);margin:.1rem 0 .45rem}
.metas-legenda i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:5px;vertical-align:-1px}
.metas-guia-nota{font-size:12px;color:var(--avinor-muted);margin:.15rem 0 .35rem}
[class*="st-key-equipe_aggrid"] [data-stale="true"],
[class*="st-key-equipe_aggrid"] [data-stale="true"] iframe,
[class*="st-key-grid_state"] [data-stale="true"],
[class*="st-key-grid_state"] iframe,
div[data-testid="stElementContainer"][data-stale="true"]:has(iframe) {
  opacity: 1 !important;
  pointer-events: auto !important;
  filter: none !important;
}
@media (max-width:1000px){.metas-previa{grid-template-columns:1fr}}
</style>
"""

_HELP_ESCOPO = (
    "Exemplo: em junho a meta automática do IRAN dá R$ 1,0 mi e você coloca R$ 1,2 mi (+20%).\n\n"
    "**Deste mês em diante:** o sistema guarda os +20% e repete nos próximos meses, em cima "
    "da automática de cada mês. Julho automático 0,9 mi vira 1,08 mi; dezembro 1,3 mi vira "
    "1,56 mi. Use quando você acha que ele rende mais do que o histórico mostra.\n\n"
    "**Só este mês:** junho fica com R$ 1,2 mi e de julho em diante ele volta para o automático. "
    "Use para uma exceção pontual (campanha, cliente grande no mês).\n\n"
    "Guardar em % (e não o valor fixo) mantém a meta dele subindo e descendo com a sazonalidade."
)


def _md(s: str) -> str:
    return s.replace("$", "\\$")


def _escopo_key(ano: int, mes: int) -> str:
    return f"escopos_{ano}_{mes}"


def _prefill_herdados(rows: list[dict], ano: int, mes: int) -> list[dict]:
    """Quem tem ajuste "deste mês em diante" de um mês anterior já entra com a meta ajustada."""
    metas = metas_colaboradores_mes(ano, mes)
    out = []
    for row in rows:
        r = dict(row)
        mc = metas.get(int(r["vendedor"]))
        if mc and mc.origem == "herdado" and float(r.get("meta_manual") or 0) <= 0:
            r["meta_manual"] = round(mc.final, 0)
        out.append(r)
    return out


def _inseridos(rows: list[dict]) -> list[dict]:
    itens = []
    for r in rows:
        auto = float(r.get("meta_prop_mes_rs") or 0)
        man = float(r.get("meta_manual") or 0)
        if man <= 0 or abs(man - auto) < 1:
            continue
        itens.append(
            {
                "vid": int(r["vendedor"]),
                "nome": str(r["nome"]),
                "auto": auto,
                "manual": man,
                "pct": (man / auto - 1) * 100 if auto > 0 else None,
                "origem": r.get("ajuste_origem"),
                "mes_origem": r.get("ajuste_mes_origem"),
            }
        )
    return itens


@st.dialog("Estruturar inserções", width="large")
def _dialog_insercoes(ano: int, mes: int, itens: list[dict]) -> None:
    key = _escopo_key(ano, mes)
    atual = dict(st.session_state.get(key, {}))
    st.markdown(
        f"Metas que você mudou à mão em **{label_mes(ano, mes)}**. "
        "Escolha até quando cada ajuste vale.",
        help=_HELP_ESCOPO,
    )
    escolhas: dict[int, str] = {}
    for it in itens:
        with st.container(border=True):
            c1, c2 = st.columns([1.5, 1.2], vertical_alignment="center")
            with c1:
                pct = f" ({pct_br(it['pct'], 1, True)})" if it["pct"] is not None else ""
                origem = ""
                if it["origem"] == "herdado" and it["mes_origem"]:
                    origem = f"  \n:gray[Ajuste que veio de {MESES_NOME[int(it['mes_origem'])]}]"
                st.markdown(
                    _md(
                        f"**{it['nome']}**  \n"
                        f"{fmt_brl_cell(it['auto'])} → **{fmt_brl_cell(it['manual'])}**{pct}"
                    )
                    + origem
                )
            with c2:
                if it["pct"] is None:
                    st.caption("Sem meta automática: vale só para este mês.")
                    escolhas[it["vid"]] = ESCOPO_MES
                    continue
                v = st.segmented_control(
                    "Vale para",
                    [ESCOPO_DIANTE, ESCOPO_MES],
                    format_func=ESCOPO_LABEL.get,
                    default=atual.get(it["vid"], ESCOPO_DIANTE),
                    key=f"dlg_esc_{ano}_{mes}_{it['vid']}",
                    label_visibility="collapsed",
                )
                escolhas[it["vid"]] = v or ESCOPO_DIANTE
    st.caption("A escolha vale quando você clicar em **Salvar meta do mês**.")
    if st.button("Confirmar", type="primary", use_container_width=True):
        st.session_state[key] = escolhas
        st.rerun()


def _salvar_mes(ano: int, mes: int, rows_live: list[dict]) -> int:
    save_premissas_lote(
        ano, mes, {int(r["vendedor"]): premissa_from_row(r) for r in rows_live}
    )
    save_grid_snapshot(ano, mes, rows_live)
    escopos = st.session_state.get(_escopo_key(ano, mes), {})
    colab: dict[int, tuple[float, float]] = {}
    ajustes: dict[int, tuple[float, str]] = {}
    for r in rows_live:
        vid = int(r["vendedor"])
        auto = float(r.get("meta_prop_mes_rs") or 0)
        man = float(r.get("meta_manual") or 0)
        final = meta_final_row(r)
        colab[vid] = (auto, final if final > 0 else auto)
        if auto > 0 and man > 0 and abs(man - auto) >= 1:
            ajustes[vid] = (man / auto - 1.0, escopos.get(vid, ESCOPO_DIANTE))
    save_mes(ano, mes, colab, ajustes)
    return len(rows_live)


def _render_previa(
    slot,
    ano: int,
    mes: int,
    rows_live: list[dict],
    editavel: bool,
) -> None:
    auto = sum(float(r.get("meta_prop_mes_rs") or 0) for r in rows_live)
    final = sum(meta_final_row(r) for r in rows_live)
    meta_anual, _ = get_config_ano(ano)
    outros = sum(meta_empresa_mes(ano, m) for m in range(1, 13) if m != mes)
    ano_total = outros + final

    salvo = mes_salvo(ano, mes)
    dif_mes = final - auto
    s_mes = f"cota do plano {mi(auto)}"
    if abs(dif_mes) >= 1_000:
        cls = "up" if dif_mes > 0 else "down"
        s_mes += (
            f' · <b class="{cls}">{"+" if dif_mes > 0 else "−"}{mi(abs(dif_mes))}</b> '
            "vs a cota (quanto entrega / manuais)"
        )
    dif_ano = ano_total - meta_anual
    s_ano = f"plano {mi(meta_anual)}"
    if meta_anual > 0 and abs(dif_ano) >= 1_000:
        cls = "up" if dif_ano > 0 else "down"
        s_ano += f' · <b class="{cls}">{"+" if dif_ano > 0 else "−"}{mi(abs(dif_ano))}</b> nos ajustes'

    if not editavel:
        st_cls, st_k, st_v, st_s = (
            "lock",
            "Mês fechado",
            "Só consulta",
            "Metas automáticas, calculadas com o histórico da época."
            if not salvo
            else "Mostrando o que foi salvo para o mês.",
        )
    elif salvo:
        saved_final = sum(v[1] for v in (salvo.get("c") or {}).values())
        quando = datetime.fromtimestamp(int(salvo.get("t", 0))).strftime("%d/%m %H:%M")
        if abs(saved_final - final) >= 1:
            st_cls, st_k, st_v, st_s = (
                "pend",
                "Alterações não salvas",
                f"Salvo: {mi(saved_final)}",
                f"Salvo em {quando}. Clique em Salvar para valer no painel.",
            )
        else:
            st_cls, st_k, st_v, st_s = ("ok", "Mês salvo", quando, "É o que vale no painel.")
    else:
        st_cls, st_k, st_v, st_s = (
            "pend",
            "Ainda não salvo",
            "Valores calculados",
            "O painel usa a cota do plano até você salvar. A meta do mês já mostra o quanto cada um entrega.",
        )

    slot.markdown(
        f"""<div class="metas-previa">
<div class="p"><div class="k">Meta de {html.escape(MESES_NOME[mes])}</div><div class="v">{mi(final)}</div><div class="s">{s_mes}</div></div>
<div class="p"><div class="k">Meta do ano {ano}</div><div class="v">{mi(ano_total)}</div><div class="s">{s_ano}</div></div>
<div class="p status {st_cls}"><div class="k">{html.escape(st_k)}</div><div class="v">{html.escape(st_v)}</div><div class="s">{html.escape(st_s)}</div></div>
</div>""",
        unsafe_allow_html=True,
    )


@st.fragment
def render_metas_equipe_tabela(ano: int, mes: int, taxa: float) -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
    editavel = mes_editavel(ano, mes)
    msg = st.session_state.pop("metas_toast", None)
    if msg:
        st.toast(msg, icon=":material/check_circle:")

    df = load_grid_metas_colaboradores(ano, mes, taxa)
    if df.empty:
        st.info("Sem colaboradores com venda no mês ou nos 3 meses anteriores para montar a tabela.")
        return

    state_key = f"grid_state_{ano}_{mes}"
    ver_key = f"{state_key}_ver"
    force_erp_key = f"grid_force_erp_{ano}_{mes}"
    agdf_key = f"{state_key}_agdf"
    grid_schema = (
        f"{ano}_{mes:02d}_snap_{snapshot_token(ano, mes)}"
        f"_prem_{premissas_file_token()}_plano_{plano_token()}"
    )

    if st.session_state.pop(force_erp_key, False):
        st.session_state[state_key] = _prefill_herdados(
            loader_rows_to_state(df, ano, mes, taxa), ano, mes
        )
        st.session_state[ver_key] = grid_schema
        st.session_state.pop(agdf_key, None)
    elif st.session_state.get(ver_key) != grid_schema or state_key not in st.session_state:
        snap = load_grid_snapshot(ano, mes)
        if snap:
            base = [recalc_row_formulas_only(dict(x), taxa) for x in snap]
        else:
            base = _prefill_herdados(loader_rows_to_state(df, ano, mes, taxa), ano, mes)
        st.session_state[state_key] = base
        st.session_state[ver_key] = grid_schema
        st.session_state.pop(agdf_key, None)

    rows: list[dict] = [
        recalc_row_formulas_only(dict(x), taxa) for x in st.session_state[state_key]
    ]
    rows = aplicar_colunas_proporcionais(rows, ano, mes)
    st.session_state[state_key] = rows

    agdf_prev = st.session_state.get(agdf_key)
    skip_lote = lote_keys_ativos(state_key)
    rows_prev = (
        rows_from_aggrid_df(rows, agdf_prev, taxa, skip_lote)
        if agdf_prev is not None
        else rows
    )
    if skip_lote:
        rows_prev = overlay_lotes_ativos(rows_prev, state_key, taxa)
    itens = _inseridos(rows_prev) if editavel else []

    salvar = False
    a1, a2, a_limpar, a3, a4 = st.columns([1.3, 1.1, 1, 1, 1.25], vertical_alignment="center")
    with a_limpar:
        tem_azul = any(_f_num(r, k) > 0 for r in rows_prev for k in EDITABLE_KEYS) or any(
            _f_num(r, f"peso_sem_man_{i}") > 0 for r in rows_prev for i in range(1, 6)
        )
        if editavel and st.button(
            "Limpar inserções",
            key=f"limpar_{ano}_{mes}",
            icon=":material/ink_eraser:",
            disabled=not tem_azul,
            help="Esvazia as colunas azuis da tabela principal e os pesos manuais da semana. "
            "As contas passam a usar as sugestões. Nada é gravado até Salvar.",
            use_container_width=True,
        ):
            nonce_key = f"{state_key}_nonce"
            st.session_state[state_key] = limpar_insercoes(rows_prev, taxa)
            st.session_state[nonce_key] = int(st.session_state.get(nonce_key, 0)) + 1
            st.session_state.pop(agdf_key, None)
            st.session_state.pop(f"{state_key}_semdf", None)
            st.session_state.pop(_escopo_key(ano, mes), None)
            st.session_state["metas_toast"] = (
                "Colunas azuis limpas: valem as sugestões. Clique em Salvar para gravar."
            )
            st.rerun(scope="fragment")
    with a1:
        if editavel:
            st.caption(
                "Edite as colunas azuis; vazio = vale a sugestão. "
                "A prévia muda na hora; o painel só muda ao salvar."
            )
        else:
            st.caption("Mês fechado: metas automáticas, sem edição.")
    with a2:
        if editavel and st.button(
            f"Estruturar inserções ({len(itens)})",
            key=f"estruturar_{ano}_{mes}",
            icon=":material/tune:",
            disabled=not itens,
            help="Lista quem você editou à mão e define se o ajuste vale só neste mês "
            "ou deste mês em diante.",
            use_container_width=True,
        ):
            _dialog_insercoes(ano, mes, itens)
    with a3:
        if st.button(
            "Recarregar do ERP",
            key=f"reload_erp_{ano}_{mes}",
            icon=":material/refresh:",
            help="Refaz as consultas do histórico. Edições não salvas são descartadas.",
            use_container_width=True,
        ):
            st.session_state[force_erp_key] = True
            st.session_state.pop(f"{state_key}_semdf", None)
            st.rerun(scope="fragment")
    with a4:
        if editavel:
            salvar = st.button(
                f"Salvar meta de {MESES_NOME[mes]}",
                type="primary",
                key=f"save_grid_{ano}_{mes}",
                icon=":material/save:",
                use_container_width=True,
            )

    previa_slot = st.empty()
    if "equipe_grid_tips" not in st.session_state:
        st.session_state.equipe_grid_tips = True
    leg_l, leg_r = st.columns([5.4, 1.2], vertical_alignment="center")
    with leg_l:
        extra = (
            "<span>Passe o mouse na célula ou no <b>?</b> do título para ver a conta.</span>"
            if st.session_state.equipe_grid_tips
            else ""
        )
        st.markdown(
            '<div class="metas-legenda">'
            '<span><i style="background:#eef4fb;border:1px solid #93c5fd"></i>média 3 meses</span>'
            '<span><i style="background:#fbefc9;border:1px solid #d4a017"></i>'
            '<b style="color:#9a6b00;font-style:italic">alavancas / quanto entrega</b></span>'
            '<span><i style="background:#e8f0fe;border:1px solid #93c5fd"></i>manual (vazio = quanto entrega)</span>'
            '<span><i style="background:#dcfce7;border:1px solid #22c55e"></i>calculado</span>'
            '<span><i style="background:#fef9c3;border:1px solid #facc15"></i>cota do plano</span>'
            '<span><i style="background:#e6f2ea;border:1px solid #3d6b5c"></i>meta que vale</span>'
            f"{extra}</div>",
            unsafe_allow_html=True,
        )
    with leg_r:
        st.toggle(
            "Explicações",
            key="equipe_grid_tips",
            help="Liga ou desliga as contas ao passar o mouse nas células e o ? nos títulos desta tabela.",
        )

    ctx = {
        "mes": label_mes(ano, mes),
        "base": round(meta_plano_mes(ano, mes), 0),
        "uteis": business_days_in_month(ano, mes),
    }
    rows = rows_prev
    st.markdown(
        '<p class="metas-guia-nota">'
        "<b>Cota do plano</b> = fatia dele no anual deste mês. "
        "<b>Quanto entrega</b> = conta do histórico/alavancas (pode ser menos ou mais que a cota). "
        "<b>Meta do mês</b> = o manual, se houver; senão o quanto ele entrega. "
        "Os botões dentro da tabela levam ao bloco; o número embaixo aplica o azul em todos."
        "</p>",
        unsafe_allow_html=True,
    )
    rows = render_guia_secoes(rows, taxa, state_key, locked=not editavel)
    render_equipe_grid(
        rows,
        ano,
        mes,
        taxa,
        state_key,
        locked=not editavel,
        ctx=ctx,
        tips=bool(st.session_state.equipe_grid_tips),
    )

    agdf = st.session_state.get(agdf_key)
    skip_lote = lote_keys_ativos(state_key)
    rows_live = (
        rows_from_aggrid_df(rows, agdf, taxa, skip_lote)
        if agdf is not None
        else rows
    )
    if skip_lote:
        rows_live = overlay_lotes_ativos(rows_live, state_key, taxa)
    _render_previa(previa_slot, ano, mes, rows_live, editavel)

    st.markdown("---")
    st.markdown("#### Ritmo do colaborador · semana e dia")
    meta_antes = tuple(round(meta_final_row(r), 0) for r in rows_live)
    rows_live = render_tabelas_ritmo(
        rows_live, ano, mes, state_key, locked=not editavel
    )
    rows_live = [recalc_row_formulas_only(r, taxa) for r in rows_live]
    rows_live = aplicar_colunas_proporcionais(rows_live, ano, mes)
    st.session_state[state_key] = rows_live
    meta_depois = tuple(round(meta_final_row(r), 0) for r in rows_live)
    if meta_antes != meta_depois:
        st.session_state[f"{state_key}_nonce"] = int(
            st.session_state.get(f"{state_key}_nonce", 0)
        ) + 1
        st.rerun(scope="fragment")

    if salvar:
        if agdf is None:
            st.error("Tabela ainda não carregou. Aguarde um instante e tente de novo.")
            return
        n = _salvar_mes(ano, mes, rows_live)
        load_grid_metas_colaboradores.clear()
        load_panorama_metas_equipe.clear()
        st.session_state.pop(_escopo_key(ano, mes), None)
        st.session_state["metas_toast"] = (
            f"Meta de {MESES_NOME[mes]} salva para {n} colaborador(es)."
        )
        st.rerun(scope="app")

