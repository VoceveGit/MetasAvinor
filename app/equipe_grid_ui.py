from __future__ import annotations

import pandas as pd
import streamlit as st

import json

from app.equipe_grid_logic import (
    AGGRID_EDITABLE_FIELDS,
    AGGRID_FIELD_LABELS,
    AGGRID_HIDDEN_FIELDS,
    EDITABLE_LABELS,
    GRID_SECTIONS,
    GRID_VIEW_HEIGHT,
    aplicar_lote_coluna,
    coluna_confere_lote,
    restaurar_lote_coluna,
    snapshot_lote_coluna,
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
_HIST = {
    "backgroundColor": "#eef4fb",
    "color": "#1e3a5f",
}
_CALC = {
    "backgroundColor": "#dcfce7",
    "color": "#14532d",
    "fontWeight": "700",
    "borderLeft": "2px solid #22c55e",
}
_READ_PROP = {
    "backgroundColor": "#fef9c3",
    "color": "#713f12",
    "fontWeight": "500",
    "borderLeft": "2px solid #facc15",
}
AGGRID_PROP_FIELDS = frozenset({"peso_3m", "meta_prop", "ajuste"})
_GOLD_FIELDS = frozenset(
    {"tx_proj_sug", "conv_sug", "pos_sug", "rec_sug", "ticket_sug", "meta_calc"}
)
_HIST_FIELDS = frozenset(
    {"tx_cob_hist", "tx_oport", "pos_media", "rec_media", "ticket_hist", "fat_media"}
)
_CALC_FIELDS_STYLE = frozenset({"cob", "oport_calc"})
_GOLD = {
    "backgroundColor": "#fbefc9",
    "color": "#7a5300",
    "fontWeight": "700",
    "borderLeft": "2px solid #d4a017",
}
_FINAL = {
    "backgroundColor": "#e6f2ea",
    "color": "#14532d",
    "fontWeight": "700",
    "borderLeft": "2px solid #3d6b5c",
}
_LOCKED_EDIT = {
    "backgroundColor": "#f1f4f8",
    "color": "#334155",
    "borderLeft": "2px solid #cbd5e1",
}

_HEADER_HELP = {
    "cart": "Clientes ativos na carteira do colaborador.",
    "tx_cob_hist": "Ativação histórica: clientes distintos que compraram ÷ carteira, média dos 3 meses fechados.",
    "tx_proj_sug": "Sugestão de ativação (histórico + ~5%, em degraus de 5). Vale quando o manual está vazio.",
    "tx_proj": "Você define: que % da carteira precisa comprar neste mês. Vazio = vale a sugestão.",
    "cob": "Carteira × ativação que vale (manual ou sugestão) = clientes que precisam comprar.",
    "oport": "Contatos no mês pela planilha de rotas (contatos por semana × 4).",
    "tx_oport": "Conversão histórica: notas ÷ oportunidades nos 3 meses fechados.",
    "conv_sug": "Sugestão de conversão (histórico + ~5%, em degraus de 5). Vale quando o manual está vazio.",
    "conv": "Você define: de cada 100 contatos, quantos viram nota. Vazio = vale a sugestão.",
    "oport_calc": "Oportunidades × conversão que vale = notas esperadas no mês.",
    "pos_media": "Notas por mês, em média nos 3 meses fechados.",
    "pos_sug": "Cobertura calculada × recorrência que vale = notas sugeridas no mês.",
    "pos": "Você define as notas do mês. Vazio = vale a sugestão.",
    "rec_media": "Notas ÷ clientes nos 3 meses fechados.",
    "rec_sug": "Sugestão de recorrência (histórico × 1,05). Vale quando o manual está vazio.",
    "rec": "Você define: notas por cliente no mês. Vazio = vale a sugestão.",
    "ticket_hist": "Faturamento médio ÷ notas nos 3 meses fechados.",
    "ticket_sug": (
        "Ticket histórico × (1 + crescimento vs os mesmos 3 meses do ano passado). "
        "Mínimo +2%, máximo +15%. Vale quando o manual está vazio."
    ),
    "ticket": "Você define o ticket do mês. Vazio = vale o sugerido.",
    "fat_media": "Faturamento médio nos 3 meses fechados.",
    "meta_calc": "Quanto ele entrega com o histórico e as alavancas: ticket × recorrência × cobertura. Pode ser menos ou mais que a cota do plano.",
    "meta_man": "Você impõe o número. Vazio = a meta do mês usa o quanto ele entrega.",
    "peso_3m": "Faturamento dele ÷ faturamento da equipe nos 3 meses fechados. Serve para calcular a cota do plano.",
    "meta_prop": "Fatia dele no alvo da empresa neste mês (anual → mês × peso 3m). É a cota, não o que se cobra se as alavancas disserem outra coisa.",
    "ajuste": "Meta do mês ÷ cota do plano − 1. Negativo = cobra menos que a fatia crua do anual.",
    "meta_final": "O que vale: o manual, se houver; senão o quanto ele entrega. A cota do plano fica só como referência.",
    "realizado": "Faturado no mês até agora.",
}
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
    ".ag-header-cell-text::after": {
        "content": "'?'",
        "display": "inline-flex",
        "align-items": "center",
        "justify-content": "center",
        "width": "13px",
        "height": "13px",
        "margin-left": "5px",
        "border-radius": "50%",
        "border": "1px solid #94a3b8",
        "color": "#64748b",
        "font-size": "9px",
        "font-weight": "700",
        "vertical-align": "1px",
    },
    ".ag-header-cell[col-id='colab'] .ag-header-cell-text::after": {"content": "none"},
    ".ag-tooltip": {
        "max-width": "340px",
        "white-space": "normal",
        "line-height": "1.45",
        "font-size": "12.5px",
        "padding": "8px 10px",
        "background": "#12261d !important",
        "color": "#eef3f0 !important",
        "border-radius": "8px",
        "border": "none !important",
    },
    ".ag-overlay-loading-wrapper": {"display": "none !important"},
    ".ag-cell-edit-input": {
        "font": "inherit",
        "text-align": "right",
        "padding": "0 8px",
    },
    ".ag-header-cell[col-id='oport'], .ag-cell[col-id='oport']": {
        "border-left": "3px solid #171717 !important",
    },
    ".ag-header-cell[col-id='pos_media'], .ag-cell[col-id='pos_media']": {
        "border-left": "3px solid #171717 !important",
    },
    ".ag-header-cell[col-id='rec_media'], .ag-cell[col-id='rec_media']": {
        "border-left": "3px solid #171717 !important",
    },
    ".ag-header-cell[col-id='ticket_hist'], .ag-cell[col-id='ticket_hist']": {
        "border-left": "3px solid #171717 !important",
    },
    ".ag-header-cell[col-id='fat_media'], .ag-cell[col-id='fat_media']": {
        "border-left": "3px solid #171717 !important",
    },
    ".ag-header-cell[col-id='peso_3m'], .ag-cell[col-id='peso_3m']": {
        "border-left": "3px solid #171717 !important",
    },
    ".ag-pinned-right-header, .ag-pinned-right-cols-container": {
        "box-shadow": "-6px 0 10px rgba(15, 23, 42, 0.08)",
        "background": "#e6f2ea",
    },
    ".ag-header-cell[col-id='meta_final'], .ag-cell[col-id='meta_final']": {
        "border-left": "3px solid #3d6b5c !important",
    },
}

_MONEY_FIELDS = frozenset(
    {
        "fat_media",
        "ticket_hist",
        "ticket",
        "ticket_sug",
        "meta_prop",
        "meta_prop_sem",
        "meta_prop_dia",
        "meta_calc",
        "meta_man",
        "meta_final",
        "realizado",
    }
)
_PCT_FIELDS = frozenset(
    {"tx_oport", "tx_cob_hist", "conv", "conv_sug", "tx_proj", "tx_proj_sug", "peso_3m", "ajuste"}
)
_INT_FIELDS = frozenset(
    {
        "cart",
        "oport",
        "oport_calc",
        "cob_media",
        "cob",
        "dif_cob",
        "pos_media",
        "pos_sug",
        "pos",
        "pos_prop",
        "cob_prop",
    }
)
_DECIMAL_FIELDS = frozenset({"rec_media", "rec", "rec_sug"})
_CALC_FIELDS = frozenset({"oport_calc", "cob", "dif_cob"})

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
    "tx_cob_hist": 108,
    "tx_proj_sug": 108,
    "conv_sug": 104,
    "pos_sug": 108,
    "pos": 108,
    "rec_sug": 104,
    "fat_media": 116,
    "pos_media": 104,
    "ticket_hist": 104,
    "ticket": 96,
    "ticket_sug": 104,
    "rec_media": 104,
    "rec": 92,
    "peso_3m": 96,
    "meta_prop": 112,
    "meta_prop_sem": 108,
    "meta_prop_dia": 116,
    "pos_prop": 108,
    "cob_prop": 108,
    "meta_calc": 112,
    "meta_man": 116,
    "ajuste": 92,
    "meta_final": 124,
    "realizado": 112,
}


_SUG_FIELDS = frozenset({"conv", "tx_proj", "rec", "pos", "ticket", "meta_man"})


def _js_sug_style(base: dict):
    """Célula azul vazia: mostra a sugestão em dourado (o valor gravado continua vazio)."""
    from st_aggrid.shared import JsCode

    return JsCode(
        "function(params) {"
        f"var base = {json.dumps(base)};"
        "var v = params.value;"
        "if (params.node && params.node.rowPinned) return {backgroundColor:'#d9cbb8',color:'#111827',fontWeight:'800'};"
        "if (v === null || v === undefined || v === '') {"
        "  return Object.assign({}, base, {color: '#9a6b00', fontStyle: 'italic', fontWeight: '600'});"
        "}"
        "return base;"
        "}"
    )


def _js_guia_install():
    """JS: barra de seções no iframe da grade — salto instantâneo, sem rerun."""
    return """
            g.installGuia = function(api, eGridDiv, items) {
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
            };
    """


def _js_grid_ready(quiet: bool = False):
    from st_aggrid.shared import JsCode

    def _esc(s: str) -> str:
        return (
            str(s)
            .encode("unicode_escape")
            .decode("ascii")
            .replace("'", "\\'")
        )

    items = "[" + ",".join(
        "{label:'%s',jump:'%s'}" % (_esc(s["label"]), _esc(s["jump"]))
        for s in GRID_SECTIONS
    ) + "]"
    code = (
        """
        function(params) {
            window.__avinorGrid = window.__avinorGrid || {};
            var g = window.__avinorGrid;
            g.quiet = __QUIET__;
            if (g._ready !== 'v10') {
            g.n = function(v) {
                var x = Number(v);
                return isNaN(x) ? 0 : x;
            };
            g.isSet = function(v) {
                return v !== null && v !== undefined && v !== '';
            };
            g.eff = function(d, f) {
                return g.isSet(d[f]) ? d[f] : d[f + '_sug'];
            };
            g.rowOportCalc = function(d) {
                if (!d) return null;
                var c = g.eff(d, 'conv');
                if (!g.isSet(c)) return null;
                var conv = g.n(c);
                if (conv === 0) return 0;
                return Math.round(g.n(d.oport) * conv / 100);
            };
            g.rowCobVal = function(d) {
                if (!d) return null;
                var t = g.eff(d, 'tx_proj');
                if (!g.isSet(t)) return null;
                var txp = g.n(t);
                if (txp === 0) return 0;
                var cart = g.n(d.cart);
                if (cart <= 0) return null;
                return Math.round(cart * txp / 100);
            };
            g.rowDifCob = function(d) {
                var cob = g.rowCobVal(d);
                if (cob === null || cob === undefined) return null;
                if (cob === 0) return 0;
                return Math.max(0, g.n(d.cart) - cob);
            };
            g.rowPosSug = function(d) {
                var cob = g.rowCobVal(d);
                var rc = g.eff(d, 'rec');
                if (cob === null || cob === undefined || cob === 0 || !g.isSet(rc)) return null;
                var rec = g.n(rc);
                if (rec === 0) return 0;
                return Math.round(cob * rec);
            };
            g.rowMetaCalc = function(d) {
                var cob = g.rowCobVal(d);
                if (cob === null || cob === undefined) return null;
                if (cob === 0) return 0;
                var tk = g.eff(d, 'ticket');
                var rc = g.eff(d, 'rec');
                if (!g.isSet(tk) || !g.isSet(rc)) return null;
                var ticket = g.n(tk);
                var rec = g.n(rc);
                if (ticket === 0 || rec === 0) return 0;
                return Math.round(ticket * rec * cob);
            };
            g.rowFinal = function(d) {
                if (!d) return null;
                if (g.isSet(d.meta_man) && g.n(d.meta_man) > 0) return g.n(d.meta_man);
                var cap = g.rowMetaCalc(d);
                if (cap !== null && cap > 0) return cap;
                return g.isSet(d.meta_prop) ? g.n(d.meta_prop) : null;
            };
            g.rowAjuste = function(d) {
                if (!d) return null;
                var fin = g.rowFinal(d);
                var auto = g.n(d.meta_prop);
                if (fin === null || auto <= 0) return null;
                return Math.round((fin / auto - 1) * 1000) / 10;
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
                var finalSum = 0;
                for (var j = 0; j < rows.length; j++) {
                    var rd = rows[j];
                    var fv = g.rowFinal(rd);
                    if (fv !== null) finalSum += fv;
                    var oc = g.rowOportCalc(rd);
                    if (oc !== null && oc !== undefined) ocalc += oc;
                    var cb = g.rowCobVal(rd);
                    if (cb !== null && cb !== undefined) cobSum += cb;
                    var df = g.rowDifCob(rd);
                    if (df !== null && df !== undefined) difSum += df;
                    var mc = g.rowMetaCalc(rd);
                    if (mc !== null && mc !== undefined) metaSum += mc;
                    var cv = g.eff(rd, 'conv');
                    if (g.isSet(cv)) {
                        convSum += g.n(cv);
                        convN += 1;
                    }
                    var tp = g.eff(rd, 'tx_proj');
                    if (g.isSet(tp)) {
                        txpSum += g.n(tp);
                        txpN += 1;
                    }
                }
                var txO = oport > 0 ? Math.round(s('pos_media') / oport * 10000) / 100 : 0;
                var cobM = s('cob_media');
                var txCob = cart > 0 ? Math.round(cobM / cart * 10000) / 100 : 0;
                var convAvg = convN > 0 ? Math.round(convSum / convN) : null;
                var txpAvg = txpN > 0 ? Math.round(txpSum / txpN) : null;
                var autoSum = s('meta_prop');
                var setPinned = function(rowsPinned) {
                    if (api.setGridOption) api.setGridOption('pinnedBottomRowData', rowsPinned);
                    else api.setPinnedBottomRowData(rowsPinned);
                };
                setPinned([{
                    colab: 'TOTAL',
                    meta_final: Math.round(finalSum),
                    ajuste: autoSum > 0 ? Math.round((finalSum / autoSum - 1) * 1000) / 10 : null,
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
                    peso_3m: Math.round(s('peso_3m') * 100) / 100,
                    meta_prop: Math.round(s('meta_prop')),
                    meta_prop_sem: Math.round(s('meta_prop_sem')),
                    meta_prop_dia: Math.round(s('meta_prop_dia')),
                    pos_prop: Math.round(s('pos_prop')),
                    cob_prop: Math.round(s('cob_prop')),
                    pos_sug: (function() {
                        var t = 0;
                        for (var k = 0; k < rows.length; k++) {
                            var ps = g.rowPosSug(rows[k]);
                            if (ps !== null && ps !== undefined) t += ps;
                        }
                        return Math.round(t);
                    })(),
                    meta_calc: Math.round(metaSum),
                    realizado: Math.round(s('realizado')),
                }]);
                g.refreshPinned(api);
            };
            g._ready = 'v10';
            }
            """
        + _js_guia_install()
        + """
            g.refreshTotals(params.api);
            g.installGuia(params.api, params.eGridDiv, __ITEMS__);
            setTimeout(function() {
                g.installGuia(params.api, params.eGridDiv, __ITEMS__);
            }, 50);
        }
        """
    )
    code = (
        code.replace("__QUIET__", "true" if quiet else "false").replace(
            "__ITEMS__", items
        )
    )
    return JsCode(code)


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
                columns: ['oport_calc', 'cob', 'dif_cob', 'pos_sug', 'pos', 'meta_calc', 'ajuste', 'meta_final'],
                force: true
            });
            g.refreshTotals(params.api);
        }
        """
    )


def _js_tooltip(ctx: dict):
    from st_aggrid.shared import JsCode

    return JsCode(
        """
        function(params) {
            if (window.__avinorGrid && window.__avinorGrid.quiet) return null;
            var C = __CTX__;
            var d = params.data;
            if (!d) return null;
            var f = params.colDef.field;
            function n(v) { var x = Number(v); return isNaN(x) ? 0 : x; }
            function set(v) { return v !== null && v !== undefined && v !== ''; }
            function br(v, dec) {
                dec = dec || 0;
                return n(v).toLocaleString('pt-BR', {minimumFractionDigits: dec, maximumFractionDigits: dec});
            }
            function rs(v) { return 'R$ ' + br(Math.round(n(v))); }
            function pc(v, dec) { return br(v, dec === undefined ? 1 : dec) + '%'; }
            if (params.node && params.node.rowPinned) {
                if (f === 'tx_oport') return 'Equipe: notas ÷ oportunidades = ' + br(d.pos_media) + ' ÷ ' + br(d.oport) + ' = ' + pc(d.tx_oport) + '.';
                if (f === 'tx_cob_hist') return 'Equipe: cobertura média ÷ carteira = ' + br(d.cob_media) + ' ÷ ' + br(d.cart) + ' = ' + pc(d.tx_cob_hist) + '.';
                if (f === 'conv' || f === 'tx_proj') return 'Média dos valores que valem: o digitado ou, se vazio, a sugestão.';
                if (f === 'meta_final') return 'Meta do mês da equipe: ' + rs(d.meta_final) + '. Soma do que vale em cada um (manual ou quanto entrega).';
                if (f === 'ajuste') return 'Equipe: soma das metas do mês ÷ soma das cotas do plano − 1 = ' + pc(d.ajuste) + '.';
                return 'Total da equipe: soma das linhas.';
            }
            var g = window.__avinorGrid || {};
            var cob = g.rowCobVal ? g.rowCobVal(d) : null;
            var fin = g.rowFinal ? g.rowFinal(d) : null;
            var adj = g.rowAjuste ? g.rowAjuste(d) : null;
            switch (f) {
            case 'colab':
                return d.aj_info ? d.colab + ' · ' + d.aj_info : d.colab;
            case 'cart':
                return br(d.cart) + ' clientes ativos na carteira. É a base: a meta de cobertura nunca passa disso.';
            case 'oport':
                return br(d.oport) + ' contatos no mês pela planilha de rotas. São as chances de venda com clientes que já são dele.';
            case 'tx_oport':
                return 'Notas ÷ oportunidades = ' + br(d.pos_media) + ' ÷ ' + br(d.oport) + ' = ' + pc(d.tx_oport) + '. De cada 100 contatos, cerca de ' + br(d.tx_oport) + ' viraram nota nos 3 últimos meses.';
            case 'conv':
                if (!set(d.conv)) return 'Vazio: vale a sugestão ' + pc(d.conv_sug, 0) + ' (histórico ' + pc(d.tx_oport) + ' + ~5%, em degraus de 5). Digite para usar outro valor.';
                return 'Conversão meta ' + pc(d.conv, 0) + ': de cada 100 contatos, ' + br(d.conv) + ' precisam virar nota. Histórico: ' + pc(d.tx_oport) + '.';
            case 'oport_calc':
                var cvE = set(d.conv) ? d.conv : d.conv_sug;
                if (!set(cvE)) return 'Sem histórico de conversão para calcular.';
                return 'Oportunidades × conversão' + (set(d.conv) ? '' : ' sugerida') + ' = ' + br(d.oport) + ' × ' + pc(cvE, 0) + ' = ' + br(Math.round(n(d.oport) * n(cvE) / 100)) + ' notas esperadas no mês.';
            case 'cob_media':
                return br(d.cob_media) + ' clientes diferentes compraram por mês, em média, nos 3 últimos meses fechados.';
            case 'tx_cob_hist':
                return 'Cobertura média ÷ carteira = ' + br(d.cob_media) + ' ÷ ' + br(d.cart) + ' = ' + pc(d.tx_cob_hist) + '. É quanto da carteira costuma comprar no mês.';
            case 'tx_proj':
                if (!set(d.tx_proj)) return 'Vazio: vale a sugestão de ativação ' + pc(d.tx_proj_sug, 0) + ' (histórico ' + pc(d.tx_cob_hist) + ' + ~5%). Digite para usar outro valor.';
                return 'Ativação manual ' + pc(d.tx_proj, 0) + ': essa parte da carteira precisa comprar no mês. Histórico: ' + pc(d.tx_cob_hist) + '.';
            case 'tx_proj_sug':
                return 'Ativação sugerida ' + pc(d.tx_proj_sug, 0) + ' com base nos 3 meses fechados.';
            case 'cob':
                if (cob === null) return 'Sem carteira ou ativação para calcular.';
                return 'Carteira × ativação' + (set(d.tx_proj) ? '' : ' sugerida') + ' = ' + br(d.cart) + ' × ' + pc(set(d.tx_proj) ? d.tx_proj : d.tx_proj_sug, 0) + ' = ' + br(cob) + ' clientes.';
            case 'dif_cob':
                if (cob === null) return 'Sem carteira ou TX para calcular.';
                return 'Carteira − cobertura = ' + br(d.cart) + ' − ' + br(cob) + ' = ' + br(Math.max(0, n(d.cart) - cob)) + ' clientes podem ficar sem comprar neste mês sem prejudicar a meta.';
            case 'fat_media':
                return 'Média dos 3 últimos meses fechados: ' + rs(d.fat_media) + ' por mês.';
            case 'pos_media':
                return br(d.pos_media) + ' notas por mês, em média. Um cliente pode ter várias notas no mês (recompra).';
            case 'pos_sug':
                return 'Cobertura × recorrência que vale = positivação sugerida.';
            case 'pos':
                if (!set(d.pos)) return 'Vazio: vale a positivação sugerida. Digite para usar outro valor.';
                return 'Positivação manual: ' + br(d.pos) + ' notas no mês.';
            case 'ticket_sug':
                return d.tk_info || '';
            case 'ticket_hist':
                return 'Faturamento médio ÷ notas = ' + rs(d.fat_media) + ' ÷ ' + br(d.pos_media) + ' = ' + rs(d.ticket_hist) + ' por nota.';
            case 'ticket':
                if (!set(d.ticket)) return 'Vazio: vale o ticket sugerido ' + rs(d.ticket_sug) + ' (dourado). Digite aqui para usar outro valor. Histórico: ' + rs(d.ticket_hist) + '.';
                return 'Ticket meta ' + rs(d.ticket) + ' por nota. Histórico: ' + rs(d.ticket_hist) + '.';
            case 'rec_media':
                return 'Notas ÷ clientes = ' + br(d.pos_media) + ' ÷ ' + br(d.cob_media) + ' = ' + br(d.rec_media, 1) + '. Cada cliente que compra faz, em média, ' + br(d.rec_media, 1) + ' pedidos no mês.';
            case 'rec':
                if (!set(d.rec)) return 'Vazio: vale a sugestão ' + br(d.rec_sug, 1) + ' (histórico ' + br(d.rec_media, 1) + ' + 5%). Digite para usar outro valor.';
                return 'Recorrência meta ' + br(d.rec, 1) + ' notas por cliente no mês. Histórico: ' + br(d.rec_media, 1) + '.';
            case 'meta_calc':
                var tkE = set(d.ticket) ? d.ticket : d.ticket_sug;
                var rcE = set(d.rec) ? d.rec : d.rec_sug;
                if (cob === null || !set(tkE) || !set(rcE)) return 'Sem histórico suficiente para calcular o quanto ele entrega.';
                var usaSug = !set(d.ticket) || !set(d.rec) || !set(d.tx_proj);
                return 'Quanto entrega (alavancas): ticket × recorrência × cobertura = ' + rs(tkE) + ' × ' + br(rcE, 1) + ' × ' + br(cob) + ' = ' + rs(n(tkE) * n(rcE) * cob) + '. Pode ser menos ou mais que a cota do plano (' + rs(d.meta_prop) + ').' + (usaSug ? ' Azul vazio usa o dourado.' : '');
            case 'peso_3m':
                return 'Faturamento dele ÷ faturamento da equipe nos 3 meses fechados = ' + pc(d.peso_3m, 2) + '. Monta a cota dele no alvo da empresa.';
            case 'meta_prop':
                return 'Cota do plano: meta da empresa em ' + C.mes + ' × peso = ' + rs(C.base) + ' × ' + pc(d.peso_3m, 2) + ' = ' + rs(d.meta_prop) + '. É a fatia crua do anual, não o que se cobra se as alavancas disserem outra coisa.';
            case 'meta_man':
                if (!set(d.meta_man) || n(d.meta_man) <= 0) return 'Vazio: a meta do mês usa o quanto ele entrega (alavancas). Digite para impor outro valor.';
                return 'Manual ' + rs(d.meta_man) + ' contra a cota do plano ' + rs(d.meta_prop) + (adj !== null ? ' (' + (adj > 0 ? '+' : '') + pc(adj) + ').' : '.') + (d.aj_info ? ' ' + d.aj_info : '');
            case 'ajuste':
                if (fin === null || !n(d.meta_prop)) return 'Sem cota do plano para comparar.';
                return 'Meta do mês ÷ cota do plano − 1 = ' + rs(fin) + ' ÷ ' + rs(d.meta_prop) + ' − 1 = ' + (adj > 0 ? '+' : '') + pc(adj) + '.' + (d.aj_info ? ' ' + d.aj_info : '');
            case 'meta_final':
                if (set(d.meta_man) && n(d.meta_man) > 0) return 'Vale o manual: ' + rs(fin) + ' (cota do plano ' + rs(d.meta_prop) + ').';
                return 'Vale o quanto ele entrega (alavancas): ' + rs(fin) + '. Cota do plano: ' + rs(d.meta_prop) + '.';
            case 'realizado':
                if (fin && fin > 0) return 'Faturado no mês: ' + rs(d.realizado) + ' = ' + pc(n(d.realizado) / fin * 100, 0) + ' da meta do mês (' + rs(fin) + ').';
                return 'Faturado no mês: ' + rs(d.realizado) + '.';
            case 'meta_prop_sem':
                return 'Cota do plano ÷ dias úteis × 5 = ' + rs(d.meta_prop) + ' ÷ ' + C.uteis + ' × 5 = ' + rs(d.meta_prop_sem) + ' por semana.';
            case 'meta_prop_dia':
                return 'Cota do plano ÷ dias úteis = ' + rs(d.meta_prop) + ' ÷ ' + C.uteis + ' = ' + rs(d.meta_prop_dia) + ' por dia útil.';
            case 'pos_prop':
                return br(d.pos_prop) + ' notas para bater a meta automática: ' + br(d.cob_prop) + ' clientes × recorrência.';
            case 'cob_prop':
                return 'Meta automática ÷ (ticket histórico × recorrência) = ' + rs(d.meta_prop) + ' ÷ (' + rs(d.ticket_hist) + ' × ' + br(d.rec_media, 1) + ') = ' + br(d.cob_prop) + ' clientes da carteira.';
            }
            return null;
        }
        """.replace("__CTX__", json.dumps(ctx, ensure_ascii=False))
    )


def _js_live_editor():
    """Editor com máscara pt-BR enquanto digita (R$ milhar, %, 1 decimal)."""
    from st_aggrid.shared import JsCode

    return JsCode(
        """
        class {
            init(params) {
                this.params = params;
                this.kind = params.kind || (params.cellEditorParams && params.cellEditorParams.kind) || 'int';
                this.eInput = document.createElement('input');
                this.eInput.className = 'ag-cell-edit-input ag-input-field-input';
                this.eInput.setAttribute('inputmode', this.kind === 'rec' ? 'decimal' : 'numeric');
                this.eInput.value = this._fmtInit(params.value);
                var self = this;
                this.eInput.addEventListener('input', function () { self._mask(); });
            }
            _fmtInit(v) {
                if (v === null || v === undefined || v === '') return '';
                var n = Number(v);
                if (isNaN(n)) return '';
                if (this.kind === 'money') return 'R$ ' + Math.round(n).toLocaleString('pt-BR');
                if (this.kind === 'int') return Math.round(n).toLocaleString('pt-BR');
                if (this.kind === 'pct') return String(Math.round(n)) + '%';
                return n.toLocaleString('pt-BR', {minimumFractionDigits: 1, maximumFractionDigits: 1});
            }
            _mask() {
                var el = this.eInput;
                var pos = el.selectionStart || 0;
                var left = el.value.slice(0, pos).replace(/\\D/g, '').length;
                var out;
                if (this.kind === 'rec') {
                    var raw = el.value.replace(/[^\\d,]/g, '');
                    var p = raw.split(',');
                    out = (p[0] || '').replace(/\\D/g, '');
                    if (raw.indexOf(',') >= 0) out += ',' + (p.slice(1).join('').replace(/\\D/g, '').slice(0, 1));
                } else {
                    var d = el.value.replace(/\\D/g, '');
                    if (!d) { el.value = ''; return; }
                    d = d.replace(/^0+(?=\\d)/, '');
                    if (this.kind === 'money') out = 'R$ ' + d.replace(/\\B(?=(\\d{3})+(?!\\d))/g, '.');
                    else if (this.kind === 'int') out = d.replace(/\\B(?=(\\d{3})+(?!\\d))/g, '.');
                    else out = d + '%';
                }
                if (out === el.value) return;
                el.value = out;
                if (this.kind === 'rec') return;
                var i = 0, seen = 0;
                while (i < out.length && seen < left) { if (/\\d/.test(out[i])) seen++; i++; }
                try { el.setSelectionRange(i, i); } catch (e) {}
            }
            getGui() { return this.eInput; }
            afterGuiAttached() { this.eInput.focus(); this.eInput.select(); }
            getValue() {
                var s = (this.eInput.value || '').trim();
                if (!s) return null;
                if (this.kind === 'rec') {
                    var n = Number(s.replace(/\\./g, '').replace(',', '.'));
                    return isNaN(n) ? null : n;
                }
                var d = s.replace(/\\D/g, '');
                if (!d) return null;
                return Number(d);
            }
            isCancelAfterEnd() { return false; }
            destroy() {}
            isPopup() { return false; }
        }
        """
    )


def _js_parse_br():
    from st_aggrid.shared import JsCode

    return JsCode(
        """
        function(params) {
            var v = params.newValue;
            if (v === '' || v === null || v === undefined) return null;
            if (typeof v === 'number') return isNaN(v) ? null : v;
            var s = String(v).replace(/R\\$ /gi, '').replace(/%/g, '').trim();
            if (!s) return null;
            if (s.indexOf(',') >= 0) s = s.replace(/\\./g, '').replace(',', '.');
            else {
                var parts = s.split('.');
                if (parts.length > 1 && parts[parts.length - 1].length === 3) s = parts.join('');
            }
            var n = Number(s);
            return isNaN(n) ? null : n;
        }
        """
    )


def _try_aggrid(
    df: pd.DataFrame,
    height: int,
    grid_key: str,
    locked: bool = False,
    ctx: dict | None = None,
    tips: bool = True,
    jump_col: str = "",
    server_sync: str = "client_wins",
) -> pd.DataFrame | None:
    try:
        from st_aggrid import AgGrid, DataReturnMode, GridOptionsBuilder, GridUpdateMode
        from st_aggrid.shared import JsCode
    except ImportError:
        return None

    pinned = [total_row_from_aggrid_df(df)]
    tooltip = _js_tooltip(ctx or {"mes": "", "base": 0, "uteis": 0})
    live_ed = _js_live_editor()
    parse_br = _js_parse_br()
    css = dict(_CUSTOM_CSS)
    if not tips:
        css[".ag-header-cell-text::after"] = {"content": "none"}
        css[".ag-tooltip"] = {"display": "none !important"}

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
            var fld = params.colDef.field;
            var dec = (fld === 'tx_oport' || fld === 'ajuste' || fld === 'peso_3m') ? 1 : 0;
            var sig = (fld === 'ajuste' && v > 0) ? '+' : '';
            return sig + v.toLocaleString('pt-BR', {minimumFractionDigits: dec, maximumFractionDigits: dec}) + '%';
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
    fmt_sug = JsCode(
        """
        function(params) {
            var d = params.data || {};
            var f = params.colDef.field;
            var v = params.value;
            if (v === null || v === undefined || v === '') {
                if (params.node && params.node.rowPinned) return '—';
                if (f === 'meta_man') {
                    var g = window.__avinorGrid;
                    v = (g && g.rowMetaCalc) ? g.rowMetaCalc(d) : d.meta_calc;
                } else {
                    v = d[f + '_sug'];
                }
            }
            if (v === null || v === undefined || v === '' || isNaN(Number(v))) return '—';
            var x = Number(v);
            if (f === 'rec') return x.toLocaleString('pt-BR', {minimumFractionDigits: 1, maximumFractionDigits: 1});
            if (f === 'pos') return Math.round(x).toLocaleString('pt-BR');
            if (f === 'ticket' || f === 'meta_man') return 'R$ ' + Math.round(x).toLocaleString('pt-BR');
            return Math.round(x).toLocaleString('pt-BR') + '%';
        }
        """
    )
    row_style = JsCode(
        """
        function(params) {
            if (params.node.rowPinned === 'bottom') {
                return { fontWeight: '800', backgroundColor: '#d9cbb8', color: '#111827' };
            }
        }
        """
    )
    eff_js = """
            function isSet(v) { return v !== null && v !== undefined && v !== ''; }
            function eff(d, f) { return isSet(d[f]) ? d[f] : d[f + '_sug']; }
            function cobVal(d) {
                var t = eff(d, 'tx_proj');
                if (!isSet(t)) return null;
                var txp = Number(t);
                if (isNaN(txp)) return null;
                if (txp === 0) return 0;
                var cart = Number(d.cart || 0);
                if (cart <= 0) return null;
                return Math.round(cart * txp / 100);
            }
    """

    def _vg(pinned_field: str, body: str):
        return JsCode(
            "function(params) {"
            + eff_js
            + "if (params.node && params.node.rowPinned) { return params.data ? params.data."
            + pinned_field
            + " : null; }"
            + "var d = params.data; if (!d) return null;"
            + body
            + "}"
        )

    vg_oport = _vg(
        "oport_calc",
        "var c = eff(d, 'conv'); if (!isSet(c)) return null;"
        "var conv = Number(c); if (isNaN(conv)) return null;"
        "return Math.round(Number(d.oport || 0) * conv / 100);",
    )
    vg_cob = _vg("cob", "return cobVal(d);")
    vg_pos_sug = _vg(
        "pos_sug",
        "var cob = cobVal(d); var rc = eff(d, 'rec');"
        "if (cob === null || cob === 0 || !isSet(rc)) return null;"
        "var rec = Number(rc); if (isNaN(rec) || rec === 0) return 0;"
        "return Math.round(cob * rec);",
    )
    vg_dif = _vg(
        "dif_cob",
        "var cob = cobVal(d); if (cob === null) return null; if (cob === 0) return 0;"
        "return Math.max(0, Number(d.cart || 0) - cob);",
    )
    vg_meta = _vg(
        "meta_calc",
        "var cob = cobVal(d); if (cob === null) return null; if (cob === 0) return 0;"
        "var tk = eff(d, 'ticket'), rc = eff(d, 'rec');"
        "if (!isSet(tk) || !isSet(rc)) return null;"
        "var ticket = Number(tk), rec = Number(rc);"
        "if (isNaN(ticket) || isNaN(rec) || ticket === 0 || rec === 0) return 0;"
        "return Math.round(ticket * rec * cob);",
    )

    vg_final = JsCode(
        """
        function(params) {
            var d = params.data;
            if (!d) return null;
            var g = window.__avinorGrid;
            if (g && g.rowFinal) {
                var fv = g.rowFinal(d);
                return fv === null ? null : Math.round(fv);
            }
            var man = Number(d.meta_man);
            if (d.meta_man !== null && d.meta_man !== undefined && d.meta_man !== '' && !isNaN(man) && man > 0) {
                return Math.round(man);
            }
            var cap = Number(d.meta_calc);
            if (!isNaN(cap) && cap > 0) return Math.round(cap);
            var auto = Number(d.meta_prop);
            if (!isNaN(auto) && auto > 0) return Math.round(auto);
            var fin = Number(d.meta_final);
            return !isNaN(fin) && fin > 0 ? Math.round(fin) : null;
        }
        """
    )
    vg_ajuste = JsCode(
        """
        function(params) {
            if (params.node && params.node.rowPinned) {
                return params.data ? params.data.ajuste : null;
            }
            var g = window.__avinorGrid;
            return g && g.rowAjuste ? g.rowAjuste(params.data) : null;
        }
        """
    )

    gb = GridOptionsBuilder.from_dataframe(df)
    for field, label in AGGRID_FIELD_LABELS:
        if field in AGGRID_HIDDEN_FIELDS:
            gb.configure_column(field, headerName=label, hide=True, editable=False)
            continue
        w = _WIDTHS.get(field, 96)
        editable = field in AGGRID_EDITABLE_FIELDS and not locked
        if field in AGGRID_EDITABLE_FIELDS:
            cell_style = _LOCKED_EDIT if locked else _EDIT_BLUE
        elif field == "meta_final":
            cell_style = _FINAL
        elif field in _GOLD_FIELDS:
            cell_style = _GOLD
        elif field in _CALC_FIELDS_STYLE:
            cell_style = _CALC
        elif field in _HIST_FIELDS:
            cell_style = _HIST
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
            "sortable": field in ("colab", "meta_calc", "meta_final", "realizado"),
        }
        if tips:
            opts["tooltipValueGetter"] = tooltip
            if field in _HEADER_HELP:
                opts["headerTooltip"] = _HEADER_HELP[field]
        if field == "colab":
            opts["pinned"] = "left"
            opts["lockPinned"] = True
        if field == "meta_final":
            opts["pinned"] = "right"
            opts["lockPinned"] = True
            opts["suppressSizeToFit"] = True
            opts["minWidth"] = 124
        if field == "oport_calc":
            opts["valueGetter"] = vg_oport
        elif field == "cob":
            opts["valueGetter"] = vg_cob
        elif field == "pos_sug":
            opts["valueGetter"] = vg_pos_sug
        elif field == "dif_cob":
            opts["valueGetter"] = vg_dif
        elif field == "meta_calc":
            opts["valueGetter"] = vg_meta
        elif field == "meta_final":
            opts["valueGetter"] = vg_final
        elif field == "ajuste":
            opts["valueGetter"] = vg_ajuste
        if field in AGGRID_EDITABLE_FIELDS:
            opts["type"] = ["numericColumn", "numberColumnFilter"]
            opts["valueParser"] = parse_br
            opts["cellEditor"] = live_ed
            if field == "rec":
                opts["cellEditorParams"] = {"kind": "rec"}
            elif field in ("ticket", "meta_man"):
                opts["cellEditorParams"] = {"kind": "money"}
            elif field == "pos":
                opts["cellEditorParams"] = {"kind": "int"}
            else:
                opts["cellEditorParams"] = {"kind": "pct"}
            if field in _SUG_FIELDS:
                opts["valueFormatter"] = fmt_sug
                opts["cellStyle"] = _js_sug_style(cell_style)
            elif field in _PCT_FIELDS:
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
    on_ready = _js_grid_ready(quiet=not tips)
    gb.configure_grid_options(
        headerHeight=48,
        rowHeight=36,
        enableRangeSelection=True,
        suppressRowClickSelection=True,
        singleClickEdit=True,
        stopEditingWhenCellsLoseFocus=True,
        enterNavigatesVertically=True,
        enterNavigatesVerticallyAfterEdit=True,
        suppressLoadingOverlay=True,
        animateRows=False,
        suppressColumnVirtualisation=True,
        alwaysShowHorizontalScroll=True,
        alwaysShowVerticalScroll=True,
        scrollbarShowAlways=True,
        suppressHorizontalScroll=False,
        domLayout="normal",
        tooltipShowDelay=400 if tips else 60000,
        tooltipHideDelay=12000,
        tooltipMouseTrack=False,
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
        update_on=[("cellValueChanged", 400)],
        allow_unsafe_jscode=True,
        theme="streamlit",
        key=grid_key,
        fit_columns_on_grid_load=False,
        custom_css=css,
        server_sync_strategy=server_sync,
    )
    return pd.DataFrame(grid["data"])


def _streamlit_editor(df: pd.DataFrame, height: int, editor_key: str, taxa: float) -> pd.DataFrame:
    edit_labels = set(EDITABLE_LABELS.values())
    _PCT_COLS = {
        "Conversão média",
        "Conversão manual",
        "% Ativação média",
        "% Ativação manual",
    }
    cfg = {}
    for col in df.columns:
        if col in edit_labels:
            if col in _PCT_COLS:
                cfg[col] = st.column_config.NumberColumn(col, format="%.0f", min_value=0, max_value=100)
            elif col in ("Ticket médio manual", "Faturamento manual"):
                cfg[col] = st.column_config.NumberColumn(col, format="%.0f", min_value=0, step=100)
            elif col == "Recorrência manual":
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


def lote_keys_ativos(state_key: str) -> frozenset[str]:
    keys: list[str] = []
    for sec in GRID_SECTIONS:
        raw = st.session_state.get(f"{state_key}_lote_{sec['id']}")
        if raw is not None and float(raw) > 0:
            keys.append(sec["lote_key"])
    return frozenset(keys)


def overlay_lotes_ativos(rows: list[dict], state_key: str, taxa: float) -> list[dict]:
    """Enquanto o campo de lote estiver preenchido, esse valor manda na coluna."""
    out = list(rows)
    for sec in GRID_SECTIONS:
        raw = st.session_state.get(f"{state_key}_lote_{sec['id']}")
        if raw is None or float(raw) <= 0:
            continue
        cur = float(raw)
        tol = 0.51 if sec["kind"] in ("int", "money") else 0.05
        if not coluna_confere_lote(out, sec["lote_key"], cur, tol):
            out = aplicar_lote_coluna(out, sec["lote_key"], cur, taxa)
    return out


def render_guia_secoes(
    rows: list[dict],
    taxa: float,
    state_key: str,
    locked: bool,
) -> list[dict]:
    """Campos de lote: o salto entre blocos fica na barra instantânea da grade."""
    out = list(rows)
    prev_key = f"{state_key}_lote_vals"
    bak_key = f"{state_key}_lote_bak"
    prev = st.session_state.setdefault(prev_key, {})
    bak = st.session_state.setdefault(bak_key, {})

    def _on_lote() -> None:
        st.session_state[f"{state_key}_lote_tick"] = True

    nsec = len(GRID_SECTIONS)
    cols = st.columns(nsec)
    for i, sec in enumerate(GRID_SECTIONS):
        with cols[i]:
            st.caption(sec["label"])
            if locked:
                continue
            kind = sec["kind"]
            fmt = "%.0f" if kind in ("pct", "int", "money") else "%.1f"
            step = 0.1 if kind == "rec" else (100.0 if kind == "money" else 1.0)
            wid = f"{state_key}_lote_{sec['id']}"
            opts = dict(
                min_value=0.0,
                step=step,
                format=fmt,
                key=wid,
                placeholder="todos",
                label_visibility="collapsed",
                help=(
                    sec["hint"]
                    + " Enter ou clique fora para aplicar. "
                    "Apague o número para cada um voltar ao que tinha."
                ),
                on_change=_on_lote,
            )
            if wid not in st.session_state:
                opts["value"] = None
            st.number_input(sec["hint"], **opts)

    if locked:
        return out

    mudou = False
    for sec in GRID_SECTIONS:
        wid = f"{state_key}_lote_{sec['id']}"
        raw = st.session_state.get(wid)
        cur = float(raw) if raw is not None and float(raw) > 0 else None
        old = prev.get(sec["id"])
        key = sec["lote_key"]
        tol = 0.51 if sec["kind"] in ("int", "money") else 0.05
        if cur is not None:
            if sec["id"] not in bak:
                bak[sec["id"]] = snapshot_lote_coluna(out, key)
            if cur != old or not coluna_confere_lote(out, key, cur, tol):
                out = aplicar_lote_coluna(out, key, cur, taxa)
                st.session_state["metas_toast"] = (
                    f"{sec['label']}: {cur:g} aplicado em todos. "
                    "Apague o campo para voltar ao que cada um tinha."
                )
                mudou = True
            prev[sec["id"]] = cur
        elif old is not None:
            out = restaurar_lote_coluna(
                out, key, bak.pop(sec["id"], {}), float(old), taxa
            )
            prev[sec["id"]] = None
            st.session_state["metas_toast"] = (
                f"{sec['label']}: lote apagado; cada um voltou ao valor anterior."
            )
            mudou = True
    if mudou:
        st.session_state[state_key] = out
        st.session_state[f"{state_key}_nonce"] = int(
            st.session_state.get(f"{state_key}_nonce", 0)
        ) + 1
        st.session_state[f"{state_key}_grid_wins"] = "server_wins"
        st.session_state.pop(f"{state_key}_agdf", None)
        st.session_state.pop(f"{state_key}_semdf", None)
        st.session_state.pop(f"{state_key}_lote_tick", None)
        st.rerun(scope="fragment")
    return out


def render_equipe_grid(
    state_rows: list[dict],
    ano: int,
    mes: int,
    taxa: float,
    state_key: str,
    locked: bool = False,
    ctx: dict | None = None,
    tips: bool = True,
) -> None:
    height = GRID_VIEW_HEIGHT
    nonce = int(st.session_state.get(f"{state_key}_nonce", 0))
    grid_key = f"{state_key}_ag{'_ro' if locked else ''}{nonce or ''}_nav8"
    editor_key = f"{state_key}_ed"
    sync = st.session_state.pop(f"{state_key}_grid_wins", "client_wins")

    ag_df = rows_to_aggrid_df(state_rows)
    with st.container(key=f"equipe_aggrid_{nonce}"):
        ag = _try_aggrid(
            ag_df,
            height,
            grid_key,
            locked=locked,
            ctx=ctx,
            tips=tips,
            server_sync=sync,
        )
    if ag is not None:
        st.session_state[f"{state_key}_agdf"] = ag
        return

    editor_df = rows_to_editor_df(state_rows)
    edited = _streamlit_editor(editor_df, height, editor_key, taxa)
    st.session_state[f"{state_key}_agdf"] = edited
