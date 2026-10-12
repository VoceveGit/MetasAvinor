from __future__ import annotations

import pandas as pd
import streamlit as st

from app.equipe_grid_logic import (
    AGGRID_EDITABLE_FIELDS,
    AGGRID_FIELD_LABELS,
    EDITABLE_LABELS,
    GRID_VIEW_HEIGHT,
    rows_to_aggrid_df,
    rows_to_editor_df,
    total_row_from_aggrid_df,
    total_row_from_editor_df,
)

_EDIT_BLUE = {
    "backgroundColor": "#e8f0fe",
    "color": "#1a365d",
    "fontWeight": "500",
    "borderLeft": "2px solid #93c5fd",
}
_READ_ONLY = {
    "backgroundColor": "#ffffff",
    "color": "#1f2937",
}
_READ_PROP = {
    "backgroundColor": "#fef9c3",
    "color": "#713f12",
    "fontWeight": "500",
    "borderLeft": "2px solid #facc15",
}
AGGRID_PROP_FIELDS = frozenset(
    {"peso_3m", "meta_prop", "meta_prop_sem", "meta_prop_dia", "pos_prop", "cob_prop"}
)
_TOTAL_ROW = {
    "backgroundColor": "#e8e0d4",
    "color": "#1f2937",
    "fontWeight": "700",
}

_CUSTOM_CSS = {
    ".ag-root-wrapper": {
        "border-radius": "10px",
        "border": "1px solid #e5e7eb !important",
        "box-shadow": "0 1px 3px rgba(0,0,0,0.06)",
    },
    ".ag-header-cell-label": {
        "justify-content": "flex-start",
        "font-size": "11px",
        "line-height": "1.3",
        "white-space": "normal",
        "padding": "6px 8px",
    },
    ".ag-cell": {
        "font-size": "13px",
        "line-height": "1.4",
        "padding-left": "10px",
        "padding-right": "10px",
        "border-right": "1px solid #f3f4f6",
    },
    ".ag-row-even": {"backgroundColor": "#fafafa"},
    ".ag-row-odd": {"backgroundColor": "#ffffff"},
    ".ag-row": {"border-bottom": "1px solid #f3f4f6"},
    ".ag-floating-bottom": {"borderTop": "2px solid #c4b5a0 !important"},
}

_MONEY_FIELDS = frozenset(
    {
        "fat_media",
        "ticket_hist",
        "ticket",
        "meta_prop",
        "meta_prop_sem",
        "meta_prop_dia",
        "meta_calc",
        "meta_man",
        "realizado",
    }
)
_PCT_FIELDS = frozenset({"tx_oport", "tx_cob_hist", "conv", "tx_proj", "peso_3m"})
_INT_FIELDS = frozenset(
    {
        "cart",
        "oport",
        "oport_calc",
        "cob_media",
        "cob",
        "dif_cob",
        "pos_media",
        "pos_prop",
        "cob_prop",
    }
)
_DECIMAL_FIELDS = frozenset({"rec_media", "rec"})
_CALC_FIELDS = frozenset({"oport_calc", "cob", "dif_cob", "meta_calc"})

_WIDTHS = {
    "colab": 168,
    "cart": 72,
    "oport": 84,
    "tx_oport": 92,
    "conv": 84,
    "oport_calc": 88,
    "cob_media": 96,
    "tx_proj": 100,
    "cob": 84,
    "dif_cob": 100,
    "tx_cob_hist": 100,
    "fat_media": 108,
    "pos_media": 104,
    "ticket_hist": 104,
    "ticket": 96,
    "rec_media": 104,
    "rec": 92,
    "peso_3m": 96,
    "meta_prop": 112,
    "meta_prop_sem": 108,
    "meta_prop_dia": 116,
    "pos_prop": 108,
    "cob_prop": 108,
    "meta_calc": 112,
    "meta_man": 112,
    "realizado": 112,
}


def _js_grid_ready():
    from st_aggrid.shared import JsCode

    return JsCode(
        """
        function(params) {
            window.__avinorGrid = window.__avinorGrid || {};
            var g = window.__avinorGrid;
            if (!g._ready) {
            g.n = function(v) {
                var x = Number(v);
                return isNaN(x) ? 0 : x;
            };
            g.isSet = function(v) {
                return v !== null && v !== undefined && v !== '';
            };
            g.rowOportCalc = function(d) {
                var cob = g.rowCobVal(d);
                if (cob !== null && g.isSet(d.rec) && g.n(d.rec) > 0) {
                    return Math.round(cob * g.n(d.rec));
                }
                if (!d || !g.isSet(d.conv)) return null;
                var conv = g.n(d.conv);
                if (conv === 0) return 0;
                return Math.round(g.n(d.oport) * conv / 100);
            };
            g.rowCobVal = function(d) {
                if (!d || !g.isSet(d.tx_proj)) return null;
                var txp = g.n(d.tx_proj);
                if (txp === 0) return 0;
                var cart = g.n(d.cart);
                if (cart <= 0) return null;
                return Math.round(cart * txp / 100);
            };
            g.rowDifCob = function(d) {
                if (!d || !g.isSet(d.tx_proj)) return null;
                if (g.n(d.tx_proj) === 0) return 0;
                var cob = g.rowCobVal(d);
                if (cob === null || cob === undefined) return null;
                return Math.max(0, g.n(d.cart) - cob);
            };
            g.rowMetaCalc = function(d) {
                if (!d || !g.isSet(d.tx_proj)) return null;
                if (g.n(d.tx_proj) === 0) return 0;
                var cob = g.rowCobVal(d);
                if (cob === null || cob === undefined) return null;
                if (!g.isSet(d.ticket) || !g.isSet(d.rec)) return null;
                var ticket = g.n(d.ticket);
                var rec = g.n(d.rec);
                if (ticket === 0 || rec === 0) return 0;
                return Math.round(ticket * rec * cob);
            };
            g.refreshPinned = function(api) {
                var bottom = [];
                api.forEachNode(function(node) {
                    if (node.rowPinned === 'bottom') bottom.push(node);
                });
                if (bottom.length) {
                    api.refreshCells({
                        rowNodes: bottom,
                        force: true
                    });
                }
            };
            g.refreshTotals = function(api) {
                if (!api) return;
                var rows = [];
                api.forEachNode(function(node) {
                    if (node.rowPinned) return;
                    if (node.data && node.data.colab !== 'TOTAL') rows.push(node.data);
                });
                if (!rows.length) return;
                function s(f) {
                    var t = 0;
                    for (var i = 0; i < rows.length; i++) t += g.n(rows[i][f]);
                    return t;
                }
                var cart = s('cart');
                var oport = s('oport');
                var ocalc = 0;
                var cobSum = 0;
                var difSum = 0;
                var metaSum = 0;
                var convSum = 0;
                var convN = 0;
                var txpSum = 0;
                var txpN = 0;
                for (var j = 0; j < rows.length; j++) {
                    var rd = rows[j];
                    var oc = g.rowOportCalc(rd);
                    if (oc !== null && oc !== undefined) ocalc += oc;
                    var cb = g.rowCobVal(rd);
                    if (cb !== null && cb !== undefined) cobSum += cb;
                    var df = g.rowDifCob(rd);
                    if (df !== null && df !== undefined) difSum += df;
                    var mc = g.rowMetaCalc(rd);
                    if (mc !== null && mc !== undefined) metaSum += mc;
                    if (g.isSet(rd.conv)) {
                        convSum += g.n(rd.conv);
                        convN += 1;
                    }
                    if (g.isSet(rd.tx_proj)) {
                        txpSum += g.n(rd.tx_proj);
                        txpN += 1;
                    }
                }
                var txO = oport > 0 ? Math.round(ocalc / oport * 10000) / 100 : 0;
                var cobM = s('cob_media');
                var txCob = cart > 0 ? Math.round(cobM / cart * 10000) / 100 : 0;
                var convAvg = convN > 0 ? Math.round(convSum / convN) : null;
                var txpAvg = txpN > 0 ? Math.round(txpSum / txpN) : null;
                api.setPinnedBottomRowData([{
                    colab: 'TOTAL',
                    cart: Math.round(cart),
                    oport: Math.round(oport),
                    tx_oport: txO,
                    conv: convAvg,
                    oport_calc: Math.round(ocalc),
                    cob_media: Math.round(cobM),
                    tx_cob_hist: txCob,
                    tx_proj: txpAvg,
                    cob: Math.round(cobSum),
                    dif_cob: Math.round(difSum),
                    fat_media: Math.round(s('fat_media')),
                    pos_media: Math.round(s('pos_media')),
                    meta_calc: Math.round(metaSum),
                    realizado: Math.round(s('realizado')),
                }]);
                g.refreshPinned(api);
            };
            g._ready = true;
            }
            g.refreshTotals(params.api);
        }
        """
    )


def _js_after_edit():
    from st_aggrid.shared import JsCode

    return JsCode(
        """
        function(params) {
            if (!params.data || params.data.colab === 'TOTAL') return;
            var g = window.__avinorGrid;
            if (!g || !g.refreshTotals) return;
            params.api.refreshCells({
                rowNodes: [params.node],
                columns: ['oport_calc', 'cob', 'dif_cob', 'meta_calc'],
                force: true
            });
            g.refreshTotals(params.api);
        }
        """
    )


def _try_aggrid(df: pd.DataFrame, height: int, grid_key: str) -> pd.DataFrame | None:
    try:
        from st_aggrid import AgGrid, DataReturnMode, GridOptionsBuilder, GridUpdateMode
        from st_aggrid.shared import JsCode
    except ImportError:
        return None

    pinned = [total_row_from_aggrid_df(df)]

    fmt_brl = JsCode(
        """
        function(params) {
            if (params.value === null || params.value === undefined || params.value === '') return '—';
            var v = Number(params.value);
            if (isNaN(v)) return '—';
            return 'R$ ' + Math.round(v).toLocaleString('pt-BR');
        }
        """
    )
    fmt_pct = JsCode(
        """
        function(params) {
            if (params.value === null || params.value === undefined || params.value === '') return '—';
            var v = Number(params.value);
            if (isNaN(v)) return '—';
            var dec = params.colDef.field === 'tx_oport' ? 1 : 0;
            return v.toLocaleString('pt-BR', {minimumFractionDigits: dec, maximumFractionDigits: dec}) + '%';
        }
        """
    )
    fmt_int = JsCode(
        """
        function(params) {
            if (params.value === null || params.value === undefined || params.value === '') return '—';
            var v = Number(params.value);
            if (isNaN(v)) return '—';
            return Math.round(v).toLocaleString('pt-BR');
        }
        """
    )
    fmt_dec = JsCode(
        """
        function(params) {
            if (params.value === null || params.value === undefined || params.value === '') return '—';
            var v = Number(params.value);
            if (isNaN(v)) return '—';
            return v.toLocaleString('pt-BR', {minimumFractionDigits: 1, maximumFractionDigits: 1});
        }
        """
    )
    row_style = JsCode(
        """
        function(params) {
            if (params.node.rowPinned === 'bottom') {
                return { fontWeight: '700', backgroundColor: '#e8e0d4' };
            }
        }
        """
    )
    vg_oport = JsCode(
        """
        function(params) {
            if (params.node && params.node.rowPinned) {
                return params.data ? params.data.oport_calc : null;
            }
            var d = params.data;
            if (!d || d.conv === null || d.conv === undefined || d.conv === '') return null;
            var conv = Number(d.conv);
            if (isNaN(conv)) return null;
            return Math.round(Number(d.oport || 0) * conv / 100);
        }
        """
    )
    vg_cob = JsCode(
        """
        function(params) {
            if (params.node && params.node.rowPinned) {
                return params.data ? params.data.cob : null;
            }
            var d = params.data;
            if (!d || d.tx_proj === null || d.tx_proj === undefined || d.tx_proj === '') return null;
            var txp = Number(d.tx_proj);
            if (isNaN(txp) || txp === 0) return 0;
            var cart = Number(d.cart || 0);
            if (cart <= 0) return null;
            return Math.round(cart * txp / 100);
        }
        """
    )
    vg_dif = JsCode(
        """
        function(params) {
            if (params.node && params.node.rowPinned) {
                return params.data ? params.data.dif_cob : null;
            }
            var d = params.data;
            if (!d || d.tx_proj === null || d.tx_proj === undefined || d.tx_proj === '') return null;
            var txp = Number(d.tx_proj);
            if (isNaN(txp) || txp === 0) return 0;
            var cart = Number(d.cart || 0);
            var cob = Math.round(cart * txp / 100);
            return Math.max(0, cart - cob);
        }
        """
    )
    vg_meta = JsCode(
        """
        function(params) {
            if (params.node && params.node.rowPinned) {
                return params.data ? params.data.meta_calc : null;
            }
            var d = params.data;
            if (!d || d.tx_proj === null || d.tx_proj === undefined || d.tx_proj === '') return null;
            var txp = Number(d.tx_proj);
            if (isNaN(txp) || txp === 0) return 0;
            if (d.ticket === null || d.ticket === undefined || d.ticket === '') return null;
            if (d.rec === null || d.rec === undefined || d.rec === '') return null;
            var ticket = Number(d.ticket);
            var rec = Number(d.rec);
            if (isNaN(ticket) || isNaN(rec) || ticket === 0 || rec === 0) return 0;
            var cart = Number(d.cart || 0);
            var cob = Math.round(cart * txp / 100);
            return Math.round(ticket * rec * cob);
        }
        """
    )

    gb = GridOptionsBuilder.from_dataframe(df)
    for field, label in AGGRID_FIELD_LABELS:
        w = _WIDTHS.get(field, 96)
        editable = field in AGGRID_EDITABLE_FIELDS
        if editable:
            cell_style = _EDIT_BLUE
        elif field in AGGRID_PROP_FIELDS:
            cell_style = _READ_PROP
        else:
            cell_style = _READ_ONLY
        opts = {
            "headerName": label,
            "editable": editable,
            "cellStyle": cell_style,
            "minWidth": w,
            "width": w,
            "wrapHeaderText": True,
            "autoHeaderHeight": True,
            "resizable": True,
            "filter": field == "colab",
            "sortable": field in ("colab", "meta_calc", "realizado"),
        }
        if field == "colab":
            opts["pinned"] = "left"
            opts["lockPinned"] = True
        if field == "oport_calc":
            opts["valueGetter"] = vg_oport
        elif field == "cob":
            opts["valueGetter"] = vg_cob
        elif field == "dif_cob":
            opts["valueGetter"] = vg_dif
        elif field == "meta_calc":
            opts["valueGetter"] = vg_meta
        if editable:
            opts["type"] = ["numericColumn", "numberColumnFilter"]
            opts["valueParser"] = JsCode(
                """
                function(params){
                    if (params.newValue === '' || params.newValue === null) return null;
                    var v = String(params.newValue).replace('%','').replace(',','.').trim();
                    var n = Number(v);
                    return isNaN(n) ? null : n;
                }
                """
            )
            if field in _PCT_FIELDS:
                opts["valueFormatter"] = fmt_pct
            elif field in ("ticket", "meta_man"):
                opts["valueFormatter"] = fmt_brl
            elif field == "rec":
                opts["valueFormatter"] = fmt_dec
            else:
                opts["valueFormatter"] = fmt_int
        elif field in _MONEY_FIELDS:
            opts["valueFormatter"] = fmt_brl
            opts["type"] = ["numericColumn"]
        elif field in _PCT_FIELDS:
            opts["valueFormatter"] = fmt_pct
            opts["type"] = ["numericColumn"]
        elif field in _INT_FIELDS:
            opts["valueFormatter"] = fmt_int
            opts["type"] = ["numericColumn"]
        elif field in _DECIMAL_FIELDS:
            opts["valueFormatter"] = fmt_dec
            opts["type"] = ["numericColumn"]
        elif field in _CALC_FIELDS:
            opts["valueFormatter"] = fmt_int
            opts["type"] = ["numericColumn"]
        gb.configure_column(field, **opts)

    gb.configure_default_column(
        resizable=True,
        sortable=False,
        filter=False,
        wrapHeaderText=True,
        autoHeaderHeight=True,
    )
    on_edit = _js_after_edit()
    on_ready = _js_grid_ready()
    gb.configure_grid_options(
        headerHeight=48,
        rowHeight=36,
        enableRangeSelection=True,
        suppressRowClickSelection=True,
        singleClickEdit=True,
        stopEditingWhenCellsLoseFocus=True,
        animateRows=False,
        domLayout="normal",
        pinnedBottomRowData=pinned,
        getRowStyle=row_style,
        onCellValueChanged=on_edit,
        onCellEditingStopped=on_edit,
        onGridReady=on_ready,
        onFirstDataRendered=JsCode(
            """
            function(params) {
                var g = window.__avinorGrid;
                if (g && g.refreshTotals) g.refreshTotals(params.api);
            }
            """
        ),
    )

    grid = AgGrid(
        df,
        gridOptions=gb.build(),
        height=height,
        width="100%",
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        update_mode=GridUpdateMode.VALUE_CHANGED,
        update_on=[("cellValueChanged", 250)],
        allow_unsafe_jscode=True,
        theme="streamlit",
        key=grid_key,
        fit_columns_on_grid_load=False,
        custom_css=_CUSTOM_CSS,
    )
    return pd.DataFrame(grid["data"])


def _streamlit_editor(df: pd.DataFrame, height: int, editor_key: str, taxa: float) -> pd.DataFrame:
    edit_labels = set(EDITABLE_LABELS.values())
    _PCT_COLS = {
        "TX conv. oport.",
        "TX conv. (média)",
        "Conversão",
        "TX conv. projetada",
    }
    cfg = {}
    for col in df.columns:
        if col in edit_labels:
            if col in _PCT_COLS:
                cfg[col] = st.column_config.NumberColumn(col, format="%.0f", min_value=0, max_value=100)
            elif col in ("Ticket médio", "Meta manual (R$)"):
                cfg[col] = st.column_config.NumberColumn(col, format="%.0f", min_value=0, step=100)
            elif col == "Recorrência":
                cfg[col] = st.column_config.NumberColumn(col, format="%.1f", min_value=0, step=0.1)
            else:
                cfg[col] = st.column_config.NumberColumn(col, format="%.0f", min_value=0)
        elif col == "Colaborador":
            cfg[col] = st.column_config.TextColumn(col, disabled=True, width="medium")
        else:
            cfg[col] = st.column_config.NumberColumn(col, disabled=True, format="%.0f")

    edited = st.data_editor(
        df,
        column_config=cfg,
        hide_index=True,
        use_container_width=True,
        height=height,
        key=editor_key,
    )
    return edited


def render_equipe_grid(
    state_rows: list[dict],
    ano: int,
    mes: int,
    taxa: float,
    state_key: str,
) -> None:
    height = GRID_VIEW_HEIGHT
    grid_key = f"{state_key}_ag"
    editor_key = f"{state_key}_ed"

    st.caption(
        "Colunas **azuis** = você preenche. **Amarelas** = proporção pelo fat. dos 3 meses anteriores "
        "(meta empresa ÷ 12 × peso). **Oport. calc.**, **Cobertura** e **Meta calc.** atualizam na hora. "
        "**Salvar** grava só as azuis."
    )

    ag_df = rows_to_aggrid_df(state_rows)
    ag = _try_aggrid(ag_df, height, grid_key)
    if ag is not None:
        st.session_state[f"{state_key}_agdf"] = ag
        return

    editor_df = rows_to_editor_df(state_rows)
    edited = _streamlit_editor(editor_df, height, editor_key, taxa)
    st.session_state[f"{state_key}_agdf"] = edited
