"""Tabelas de ritmo semanal e diário por colaborador (Início)."""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from app.dates_util import semanas_mes
from app.ritmo_colab import (
    MAX_SEM,
    aplicar_ritmo_sugerido,
    patch_pesos_from_aggrid,
    pesos_aplicados,
    rows_to_dia_df,
    rows_to_semana_df,
    semana_labels,
    sincronizar_meta_pelo_ritmo,
    total_ritmo_row,
)

_CSS = {
    ".ag-root-wrapper": {
        "border-radius": "10px",
        "border": "1px solid #e5e7eb !important",
    },
    ".ag-header-cell-label": {
        "justify-content": "flex-start",
        "font-size": "11px",
        "line-height": "1.3",
        "white-space": "normal",
        "padding": "6px 8px",
    },
    ".ag-cell": {"font-size": "13px", "padding-left": "10px", "padding-right": "10px"},
    ".ag-overlay-loading-wrapper": {"display": "none !important"},
    ".ag-pinned-right-header, .ag-pinned-right-cols-container": {
        "box-shadow": "-6px 0 10px rgba(15, 23, 42, 0.08)",
        "background": "#e6f2ea",
    },
    ".ag-header-cell[col-id='meta_mes'], .ag-cell[col-id='meta_mes']": {
        "border-left": "3px solid #3d6b5c !important",
    },
    ".ag-floating-bottom": {
        "borderTop": "2px solid #8b7355 !important",
        "background": "#d9cbb8 !important",
    },
    ".ag-floating-bottom .ag-row": {
        "background": "#d9cbb8 !important",
        "opacity": "1 !important",
    },
    ".ag-floating-bottom .ag-cell": {
        "background-color": "#d9cbb8 !important",
        "color": "#111827 !important",
        "font-weight": "800 !important",
        "font-style": "normal !important",
        "opacity": "1 !important",
    },
    ".ag-body-horizontal-scroll": {
        "display": "flex !important",
        "visibility": "visible !important",
        "opacity": "1 !important",
        "height": "18px !important",
        "min-height": "18px !important",
        "max-height": "18px !important",
        "background": "#e5e7eb !important",
    },
    ".ag-body-horizontal-scroll-viewport": {
        "overflow-x": "scroll !important",
        "height": "18px !important",
    },
    ".ag-body-horizontal-scroll-container": {
        "min-height": "18px !important",
    },
}
_BLUE = {"backgroundColor": "#e8f0fe", "color": "#1a365d", "fontWeight": "500"}
_GOLD = {"backgroundColor": "#fbefc9", "color": "#7a5300", "fontWeight": "700"}
_HIST = {"backgroundColor": "#eef4fb", "color": "#1e3a5f"}
_CALC = {"backgroundColor": "#dcfce7", "color": "#14532d", "fontWeight": "700"}
_RO = {"backgroundColor": "#ffffff", "color": "#1f2937"}
_FINAL = {
    "backgroundColor": "#e6f2ea",
    "color": "#14532d",
    "fontWeight": "700",
}
_SEC = ("h1", "h2", "h3", "h4", "h5", "dia1", "dia2", "dia3", "dia4", "dia5")


def _js_sug_pct():
    from st_aggrid.shared import JsCode

    return JsCode(
        """
        function(params) {
            var d = params.data || {};
            var f = params.colDef.field;
            var v = params.value;
            if (v === null || v === undefined || v === '' || Number(v) === 0) {
                if (params.node && params.node.rowPinned) return '—';
                v = d['s' + f.slice(1)];
            }
            if (v === null || v === undefined || v === '' || isNaN(Number(v))) return '—';
            return Number(v).toLocaleString('pt-BR', {minimumFractionDigits: 1, maximumFractionDigits: 1}) + '%';
        }
        """
    )


def _js_sug_style(base: dict):
    from st_aggrid.shared import JsCode

    return JsCode(
        "function(params) {"
        f"var base = {json.dumps(base)};"
        "var v = params.value;"
        "if (params.node && params.node.rowPinned) return {backgroundColor:'#d9cbb8',color:'#111827',fontWeight:'800'};"
        "if (v === null || v === undefined || v === '' || Number(v) === 0) {"
        "  return Object.assign({}, base, {color: '#9a6b00', fontStyle: 'italic', fontWeight: '600'});"
        "}"
        "return base;"
        "}"
    )


def _js_parse():
    from st_aggrid.shared import JsCode

    return JsCode(
        """
        function(params) {
            var v = params.newValue;
            if (v === '' || v === null || v === undefined) return null;
            if (typeof v === 'number') return isNaN(v) ? null : v;
            var s = String(v).replace('%','').replace(',','.').trim();
            var n = Number(s);
            return isNaN(n) ? null : n;
        }
        """
    )


def _js_ready(compensar: bool = True, n_sem: int = 5, guia_items: list | None = None):
    from st_aggrid.shared import JsCode

    def _esc(s: str) -> str:
        return str(s).replace("\\", "\\\\").replace("'", "\\'")

    items = "[" + ",".join(
        "{label:'%s',jump:'%s',title:'%s'}"
        % (_esc(it.get("label", "")), _esc(it.get("jump", "")), _esc(it.get("title") or it.get("label", "")))
        for it in (guia_items or [])
    ) + "]"
    return JsCode(
        """
        function(params) {
            window.__avinorRitmo = {
                compensar: __COMP__,
                nSem: __NSEM__,
                installGuia: function(api, eGridDiv, items) {
                    if (!items || !items.length) return;
                    var el = eGridDiv || document.querySelector('.ag-root-wrapper');
                    if (!el) return;
                    var wrap = el.parentElement;
                    if (!wrap) return;
                    var old = wrap.querySelector('.avinor-guia');
                    if (old) old.remove();
                    var bar = document.createElement('div');
                    bar.className = 'avinor-guia';
                    bar.style.cssText = 'display:flex;gap:6px;flex-wrap:wrap;padding:4px 2px 8px;box-sizing:border-box;';
                    function paint(ativo) {
                        var btns = bar.querySelectorAll('button');
                        for (var i = 0; i < btns.length; i++) {
                            var on = btns[i] === ativo;
                            btns[i].style.background = on ? '#14532d' : '#fff';
                            btns[i].style.color = on ? '#fff' : '#14532d';
                            btns[i].style.borderColor = on ? '#14532d' : '#c5d4cc';
                        }
                    }
                    items.forEach(function(it) {
                        var b = document.createElement('button');
                        b.type = 'button';
                        b.textContent = it.label;
                        b.title = it.title || it.label;
                        b.style.cssText = 'cursor:pointer;border:1px solid #c5d4cc;background:#fff;color:#14532d;border-radius:8px;padding:6px 10px;font-size:12px;font-weight:650;line-height:1.2;font-family:inherit;';
                        b.onclick = function(ev) {
                            ev.preventDefault();
                            ev.stopPropagation();
                            try { api.ensureColumnVisible(it.jump, 'start'); } catch (err) {}
                            paint(b);
                        };
                        bar.appendChild(b);
                    });
                    wrap.insertBefore(bar, el);
                    wrap.style.display = 'flex';
                    wrap.style.flexDirection = 'column';
                    wrap.style.height = '100%';
                    wrap.style.overflow = 'hidden';
                    bar.style.flex = '0 0 auto';
                    el.style.flex = '1 1 auto';
                    el.style.minHeight = '0';
                    el.style.height = 'auto';
                    el.style.maxHeight = 'none';
                    if (bar.firstChild) paint(bar.firstChild);
                },
                n: function(v) { var x = Number(v); return isNaN(x) ? 0 : x; },
                set: function(v) { return v !== null && v !== undefined && v !== ''; },
                ef: function(d, i) {
                    var m = d['m' + i];
                    return this.set(m) && this.n(m) > 0 ? this.n(m) : this.n(d['s' + i]);
                },
                pesos: function(d) {
                    var n = this.nSem || 5;
                    var locked = [], efs = [];
                    for (var i = 1; i <= n; i++) {
                        var m = d['m' + i];
                        var lk = this.set(m) && this.n(m) > 0;
                        locked.push(lk);
                        efs.push(lk ? this.n(m) : this.n(d['s' + i]));
                    }
                    if (!this.compensar) {
                        var anyL = locked.some(Boolean);
                        if (!anyL) {
                            var hab = [];
                            for (var h = 1; h <= n; h++) hab.push(this.n(d['p' + h]));
                            return hab;
                        }
                        return efs;
                    }
                    if (!locked.some(Boolean)) {
                        var t = efs.reduce(function(a,b){return a+b;},0) || 1;
                        return efs.map(function(x){ return x / t * 100; });
                    }
                    var lockSum = 0, freeSum = 0;
                    for (var j = 0; j < n; j++) {
                        if (locked[j]) lockSum += efs[j];
                        else freeSum += efs[j];
                    }
                    var rest = 100 - lockSum;
                    return efs.map(function(e, idx) {
                        if (locked[idx]) return e;
                        if (freeSum > 0 && rest > 0) return e / freeSum * rest;
                        return 0;
                    });
                },
                refresh: function(api) {
                    if (!api) return;
                    api.refreshCells({ force: true, columns: ['v1','v2','v3','v4','v5','soma'] });
                }
            };
            window.__avinorRitmo.refresh(params.api);
            window.__avinorRitmo.installGuia(params.api, params.eGridDiv, __ITEMS__);
            setTimeout(function() {
                window.__avinorRitmo.installGuia(params.api, params.eGridDiv, __ITEMS__);
            }, 50);
        }
        """.replace("__COMP__", "true" if compensar else "false")
        .replace("__NSEM__", str(int(n_sem)))
        .replace("__ITEMS__", items)
    )


def _js_after():
    from st_aggrid.shared import JsCode

    return JsCode(
        """
        function(params) {
            var g = window.__avinorRitmo;
            if (g && g.refresh) g.refresh(params.api);
        }
        """
    )


def _js_meta_w(i: int):
    from st_aggrid.shared import JsCode

    return JsCode(
        f"""
        function(params) {{
            if (params.node && params.node.rowPinned) return params.data ? params.data.v{i} : null;
            var d = params.data; if (!d) return null;
            var g = window.__avinorRitmo;
            if (!g) return d.v{i};
            var p = g.pesos ? g.pesos(d)[{i} - 1] : g.ef(d, {i});
            var meta = g.n(d.meta_mes);
            if (meta <= 0 || p <= 0) return null;
            return Math.round(meta * p / 100);
        }}
        """
    )


def _js_soma():
    from st_aggrid.shared import JsCode

    return JsCode(
        """
        function(params) {
            if (params.node && params.node.rowPinned) return params.data ? params.data.soma : null;
            var d = params.data; if (!d) return null;
            var g = window.__avinorRitmo;
            if (!g) return d.soma;
            var ps = g.pesos ? g.pesos(d) : null;
            if (ps) {
                var t = 0;
                for (var i = 0; i < ps.length; i++) t += ps[i];
                return Math.round(t * 10) / 10;
            }
            var t2 = 0;
            for (var j = 1; j <= 5; j++) t2 += g.ef(d, j);
            return Math.round(t2 * 10) / 10;
        }
        """
    )


def _fmt_brl():
    from st_aggrid.shared import JsCode

    return JsCode(
        """
        function(params) {
            if (params.value === null || params.value === undefined || params.value === '') return '—';
            var v = Number(params.value);
            if (isNaN(v)) return '—';
            return 'R$ ' + Math.round(v).toLocaleString('pt-BR');
        }
        """
    )


def _fmt_pct():
    from st_aggrid.shared import JsCode

    return JsCode(
        """
        function(params) {
            if (params.value === null || params.value === undefined || params.value === '') return '—';
            var v = Number(params.value);
            if (isNaN(v)) return '—';
            return v.toLocaleString('pt-BR', {minimumFractionDigits: 1, maximumFractionDigits: 1}) + '%';
        }
        """
    )


def _try_grid(
    df: pd.DataFrame,
    height: int,
    key: str,
    build_cols,
    locked: bool,
    compensar: bool = True,
    n_sem: int = 5,
    guia_items: list | None = None,
) -> pd.DataFrame | None:
    try:
        from st_aggrid import AgGrid, DataReturnMode, GridOptionsBuilder, GridUpdateMode
    except ImportError:
        return None
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(
        resizable=True,
        sortable=False,
        filter=False,
        wrapHeaderText=True,
        autoHeaderHeight=True,
        minWidth=72,
        suppressSizeToFit=True,
    )
    build_cols(gb, locked)
    from st_aggrid.shared import JsCode as _Js

    tot = total_ritmo_row(df)
    row_style = _Js(
        """
        function(params) {
            if (params.node && params.node.rowPinned === 'bottom') {
                return { fontWeight: '800', backgroundColor: '#d9cbb8', color: '#111827' };
            }
        }
        """
    )
    gb.configure_grid_options(
        headerHeight=56,
        rowHeight=34,
        singleClickEdit=True,
        stopEditingWhenCellsLoseFocus=True,
        enterNavigatesVertically=True,
        enterNavigatesVerticallyAfterEdit=True,
        suppressLoadingOverlay=True,
        animateRows=False,
        tooltipShowDelay=400,
        suppressColumnVirtualisation=True,
        alwaysShowHorizontalScroll=True,
        alwaysShowVerticalScroll=True,
        scrollbarShowAlways=True,
        suppressHorizontalScroll=False,
        onGridReady=_js_ready(compensar, n_sem, guia_items),
        onCellValueChanged=_js_after(),
        onCellEditingStopped=_js_after(),
        pinnedBottomRowData=[tot],
        getRowStyle=row_style,
    )
    css = dict(_CSS)
    for col in _SEC:
        css[f".ag-header-cell[col-id='{col}'], .ag-cell[col-id='{col}']"] = {
            "border-left": "3px solid #171717 !important"
        }
    grid = AgGrid(
        df,
        gridOptions=gb.build(),
        height=height,
        width="100%",
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        update_mode=GridUpdateMode.VALUE_CHANGED,
        update_on=[("cellValueChanged", 400)],
        allow_unsafe_jscode=True,
        theme="streamlit",
        key=key,
        fit_columns_on_grid_load=False,
        custom_css=css,
        server_sync_strategy="client_wins",
    )
    return pd.DataFrame(grid["data"])


def _build_semana(gb, locked: bool, n: int, labs: list[str]) -> None:
    fmt_brl, fmt_pct, fmt_sug, parse = _fmt_brl(), _fmt_pct(), _js_sug_pct(), _js_parse()
    sug_st = _js_sug_style(_BLUE)
    gb.configure_column("vid", hide=True)
    gb.configure_column("origem", hide=True)
    gb.configure_column("info", hide=True)
    gb.configure_column(
        "colab",
        headerName="Colaborador",
        pinned="left",
        width=200,
        minWidth=180,
        editable=False,
        suppressSizeToFit=True,
    )
    gb.configure_column(
        "meta_mes",
        headerName="Meta do mês",
        width=124,
        minWidth=118,
        editable=False,
        pinned="right",
        lockPinned=True,
        cellStyle=_FINAL,
        valueFormatter=fmt_brl,
        type=["numericColumn"],
        suppressSizeToFit=True,
        headerTooltip="Meta do mês que vale. Com o compensador desligado, muda se você alterar a semana.",
    )
    for i in range(1, MAX_SEM + 1):
        hide = i > n
        lab = labs[i - 1] if i <= n else f"S{i}"
        gb.configure_column(
            f"h{i}",
            headerName=f"{lab} média",
            width=118,
            minWidth=110,
            hide=hide,
            editable=False,
            cellStyle=_HIST,
            valueFormatter=fmt_brl,
            type=["numericColumn"],
            headerTooltip="Média de faturamento nessa semana-do-mês nos 3 meses fechados.",
            suppressSizeToFit=True,
        )
        gb.configure_column(
            f"p{i}",
            headerName=f"{lab} hab.",
            width=96,
            minWidth=88,
            hide=hide,
            editable=False,
            cellStyle=_HIST,
            valueFormatter=fmt_pct,
            type=["numericColumn"],
            headerTooltip="Fatia habitual dessa semana no mês (histórico 3m; senão dias úteis).",
            suppressSizeToFit=True,
        )
        gb.configure_column(
            f"s{i}",
            headerName=f"{lab} evo.",
            width=100,
            minWidth=92,
            hide=hide,
            editable=False,
            cellStyle=_GOLD,
            valueFormatter=fmt_pct,
            type=["numericColumn"],
            headerTooltip="Evolução atingível: peso habitual × 1,05. Vale quando o manual está vazio.",
            suppressSizeToFit=True,
        )
        gb.configure_column(
            f"m{i}",
            headerName=f"{lab} man.",
            width=108,
            minWidth=100,
            hide=hide,
            editable=not locked,
            cellStyle=sug_st if not locked else _BLUE,
            valueFormatter=fmt_sug,
            valueParser=parse,
            type=["numericColumn"],
            headerTooltip="Você concorda com a evolução ou põe outro %. Vazio = vale o dourado.",
            suppressSizeToFit=True,
        )
        gb.configure_column(
            f"v{i}",
            headerName=f"{lab} meta",
            width=118,
            minWidth=110,
            hide=hide,
            editable=False,
            cellStyle=_CALC,
            valueFormatter=fmt_brl,
            valueGetter=_js_meta_w(i),
            type=["numericColumn"],
            headerTooltip="Meta do mês × peso que vale.",
            suppressSizeToFit=True,
        )
    gb.configure_column(
        "soma",
        headerName="Soma pesos",
        width=100,
        minWidth=92,
        editable=False,
        pinned="right",
        lockPinned=True,
        cellStyle=_CALC,
        valueFormatter=fmt_pct,
        valueGetter=_js_soma(),
        type=["numericColumn"],
        headerTooltip="Soma dos pesos que valem. O ideal é 100%.",
        suppressSizeToFit=True,
    )


def _build_dia(gb, locked: bool, n: int, labs: list[str]) -> None:
    del locked
    fmt_brl = _fmt_brl()
    gb.configure_column("vid", hide=True)
    gb.configure_column(
        "colab",
        headerName="Colaborador",
        pinned="left",
        width=200,
        minWidth=180,
        editable=False,
        suppressSizeToFit=True,
    )
    gb.configure_column(
        "meta_mes",
        headerName="Meta do mês",
        width=124,
        minWidth=118,
        editable=False,
        pinned="right",
        lockPinned=True,
        cellStyle=_FINAL,
        valueFormatter=fmt_brl,
        type=["numericColumn"],
        suppressSizeToFit=True,
        headerTooltip="Meta do mês que vale. Acompanhe aqui se o ritmo da semana alterar o mês.",
    )
    for i in range(1, MAX_SEM + 1):
        hide = i > n
        lab = labs[i - 1] if i <= n else f"S{i}"
        gb.configure_column(
            f"du{i}",
            headerName=f"{lab} du",
            width=88,
            minWidth=80,
            hide=hide,
            editable=False,
            cellStyle=_HIST,
            type=["numericColumn"],
            headerTooltip="Dias úteis (seg–sex) desta semana no mês.",
            suppressSizeToFit=True,
        )
        gb.configure_column(
            f"ms{i}",
            headerName=f"{lab} meta sem.",
            width=118,
            minWidth=110,
            hide=hide,
            editable=False,
            cellStyle=_GOLD,
            valueFormatter=fmt_brl,
            type=["numericColumn"],
            headerTooltip="Espelho da tabela semanal: meta do mês × peso que vale.",
            suppressSizeToFit=True,
        )
        gb.configure_column(
            f"dia{i}",
            headerName=f"{lab} R$/du",
            width=118,
            minWidth=110,
            hide=hide,
            editable=False,
            cellStyle=_CALC,
            valueFormatter=fmt_brl,
            type=["numericColumn"],
            headerTooltip="Meta da semana ÷ dias úteis da semana.",
            suppressSizeToFit=True,
        )


def render_tabelas_ritmo(
    rows: list[dict],
    ano: int,
    mes: int,
    state_key: str,
    locked: bool,
) -> list[dict]:
    """Devolve as linhas com pesos manuais da grade semanal (dia só espelha)."""
    rows = aplicar_ritmo_sugerido(rows, ano, mes)
    n = len(semanas_mes(ano, mes))
    labs = semana_labels(ano, mes)
    nonce = int(st.session_state.get(f"{state_key}_nonce", 0))
    comp_key = f"{state_key}_compensar"
    if comp_key not in st.session_state:
        st.session_state[comp_key] = True
    c1, c2 = st.columns([1.4, 3.2], vertical_alignment="center")
    with c1:
        compensar = st.toggle(
            "Compensador",
            key=comp_key,
            disabled=locked,
            help=(
                "Ligado: a meta do mês fica parada. Se você sobe o peso de uma semana, "
                "as outras baixam para a soma continuar 100%. "
                "Desligado: a semana extra entra na meta do mês (e no anual, na prévia). "
                "Ex.: +R$ 100 nesta semana → +R$ 100 na meta do mês desse colaborador."
            ),
        )
    with c2:
        st.caption(
            "**Hab.** = fatia que ele costuma fazer nessa semana. "
            "**Evo.** = habitual × 1,05 (dourado). "
            "**Man.** vazio = vale a evolução. "
            "O dia só reparte a meta da semana nos dias úteis."
        )
    guia_sem = [
        {"label": f"S{i + 1}", "jump": f"h{i + 1}", "title": labs[i]} for i in range(n)
    ]
    guia_dia = [
        {"label": f"S{i + 1}", "jump": f"du{i + 1}", "title": labs[i]} for i in range(n)
    ]
    st.markdown("##### Distribuição por semana")
    sdf = rows_to_semana_df(rows, ano, mes, compensar)
    sem_key = f"{state_key}_sem{nonce or ''}_pin"
    ag = _try_grid(
        sdf,
        460,
        sem_key,
        lambda gb, lk: _build_semana(gb, lk, n, labs),
        locked,
        compensar=compensar,
        n_sem=n,
        guia_items=guia_sem,
    )
    if ag is not None:
        st.session_state[f"{state_key}_semdf"] = ag
        rows = patch_pesos_from_aggrid(rows, ag)
        rows = sincronizar_meta_pelo_ritmo(rows, n, compensar)
        apl_fora = [
            f"{int(r['vendedor']):03d}"
            for r in rows
            if abs(sum(pesos_aplicados(r, n, compensar)) - 100.0) > 1.5
        ]
        if apl_fora and not compensar:
            st.warning(
                "Compensador desligado: a soma dos pesos saiu de 100% "
                f"({', '.join(apl_fora[:12])}"
                + ("…" if len(apl_fora) > 12 else "")
                + "). Isso altera a meta do mês desse colaborador."
            )
    st.markdown("##### Distribuição por dia útil (espelho da semana)")
    ddf = rows_to_dia_df(rows, ano, mes, compensar)
    _try_grid(
        ddf,
        420,
        f"{state_key}_dia{nonce or ''}_pin",
        lambda gb, lk: _build_dia(gb, lk, n, labs),
        True,
        compensar=compensar,
        n_sem=n,
        guia_items=guia_dia,
    )
    return rows
