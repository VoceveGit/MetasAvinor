from __future__ import annotations

import pandas as pd
import streamlit as st

import json

from app.equipe_grid_logic import (
    AGGRID_EDITABLE_FIELDS,
    AGGRID_FIELD_LABELS,
    AGGRID_HIDDEN_FIELDS,
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
    {"peso_3m", "meta_prop", "ajuste", "meta_prop_sem", "meta_prop_dia", "pos_prop", "cob_prop"}
)
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
    "cart": "Clientes ativos na carteira do colaborador. Toda meta sai de clientes que já são dele.",
    "oport": "Contatos no mês pela planilha de rotas: contatos por semana × 4, somando os clientes ativos.",
    "tx_oport": "Notas ÷ oportunidades nos 3 últimos meses fechados. De cada 100 contatos, quantos viraram nota.",
    "conv": "Você define: de cada 100 contatos, quantos precisam virar nota neste mês.",
    "oport_calc": "Oportunidades × conversão meta = notas esperadas no mês.",
    "cob_media": "Clientes diferentes que compraram por mês, em média, nos 3 últimos meses fechados.",
    "tx_cob_hist": "Cobertura média ÷ carteira. Quanto da carteira costuma comprar no mês.",
    "tx_proj": "Você define: que parte da carteira precisa comprar neste mês.",
    "cob": "Carteira × TX projetada = clientes da carteira que precisam comprar no mês.",
    "dif_cob": "Carteira − cobertura = clientes que podem ficar sem comprar sem prejudicar a meta.",
    "fat_media": "Faturamento médio por mês nos 3 últimos meses fechados.",
    "pos_media": "Notas por mês, em média (positivação = nota). Um cliente pode ter várias notas.",
    "ticket_hist": "Faturamento médio ÷ notas = valor médio de cada nota.",
    "ticket": "Você define: valor médio de cada nota neste mês. Vazio = vale o ticket sugerido (dourado).",
    "ticket_sug": (
        "Ticket histórico × (1 + crescimento do ticket dele: 3 meses fechados vs mesmos meses do "
        "ano passado). Mínimo +2%, máximo +15%; sem histórico usa a equipe. Vale quando o azul está vazio."
    ),
    "rec_media": "Notas ÷ clientes = quantos pedidos cada cliente faz no mês.",
    "rec": "Você define: notas por cliente no mês.",
    "meta_calc": "Ticket × recorrência × cobertura = meta que sai das alavancas azuis (método Frigosol).",
    "peso_3m": "Faturamento dele ÷ faturamento da equipe nos 3 meses fechados = fatia dele na meta.",
    "meta_prop": "Meta da empresa no mês × peso. Sai direto da meta anual (com ou sem sazonalidade).",
    "meta_man": "Você define, se quiser. Vazio = vale a automática. O sistema guarda a diferença em %.",
    "ajuste": "Meta do mês ÷ meta automática − 1. Quanto você colocou acima ou abaixo do automático.",
    "meta_final": "A meta que vale: a manual, se houver; senão a automática. A soma é a meta do mês.",
    "realizado": "Faturado no mês até agora.",
    "meta_prop_sem": "Meta automática ÷ dias úteis do mês × 5.",
    "meta_prop_dia": "Meta automática ÷ dias úteis do mês.",
    "pos_prop": "Notas necessárias para bater a meta automática: cobertura sugerida × recorrência.",
    "cob_prop": "Clientes necessários para a meta automática: meta ÷ (ticket histórico × recorrência).",
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
    ".ag-floating-bottom": {"borderTop": "2px solid #c4b5a0 !important"},
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
_PCT_FIELDS = frozenset({"tx_oport", "tx_cob_hist", "conv", "tx_proj", "peso_3m", "ajuste"})
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


_SUG_FIELDS = frozenset({"conv", "tx_proj", "rec"})


def _js_sug_style(base: dict):
    """Célula azul vazia: mostra a sugestão em dourado (o valor gravado continua vazio)."""
    from st_aggrid.shared import JsCode

    return JsCode(
        "function(params) {"
        f"var base = {json.dumps(base)};"
        "var v = params.value;"
        "if (params.node && params.node.rowPinned) return base;"
        "if (v === null || v === undefined || v === '') {"
        "  return Object.assign({}, base, {color: '#9a6b00', fontStyle: 'italic', fontWeight: '600'});"
        "}"
        "return base;"
        "}"
    )


def _js_grid_ready():
    from st_aggrid.shared import JsCode

    return JsCode(
        """
        function(params) {
            window.__avinorGrid = window.__avinorGrid || {};
            var g = window.__avinorGrid;
            if (g._ready !== 'v5') {
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
                return g.isSet(d.meta_prop) ? g.n(d.meta_prop) : null;
            };
            g.rowAjuste = function(d) {
                if (!d || !g.isSet(d.meta_man) || g.n(d.meta_man) <= 0) return null;
                var auto = g.n(d.meta_prop);
                if (auto <= 0) return null;
                return Math.round((g.n(d.meta_man) / auto - 1) * 1000) / 10;
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
                    meta_calc: Math.round(metaSum),
                    realizado: Math.round(s('realizado')),
                }]);
                g.refreshPinned(api);
            };
            g._ready = 'v5';
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
                columns: ['oport_calc', 'cob', 'dif_cob', 'meta_calc', 'ajuste', 'meta_final'],
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
                if (f === 'meta_final') return 'Meta do mês da equipe: ' + rs(d.meta_final) + '. Soma das metas de cada um (manual, se houver; senão automática).';
                if (f === 'ajuste') return 'Equipe: soma das metas do mês ÷ soma das automáticas − 1 = ' + pc(d.ajuste) + '.';
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
                if (!set(d.tx_proj)) return 'Vazio: vale a sugestão ' + pc(d.tx_proj_sug, 0) + ' (histórico ' + pc(d.tx_cob_hist) + ' + ~5%, em degraus de 5). Digite para usar outro valor.';
                return 'TX projetada ' + pc(d.tx_proj, 0) + ': essa parte da carteira precisa comprar no mês. Histórico: ' + pc(d.tx_cob_hist) + '.';
            case 'cob':
                if (cob === null) return 'Sem carteira ou TX para calcular.';
                return 'Carteira × TX projetada' + (set(d.tx_proj) ? '' : ' sugerida') + ' = ' + br(d.cart) + ' × ' + pc(set(d.tx_proj) ? d.tx_proj : d.tx_proj_sug, 0) + ' = ' + br(cob) + ' clientes da carteira precisam comprar no mês.';
            case 'dif_cob':
                if (cob === null) return 'Sem carteira ou TX para calcular.';
                return 'Carteira − cobertura = ' + br(d.cart) + ' − ' + br(cob) + ' = ' + br(Math.max(0, n(d.cart) - cob)) + ' clientes podem ficar sem comprar neste mês sem prejudicar a meta.';
            case 'fat_media':
                return 'Média dos 3 últimos meses fechados: ' + rs(d.fat_media) + ' por mês.';
            case 'pos_media':
                return br(d.pos_media) + ' notas por mês, em média. Um cliente pode ter várias notas no mês (recompra).';
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
                if (cob === null || !set(tkE) || !set(rcE)) return 'Sem histórico suficiente para calcular.';
                var usaSug = !set(d.ticket) || !set(d.rec) || !set(d.tx_proj);
                return 'Ticket × recorrência × cobertura = ' + rs(tkE) + ' × ' + br(rcE, 1) + ' × ' + br(cob) + ' = ' + rs(n(tkE) * n(rcE) * cob) + '.' + (usaSug ? ' Campos azuis vazios usam a sugestão (dourado).' : ' Sai das alavancas azuis.');
            case 'peso_3m':
                return 'Faturamento dele ÷ faturamento da equipe nos 3 meses fechados = ' + pc(d.peso_3m, 2) + '. É a fatia dele na meta da empresa.';
            case 'meta_prop':
                return 'Meta da empresa em ' + C.mes + ' × peso = ' + rs(C.base) + ' × ' + pc(d.peso_3m, 2) + ' = ' + rs(d.meta_prop) + '. Sai direto da meta anual.';
            case 'meta_man':
                if (!set(d.meta_man) || n(d.meta_man) <= 0) return 'Vazio = vale a automática (' + rs(d.meta_prop) + '). Se preencher, o sistema guarda a diferença em %.';
                return 'Meta manual ' + rs(d.meta_man) + ' contra a automática ' + rs(d.meta_prop) + (adj !== null ? ' (' + (adj > 0 ? '+' : '') + pc(adj) + ').' : '.') + (d.aj_info ? ' ' + d.aj_info : '');
            case 'ajuste':
                if (adj === null) return 'Sem ajuste: vale a meta automática.';
                return 'Meta do mês ÷ automática − 1 = ' + rs(fin) + ' ÷ ' + rs(d.meta_prop) + ' − 1 = ' + (adj > 0 ? '+' : '') + pc(adj) + '.' + (d.aj_info ? ' ' + d.aj_info : '');
            case 'meta_final':
                if (adj === null) return 'Sem ajuste manual: vale a automática, ' + rs(fin) + '.';
                return 'Vale a manual: ' + rs(fin) + ' (' + (adj > 0 ? '+' : '') + pc(adj) + ' sobre a automática ' + rs(d.meta_prop) + ').';
            case 'realizado':
                if (fin && fin > 0) return 'Faturado no mês: ' + rs(d.realizado) + ' = ' + pc(n(d.realizado) / fin * 100, 0) + ' da meta do mês (' + rs(fin) + ').';
                return 'Faturado no mês: ' + rs(d.realizado) + '.';
            case 'meta_prop_sem':
                return 'Meta automática ÷ dias úteis × 5 = ' + rs(d.meta_prop) + ' ÷ ' + C.uteis + ' × 5 = ' + rs(d.meta_prop_sem) + ' por semana.';
            case 'meta_prop_dia':
                return 'Meta automática ÷ dias úteis = ' + rs(d.meta_prop) + ' ÷ ' + C.uteis + ' = ' + rs(d.meta_prop_dia) + ' por dia útil.';
            case 'pos_prop':
                return br(d.pos_prop) + ' notas para bater a meta automática: ' + br(d.cob_prop) + ' clientes × recorrência.';
            case 'cob_prop':
                return 'Meta automática ÷ (ticket histórico × recorrência) = ' + rs(d.meta_prop) + ' ÷ (' + rs(d.ticket_hist) + ' × ' + br(d.rec_media, 1) + ') = ' + br(d.cob_prop) + ' clientes da carteira.';
            }
            return null;
        }
        """.replace("__CTX__", json.dumps(ctx, ensure_ascii=False))
    )


def _try_aggrid(
    df: pd.DataFrame,
    height: int,
    grid_key: str,
    locked: bool = False,
    ctx: dict | None = None,
) -> pd.DataFrame | None:
    try:
        from st_aggrid import AgGrid, DataReturnMode, GridOptionsBuilder, GridUpdateMode
        from st_aggrid.shared import JsCode
    except ImportError:
        return None

    pinned = [total_row_from_aggrid_df(df)]
    tooltip = _js_tooltip(ctx or {"mes": "", "base": 0, "uteis": 0})

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
                v = d[f + '_sug'];
            }
            if (v === null || v === undefined || v === '' || isNaN(Number(v))) return '—';
            var x = Number(v);
            return f === 'rec'
                ? x.toLocaleString('pt-BR', {minimumFractionDigits: 1, maximumFractionDigits: 1})
                : Math.round(x).toLocaleString('pt-BR') + '%';
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
            if (params.node && params.node.rowPinned) {
                return params.data ? params.data.meta_final : null;
            }
            var g = window.__avinorGrid;
            return g && g.rowFinal ? g.rowFinal(params.data) : null;
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
        elif field == "ticket_sug":
            cell_style = _GOLD
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
            "tooltipValueGetter": tooltip,
        }
        if field in _HEADER_HELP:
            opts["headerTooltip"] = _HEADER_HELP[field]
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
        elif field == "meta_final":
            opts["valueGetter"] = vg_final
        elif field == "ajuste":
            opts["valueGetter"] = vg_ajuste
        if field in AGGRID_EDITABLE_FIELDS:
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
        tooltipShowDelay=250,
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
    locked: bool = False,
    ctx: dict | None = None,
) -> None:
    height = GRID_VIEW_HEIGHT
    nonce = int(st.session_state.get(f"{state_key}_nonce", 0))
    grid_key = f"{state_key}_ag{'_ro' if locked else ''}{nonce or ''}"
    editor_key = f"{state_key}_ed"

    ag_df = rows_to_aggrid_df(state_rows)
    ag = _try_aggrid(ag_df, height, grid_key, locked=locked, ctx=ctx)
    if ag is not None:
        st.session_state[f"{state_key}_agdf"] = ag
        return

    editor_df = rows_to_editor_df(state_rows)
    edited = _streamlit_editor(editor_df, height, editor_key, taxa)
    st.session_state[f"{state_key}_agdf"] = edited
