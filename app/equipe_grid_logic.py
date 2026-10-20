from __future__ import annotations

import pandas as pd

from app.data import (
    crescimento_ticket_lote,
    load_carteira_ativos,
    load_metricas_vendedor_trimestre,
    load_oportunidades_rotas_equipe,
)
from app.indicadores_vendedor import calc_indicadores_3m
from app.meta_arredondamento import (
    sugerir_pct_meta,
    sugerir_recorrencia_meta,
    ticket_sugerido_crescimento,
)
from app.meta_frigosol import montar_bloco_frigosol
from app.premissas import PremissaVendedor, get_premissa, vendedor_tem_premissa

# Chaves internas → rótulos iguais à aba PAINEL (Frigosol)
EDITABLE_KEYS = (
    "conv_meta_pct",
    "tx_conv_projetada_pct",
    "ticket_meta",
    "recorrencia_meta",
    "positivacao_meta",
    "meta_manual",
)

EDITABLE_LABELS = {
    "conv_meta_pct": "Conversão manual",
    "tx_conv_projetada_pct": "% Ativação manual",
    "ticket_meta": "Ticket médio manual",
    "recorrencia_meta": "Recorrência manual",
    "positivacao_meta": "Positivação manual",
    "meta_manual": "Faturamento manual",
}

# Campos ASCII no AgGrid (evita bug de JS com "." e acentos nos nomes de coluna)
AGGRID_FIELD_LABELS: tuple[tuple[str, str], ...] = (
    ("vid", "Cód."),
    ("aj_info", "Origem do ajuste"),
    ("tk_info", "Cálculo ticket sugerido"),
    ("colab", "Colaborador"),
    ("cart", "Carteira"),
    ("tx_cob_hist", "% Ativação média"),
    ("tx_proj_sug", "% Ativação sugerida"),
    ("tx_proj", "% Ativação manual"),
    ("cob", "Cobertura calculada"),
    ("oport", "Oportunidades"),
    ("tx_oport", "Conversão média"),
    ("conv_sug", "Conversão sugerida"),
    ("conv", "Conversão manual"),
    ("oport_calc", "Oportunidades calculadas"),
    ("pos_media", "Positivação média"),
    ("pos_sug", "Positivação sugerida"),
    ("pos", "Positivação manual"),
    ("rec_media", "Recorrência média"),
    ("rec_sug", "Recorrência sugerida"),
    ("rec", "Recorrência manual"),
    ("ticket_hist", "Ticket médio (hist.)"),
    ("ticket_sug", "Ticket médio sugerido"),
    ("ticket", "Ticket médio manual"),
    ("fat_media", "Faturamento médio"),
    ("meta_calc", "Faturamento sugerido"),
    ("meta_man", "Faturamento manual"),
    ("peso_3m", "Peso fat. 3m %"),
    ("meta_prop", "Meta automática"),
    ("ajuste", "Ajuste %"),
    ("meta_final", "Meta do mês"),
    ("realizado", "Realizado (mês)"),
    ("cob_media", "Cobertura média"),
    ("dif_cob", "Dif. cart. × cob."),
    ("meta_prop_sem", "Meta autom. semana"),
    ("meta_prop_dia", "Meta autom. dia útil"),
    ("pos_prop", "Posit. sugeridas"),
    ("cob_prop", "Cobertura sugerida"),
)
AGGRID_HIDDEN_FIELDS = frozenset(
    {
        "vid",
        "aj_info",
        "tk_info",
        "cob_media",
        "dif_cob",
        "meta_prop_sem",
        "meta_prop_dia",
        "pos_prop",
        "cob_prop",
    }
)

AGGRID_LABEL_TO_FIELD = {lbl: fld for fld, lbl in AGGRID_FIELD_LABELS}
AGGRID_EDITABLE_FIELDS = frozenset({"conv", "tx_proj", "ticket", "rec", "pos", "meta_man"})
AGGRID_KEY_TO_FIELD = {
    "conv_meta_pct": "conv",
    "tx_conv_projetada_pct": "tx_proj",
    "ticket_meta": "ticket",
    "recorrencia_meta": "rec",
    "positivacao_meta": "pos",
    "meta_manual": "meta_man",
}

# Guia acima da grade: salto para o bloco + lote na coluna azul da seção.
GRID_SECTIONS: tuple[dict, ...] = (
    {
        "id": "ativacao",
        "label": "Ativação",
        "jump": "cart",
        "lote_key": "tx_conv_projetada_pct",
        "kind": "pct",
        "hint": "Aplica a ativação manual em todos.",
    },
    {
        "id": "conversao",
        "label": "Conversão",
        "jump": "oport",
        "lote_key": "conv_meta_pct",
        "kind": "pct",
        "hint": "Aplica a conversão manual em todos.",
    },
    {
        "id": "positivacao",
        "label": "Positivação",
        "jump": "pos_media",
        "lote_key": "positivacao_meta",
        "kind": "int",
        "hint": "Aplica a positivação manual em todos.",
    },
    {
        "id": "recorrencia",
        "label": "Recorrência",
        "jump": "rec_media",
        "lote_key": "recorrencia_meta",
        "kind": "rec",
        "hint": "Aplica a recorrência manual em todos.",
    },
    {
        "id": "ticket",
        "label": "Ticket",
        "jump": "ticket_hist",
        "lote_key": "ticket_meta",
        "kind": "money",
        "hint": "Aplica o ticket manual em todos.",
    },
    {
        "id": "faturamento",
        "label": "Faturamento",
        "jump": "fat_media",
        "lote_key": "meta_manual",
        "kind": "money",
        "hint": "Aplica o faturamento manual em todos.",
    },
)

GRID_VIEW_HEIGHT = 520


def _oport_rotas(vendedor_id: int) -> int | None:
    df = load_oportunidades_rotas_equipe()
    row = df.loc[df["vendedor"] == vendedor_id]
    if row.empty:
        return None
    return int(row.iloc[0]["oportunidades_mes"])


def _f(row: dict, key: str) -> float:
    v = row.get(key)
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def premissa_tem_prescricao(prem: PremissaVendedor) -> bool:
    return (
        prem.oportunidades_mes > 0
        or prem.conversao_meta_pct > 0
        or prem.tx_conv_projetada_pct > 0
        or prem.cobertura_meta_pct > 0
        or prem.ticket_meta > 0
        or prem.meta_recorrencia > 0
        or prem.meta_positivacao > 0
        or (prem.usar_meta_oficial_rs and prem.meta_faturamento_rs > 0)
    )


def aplicar_premissa_salva(row: dict, ano: int, mes: int, taxa: float) -> dict:
    """Mescla premissa gravada no Início (para Colaboradores / motor)."""
    vid = int(row["vendedor"])
    if not vendedor_tem_premissa(vid, ano, mes):
        return dict(row)
    prem = get_premissa(vid, ano, mes)
    if not premissa_tem_prescricao(prem):
        return dict(row)
    out = dict(row)
    out["conv_meta_pct"] = float(prem.conversao_meta_pct)
    tx = prem.tx_conv_projetada_pct or prem.cobertura_meta_pct
    out["tx_conv_projetada_pct"] = float(tx)
    out["oport_meta"] = float(prem.oportunidades_mes)
    out["ticket_meta"] = float(prem.ticket_meta)
    out["recorrencia_meta"] = float(prem.meta_recorrencia)
    out["positivacao_meta"] = float(prem.meta_positivacao)
    if prem.usar_meta_oficial_rs and prem.meta_faturamento_rs > 0:
        out["meta_manual"] = float(prem.meta_faturamento_rs)
    else:
        out["meta_manual"] = 0.0
    return recalc_row_formulas_only(out, taxa)


def premissa_from_row(row: dict) -> PremissaVendedor:
    manual = _f(row, "meta_manual")
    tx_proj = _f(row, "tx_conv_projetada_pct")
    return PremissaVendedor(
        oportunidades_mes=_f(row, "oport_meta"),
        conversao_meta_pct=_f(row, "conv_meta_pct"),
        tx_conv_projetada_pct=tx_proj,
        cobertura_meta_pct=tx_proj,
        ticket_meta=_f(row, "ticket_meta"),
        meta_recorrencia=_f(row, "recorrencia_meta"),
        meta_positivacao=_f(row, "positivacao_meta"),
        meta_faturamento_rs=manual,
        usar_meta_oficial_rs=manual > 0,
        taxa_cobertura=0.9,
    )


def _apply_bloco_to_row(out: dict, bloco) -> dict:
    out["oport_calc_pos"] = bloco.oport_calc_positivacao
    out["posit_meta"] = bloco.positivacoes_meta
    out["cobertura_meta_clientes"] = bloco.cobertura_meta
    out["diff_carteira_cob"] = bloco.diff_carteira_cobertura
    out["meta_formula"] = bloco.meta_formula
    out["meta_efetiva"] = bloco.meta_faturamento
    out["positivacao_media_3m"] = bloco.positivacao_media_3m
    out["faturamento_media_3m"] = bloco.faturamento_media_3m
    out["recorrencia_media"] = bloco.recorrencia_media
    out["ticket_historico"] = bloco.ticket_historico
    out["tx_conv_hist_pct"] = bloco.tx_conv_oport_hist * 100.0
    out["cob_media_clientes_3m"] = bloco.cobertura_media_3m
    if out.get("carteira", 0) > 0:
        out["cobertura_hist_pct"] = bloco.cobertura_media_3m / out["carteira"] * 100.0
    return out


SUGESTAO_KEYS = {
    "conv_meta_pct": "conv_sugerido",
    "tx_conv_projetada_pct": "tx_proj_sugerido",
    "ticket_meta": "ticket_sugerido",
    "recorrencia_meta": "rec_sugerido",
    "positivacao_meta": "pos_sugerido",
}


def valor_efetivo(row: dict, key: str) -> float:
    """Valor digitado (azul) ou, se vazio, a sugestão (dourado)."""
    return _f(row, key) or _f(row, SUGESTAO_KEYS.get(key, ""))


def ticket_efetivo(row: dict) -> float:
    return valor_efetivo(row, "ticket_meta")


def aplicar_sugestoes(row: dict, taxa: float) -> dict:
    """Sugestões a partir do histórico de cada um (usadas quando o azul fica vazio)."""
    default_tx = round(taxa * 100.0, 0) if taxa > 0 else 90.0
    row["conv_sugerido"] = sugerir_pct_meta(_f(row, "tx_conv_hist_pct"))
    hist_cob = _f(row, "cobertura_hist_pct")
    row["tx_proj_sugerido"] = sugerir_pct_meta(hist_cob) if hist_cob > 0 else default_tx
    row["rec_sugerido"] = sugerir_recorrencia_meta(_f(row, "recorrencia_media"))
    return row


def limpar_insercoes(rows: list[dict], taxa: float) -> list[dict]:
    """Esvazia as colunas azuis: tudo passa a usar as sugestões e a meta automática."""
    out = []
    for r in rows:
        x = dict(r)
        for k in EDITABLE_KEYS:
            x[k] = 0.0
        for i in range(1, 6):
            x[f"peso_sem_man_{i}"] = 0.0
        out.append(recalc_row_formulas_only(x, taxa))
    return out


def recalc_row_formulas_only(row: dict, taxa: float) -> dict:
    """Só fórmulas da planilha — sem consulta ao banco (edição na grade)."""
    out = aplicar_sugestoes(dict(row), taxa)
    cart = int(out.get("carteira") or 0)
    oport = int(out.get("oportunidades_mes") or 0)
    conv = valor_efetivo(out, "conv_meta_pct")
    txp = valor_efetivo(out, "tx_conv_projetada_pct")
    ticket = ticket_efetivo(out)
    rec = valor_efetivo(out, "recorrencia_meta")
    manual = _f(out, "meta_manual")

    cob = round(cart * txp / 100.0) if txp > 0 and cart > 0 else 0
    if cart > 0 and cob > cart:
        cob = cart
    out["oport_calc_pos"] = round(oport * conv / 100.0) if conv > 0 and oport > 0 else 0
    out["pos_sugerido"] = round(cob * rec) if cob > 0 and rec > 0 else 0
    out["posit_meta"] = valor_efetivo(out, "positivacao_meta")
    out["cobertura_meta_clientes"] = cob
    out["diff_carteira_cob"] = max(cart - cob, 0) if cob > 0 else 0
    if ticket > 0 and rec > 0 and cob > 0:
        out["meta_formula"] = round(ticket * rec * cob)
    else:
        out["meta_formula"] = 0
    out["meta_efetiva"] = manual if manual > 0 else out["meta_formula"]
    return out


def recalc_row_derivados(row: dict, ano: int, mes: int, taxa: float) -> dict:
    vid = int(row["vendedor"])
    cart = int(row.get("carteira") or load_carteira_ativos(vid))
    hist = load_metricas_vendedor_trimestre(vid, ano, mes)
    oport_rotas = _oport_rotas(vid)
    prem = premissa_from_row(row)
    bloco = montar_bloco_frigosol(
        cart,
        hist,
        prem,
        taxa,
        int(_f(row, "clientes_mes")) or None,
        oportunidades_rotas=oport_rotas,
    )
    out = dict(row)
    out["carteira"] = cart
    out["oportunidades_mes"] = bloco.oportunidades_mes
    out = _apply_bloco_to_row(out, bloco)
    return recalc_row_formulas_only(out, taxa)


def _loader_num(r: dict, key: str, default: float = 0.0) -> float:
    v = r.get(key)
    if v is None:
        return default
    try:
        if pd.isna(v):
            return default
    except (TypeError, ValueError):
        pass
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def row_from_loader(r: dict, ano: int, mes: int, taxa: float) -> dict:
    vid = int(r["vendedor"])
    cart = int(r["carteira"])
    oport_rotas = _oport_rotas(vid)
    ind = calc_indicadores_3m(vid, ano, mes, cart, oport_rotas)

    base = {
        "vendedor": vid,
        "nome": r["nome"],
        "carteira": cart,
        "clientes_mes": int(r.get("clientes_mes") or 0),
        "oportunidades_mes": ind["oportunidades_mes"],
        "tx_conv_hist_pct": ind["tx_conv_oport_hist_pct"],
        "conv_meta_pct": _loader_num(r, "conv_meta_pct"),
        "cob_media_clientes_3m": ind["cobertura_media_clientes_3m"],
        "cobertura_hist_pct": ind["cobertura_hist_pct"],
        "tx_conv_projetada_pct": _loader_num(r, "tx_conv_projetada_pct"),
        "ticket_historico": ind["ticket_historico"],
        "ticket_meta": _loader_num(r, "ticket_meta"),
        "fat_media_3m": ind["faturamento_media_3m"],
        "positivacao_media_3m": ind["positivacao_media_3m"],
        "recorrencia_media": ind["recorrencia_media"],
        "recorrencia_meta": _loader_num(r, "recorrencia_meta"),
        "positivacao_meta": _loader_num(r, "positivacao_meta"),
        "oport_meta": _loader_num(r, "oport_meta"),
        "meta_manual": _loader_num(r, "meta_manual"),
        "realizado_mes": float(r["realizado_mes"]),
        "participacao_empresa": r.get("participacao_empresa"),
    }
    por_vend, cresc_eq = crescimento_ticket_lote(ano, mes)
    tk_a, tk_b = por_vend.get(vid, (0.0, 0.0))
    sug, g, origem = ticket_sugerido_crescimento(ind["ticket_historico"], tk_a, tk_b, cresc_eq)
    base["ticket_sugerido"] = sug
    base["ticket_sug_pct"] = round(g * 100, 1)
    base["ticket_sug_origem"] = origem
    base["ticket_ano_ant"] = tk_b
    out = recalc_row_derivados(base, ano, mes, taxa)
    return aplicar_premissa_salva(out, ano, mes, taxa)


def loader_rows_to_state(df: pd.DataFrame, ano: int, mes: int, taxa: float) -> list[dict]:
    return [row_from_loader(r.to_dict(), ano, mes, taxa) for _, r in df.iterrows()]


def editable_fields_changed(prev: list[dict], new: list[dict]) -> bool:
    n = min(len(prev), len(new))
    for i in range(n):
        for k in EDITABLE_KEYS:
            if _f(prev[i], k) != _f(new[i], k):
                return True
    return False


def _media_preenchidos(col) -> float:
    """Média só de quem preencheu (vazio/0 não puxa a média para baixo)."""
    if col is None:
        return 0.0
    vals = pd.to_numeric(col, errors="coerce")
    vals = vals[vals > 0]
    return float(vals.mean()) if len(vals) else 0.0


def total_row_from_aggrid_df(df: pd.DataFrame) -> dict:
    """Linha TOTAL para grade AgGrid (campos ASCII)."""
    if df.empty:
        return {}
    d = df[df["colab"].astype(str).str.upper() != "TOTAL"].copy()
    if d.empty:
        return {}

    def _sum(col: str) -> float:
        if col not in d.columns:
            return 0.0
        return float(pd.to_numeric(d[col], errors="coerce").fillna(0).sum())

    def _ef(row, col: str) -> float:
        for c in (col, f"{col}_sug"):
            v = row.get(c)
            if v is not None and not pd.isna(v) and str(v) != "":
                try:
                    return float(v)
                except (TypeError, ValueError):
                    return 0.0
        return 0.0

    def _cob_row(row) -> float:
        txp = _ef(row, "tx_proj")
        cart = float(row.get("cart") or 0)
        return round(cart * txp / 100.0) if txp > 0 and cart > 0 else 0.0

    def _sum_calc_oport() -> float:
        return sum(round(float(r.get("oport") or 0) * _ef(r, "conv") / 100.0) for _, r in d.iterrows())

    def _sum_calc_cob() -> float:
        return sum(_cob_row(r) for _, r in d.iterrows())

    def _sum_dif() -> float:
        total = 0.0
        for _, row in d.iterrows():
            cob = _cob_row(row)
            if cob > 0:
                total += max(float(row.get("cart") or 0) - cob, 0.0)
        return total

    def _sum_meta_calc() -> float:
        total = 0.0
        for _, row in d.iterrows():
            cob = _cob_row(row)
            ticket, rec = _ef(row, "ticket"), _ef(row, "rec")
            if cob > 0 and ticket > 0 and rec > 0:
                total += round(ticket * rec * cob)
        return total

    def _media_ef(col: str) -> float:
        vals = [v for v in (_ef(r, col) for _, r in d.iterrows()) if v > 0]
        return sum(vals) / len(vals) if vals else 0.0

    cart = _sum("cart")
    oport = _sum("oport")
    oport_calc = _sum_calc_oport()
    cob_media = _sum("cob_media")
    cob = _sum_calc_cob()
    dif = _sum_dif()
    fat = _sum("fat_media")
    pos = _sum("pos_media")
    meta = _sum_meta_calc()
    real = _sum("realizado")
    auto_tot = _sum("meta_prop")
    man_col = pd.to_numeric(d.get("meta_man"), errors="coerce").fillna(0)
    auto_col = pd.to_numeric(d.get("meta_prop"), errors="coerce").fillna(0)
    final_tot = float(man_col.where(man_col > 0, auto_col).sum())

    tx_oport = (pos / oport * 100.0) if oport > 0 else 0.0
    conv_media = _media_ef("conv")
    tx_cob_media = (cob_media / cart * 100.0) if cart > 0 else 0.0
    tx_proj = _media_ef("tx_proj")

    return {
        "vid": None,
        "aj_info": "",
        "colab": "TOTAL",
        "cart": int(round(cart)),
        "oport": int(round(oport)),
        "tx_oport": round(tx_oport, 2),
        "conv": round(conv_media, 0) if conv_media else None,
        "oport_calc": int(round(oport_calc)),
        "cob_media": int(round(cob_media)),
        "tx_proj": round(tx_proj, 0) if tx_proj else None,
        "cob": int(round(cob)),
        "dif_cob": int(round(dif)),
        "tx_cob_hist": round(tx_cob_media, 2),
        "fat_media": round(fat, 0),
        "pos_media": int(round(pos)),
        "pos_sug": int(round(sum(
            _cob_row(r) * _ef(r, "rec") for _, r in d.iterrows()
            if _cob_row(r) > 0 and _ef(r, "rec") > 0
        ))),
        "pos": None,
        "ticket_hist": None,
        "ticket": None,
        "ticket_sug": None,
        "tk_info": "",
        "conv_sug": None,
        "tx_proj_sug": None,
        "rec_sug": None,
        "rec_media": None,
        "rec": None,
        "peso_3m": round(_sum("peso_3m"), 2) if "peso_3m" in d.columns else None,
        "meta_prop": round(_sum("meta_prop"), 0),
        "meta_prop_sem": round(_sum("meta_prop_sem"), 0),
        "meta_prop_dia": round(_sum("meta_prop_dia"), 0),
        "pos_prop": int(round(_sum("pos_prop"))),
        "cob_prop": int(round(_sum("cob_prop"))),
        "meta_calc": round(meta, 0),
        "meta_man": None,
        "ajuste": round((final_tot / auto_tot - 1) * 100, 1) if auto_tot > 0 else None,
        "meta_final": round(final_tot, 0),
        "realizado": round(real, 0),
    }


def total_row_from_editor_df(df: pd.DataFrame) -> dict:
    """Linha TOTAL estilo planilha (somas + taxas ponderadas)."""
    if df.empty:
        return {}
    d = df[df["Colaborador"].astype(str).str.upper() != "TOTAL"].copy()
    if d.empty:
        return {}

    def _sum(col: str) -> float:
        if col not in d.columns:
            return 0.0
        return float(pd.to_numeric(d[col], errors="coerce").fillna(0).sum())

    cart = _sum("Carteira")
    oport = _sum("Oportunidades")
    oport_calc = _sum("Oport. calc.")
    cob_media = _sum("Cobertura média")
    cob = _sum("Cobertura")
    dif = _sum("Dif. cart. × cob.")
    fat = _sum("Fat. média")
    pos = _sum("Positivação média")
    meta = _sum("Meta calc.")
    real = _sum("Realizado (mês)")

    tx_oport = (pos / oport * 100.0) if oport > 0 else 0.0
    conv_media = _media_preenchidos(d.get("Conversão"))
    tx_cob_media = (cob_media / cart * 100.0) if cart > 0 else 0.0
    tx_proj = _media_preenchidos(d.get("TX conv. projetada"))

    return {
        "Colaborador": "TOTAL",
        "Carteira": int(round(cart)),
        "Oportunidades": int(round(oport)),
        "TX conv. oport.": round(tx_oport, 2),
        "Conversão": round(conv_media, 0) if conv_media else None,
        "Oport. calc.": int(round(oport_calc)),
        "Cobertura média": int(round(cob_media)),
        "TX conv. (média)": round(tx_cob_media, 2),
        "TX conv. projetada": round(tx_proj, 0) if tx_proj else None,
        "Cobertura": int(round(cob)),
        "Dif. cart. × cob.": int(round(dif)),
        "Fat. média": round(fat, 0),
        "Positivação média": int(round(pos)),
        "Ticket histórico": None,
        "Ticket médio": None,
        "Recorrência média": None,
        "Recorrência": None,
        "Meta calc.": round(meta, 0),
        "Meta manual (R$)": None,
        "Realizado (mês)": round(real, 0),
    }


def grid_totals(rows: list[dict]) -> dict[str, float]:
    meta_calc = sum(_f(r, "meta_formula") for r in rows)
    meta_man = sum(_f(r, "meta_manual") for r in rows if _f(r, "meta_manual") > 0)
    realizado = sum(_f(r, "realizado_mes") for r in rows)
    return {
        "meta_calc": meta_calc,
        "meta_manual": meta_man,
        "realizado": realizado,
        "colaboradores": float(len(rows)),
    }


def aplicar_lote_coluna(rows: list[dict], key: str, valor: float, taxa: float) -> list[dict]:
    """Preenche a coluna azul da seção em todos os colaboradores."""
    if key not in EDITABLE_KEYS:
        return rows
    out = []
    for r in rows:
        x = dict(r)
        x[key] = float(valor)
        out.append(recalc_row_formulas_only(x, taxa))
    return out


def coluna_confere_lote(rows: list[dict], key: str, valor: float, tol: float = 0.05) -> bool:
    """True se todo mundo já está com o azul do lote."""
    if not rows:
        return True
    v = float(valor)
    return all(abs(_f(r, key) - v) < tol for r in rows)


def snapshot_lote_coluna(rows: list[dict], key: str) -> dict[int, float]:
    """Guarda o azul de cada um (0 = estava na sugestão) para poder desfazer o lote."""
    return {int(r["vendedor"]): _f(r, key) for r in rows}


def restaurar_lote_coluna(
    rows: list[dict],
    key: str,
    bak: dict[int, float],
    lote_val: float,
    taxa: float,
) -> list[dict]:
    """Apagou o lote: volta o manual anterior, ou a sugestão se o azul estava vazio."""
    if key not in EDITABLE_KEYS:
        return rows
    out = []
    for r in rows:
        x = dict(r)
        atual = _f(x, key)
        if lote_val > 0 and abs(atual - lote_val) >= 0.05:
            out.append(recalc_row_formulas_only(x, taxa))
            continue
        x[key] = float(bak.get(int(x["vendedor"]), 0.0))
        out.append(recalc_row_formulas_only(x, taxa))
    return out


def fill_column_down_rows(
    rows: list[dict],
    col: str,
    from_index: int,
    ano: int,
    mes: int,
    taxa: float,
) -> list[dict]:
    if col not in EDITABLE_KEYS or from_index < 0 or from_index >= len(rows):
        return rows
    out = [dict(x) for x in rows]
    val = out[from_index].get(col)
    for i in range(from_index + 1, len(out)):
        out[i][col] = val
        out[i] = recalc_row_formulas_only(out[i], taxa)
    return out


def sync_edited_rows(
    prev: list[dict],
    patched: list[dict],
    ano: int,
    mes: int,
    taxa: float,
) -> list[dict]:
    del prev, ano, mes
    return [recalc_row_formulas_only(dict(p), taxa) for p in patched]


def rows_to_editor_df(rows: list[dict]) -> pd.DataFrame:
    data = []
    for r in rows:
        vid = int(r["vendedor"])
        nome = str(r["nome"])
        cart = int(r["carteira"])
        data.append(
            {
                "Colaborador": f"{vid:03d} · {nome}"[:44],
                "Carteira": cart,
                "Oportunidades": int(r["oportunidades_mes"]),
                "TX conv. oport.": round(_f(r, "tx_conv_hist_pct"), 2),
                EDITABLE_LABELS["conv_meta_pct"]: (
                    round(_f(r, "conv_meta_pct"), 0) or None
                ),
                "Oport. calc.": (
                    int(round(_f(r, "oport_calc_pos")))
                    if _f(r, "conv_meta_pct") > 0
                    else None
                ),
                "Cobertura média": round(_f(r, "cob_media_clientes_3m"), 0),
                "TX conv. (média)": round(_f(r, "cobertura_hist_pct"), 2),
                EDITABLE_LABELS["tx_conv_projetada_pct"]: (
                    round(_f(r, "tx_conv_projetada_pct"), 0) or None
                ),
                "Cobertura": (
                    int(_f(r, "cobertura_meta_clientes"))
                    if _f(r, "tx_conv_projetada_pct") > 0
                    else None
                ),
                "Dif. cart. × cob.": (
                    int(_f(r, "diff_carteira_cob"))
                    if _f(r, "tx_conv_projetada_pct") > 0
                    else None
                ),
                "Fat. média": round(_f(r, "faturamento_media_3m"), 0),
                "Positivação média": round(_f(r, "positivacao_media_3m"), 0),
                EDITABLE_LABELS["positivacao_meta"]: (
                    round(_f(r, "positivacao_meta"), 0) or None
                ),
                "Ticket histórico": round(_f(r, "ticket_historico"), 0),
                EDITABLE_LABELS["ticket_meta"]: round(_f(r, "ticket_meta"), 0) or None,
                "Recorrência média": round(_f(r, "recorrencia_media"), 1),
                EDITABLE_LABELS["recorrencia_meta"]: (
                    round(_f(r, "recorrencia_meta"), 1) or None
                ),
                "Peso fat. 3m %": _f(r, "peso_fat_3m_pct") or None,
                "Meta prop. mês": round(_f(r, "meta_prop_mes_rs"), 0) or None,
                "Meta prop. sem.": round(_f(r, "meta_prop_sem_rs"), 0) or None,
                "Meta prop. dia útil": round(_f(r, "meta_prop_dia_rs"), 0) or None,
                "Posit. sug. prop.": (
                    int(r["posit_prop_sug"])
                    if r.get("posit_prop_sug") is not None
                    else None
                ),
                "Cobert. sug. prop.": (
                    int(r["cob_prop_sug"])
                    if r.get("cob_prop_sug") is not None
                    else None
                ),
                "Meta calc.": (
                    round(_f(r, "meta_formula"), 0)
                    if _f(r, "ticket_meta") > 0
                    and _f(r, "recorrencia_meta") > 0
                    and _f(r, "tx_conv_projetada_pct") > 0
                    else None
                ),
                EDITABLE_LABELS["meta_manual"]: round(_f(r, "meta_manual"), 0) or None,
                "Realizado (mês)": round(_f(r, "realizado_mes"), 0),
            }
        )
    return pd.DataFrame(data)


def _ticket_info(r: dict) -> str:
    hist = _f(r, "ticket_historico")
    sug = _f(r, "ticket_sugerido")
    if hist <= 0 or sug <= 0:
        return "Sem histórico de ticket nos 3 meses fechados."
    pct = _f(r, "ticket_sug_pct")
    origem = r.get("ticket_sug_origem")
    rs = lambda v: "R$ " + f"{v:,.0f}".replace(",", ".")
    if origem == "colaborador":
        base = (
            f"Ticket dos 3 meses fechados ({rs(hist)}) vs mesmos meses do ano passado "
            f"({rs(_f(r, 'ticket_ano_ant'))})"
        )
    elif origem == "equipe":
        base = "Sem histórico do ano passado: usa o crescimento do ticket da equipe"
    else:
        base = "Sem comparação disponível: usa o piso"
    p = f"{pct:.1f}".replace(".", ",")
    return (
        f"{base}. Crescimento aplicado: +{p}% (mín. +2%, máx. +15%). "
        f"{rs(hist)} × (1 + {p}%) = {rs(sug)}. Deixe o azul vazio para usar este valor."
    )


def rows_to_aggrid_df(rows: list[dict]) -> pd.DataFrame:
    data = []
    for r in rows:
        vid = int(r["vendedor"])
        nome = str(r["nome"])
        cart = int(r["carteira"])
        conv = _f(r, "conv_meta_pct")
        txp = _f(r, "tx_conv_projetada_pct")
        ticket = _f(r, "ticket_meta")
        rec = _f(r, "recorrencia_meta")
        pos_man = _f(r, "positivacao_meta")
        conv_ef = valor_efetivo(r, "conv_meta_pct")
        txp_ef = valor_efetivo(r, "tx_conv_projetada_pct")
        tk_ef = ticket_efetivo(r)
        rec_ef = valor_efetivo(r, "recorrencia_meta")
        cob_val = int(_f(r, "cobertura_meta_clientes")) if txp_ef > 0 and cart > 0 else None
        ocalc = int(round(_f(r, "oport_calc_pos"))) if conv_ef > 0 else None
        dif_val = int(_f(r, "diff_carteira_cob")) if txp_ef > 0 and cart > 0 else None
        meta_c = (
            int(round(_f(r, "meta_formula")))
            if tk_ef > 0 and rec_ef > 0 and txp_ef > 0 and cart > 0
            else None
        )
        auto = round(_f(r, "meta_prop_mes_rs"), 0)
        man = round(_f(r, "meta_manual"), 0)
        final = man if man > 0 else auto
        data.append(
            {
                "vid": vid,
                "aj_info": _ajuste_info(r),
                "colab": f"{vid:03d} · {nome}"[:44],
                "cart": cart,
                "oport": int(r["oportunidades_mes"]),
                "tx_oport": round(_f(r, "tx_conv_hist_pct"), 2),
                "conv": round(conv, 0) if conv > 0 else None,
                "oport_calc": ocalc,
                "cob_media": round(_f(r, "cob_media_clientes_3m"), 0),
                "tx_cob_hist": round(_f(r, "cobertura_hist_pct"), 2),
                "tx_proj": round(txp, 0) if txp > 0 else None,
                "cob": cob_val,
                "dif_cob": dif_val,
                "fat_media": round(_f(r, "faturamento_media_3m"), 0),
                "pos_media": round(_f(r, "positivacao_media_3m"), 0),
                "pos_sug": int(_f(r, "pos_sugerido")) or None,
                "pos": round(pos_man, 0) or None,
                "ticket_hist": round(_f(r, "ticket_historico"), 0),
                "ticket": round(ticket, 0) or None,
                "ticket_sug": round(_f(r, "ticket_sugerido"), 0) or None,
                "tk_info": _ticket_info(r),
                "rec_media": round(_f(r, "recorrencia_media"), 1),
                "rec": round(rec, 1) or None,
                "conv_sug": round(_f(r, "conv_sugerido"), 0) or None,
                "tx_proj_sug": round(_f(r, "tx_proj_sugerido"), 0) or None,
                "rec_sug": round(_f(r, "rec_sugerido"), 1) or None,
                "peso_3m": _f(r, "peso_fat_3m_pct") or None,
                "meta_prop": auto or None,
                "meta_prop_sem": round(_f(r, "meta_prop_sem_rs"), 0) or None,
                "meta_prop_dia": round(_f(r, "meta_prop_dia_rs"), 0) or None,
                "pos_prop": (
                    int(r["posit_prop_sug"])
                    if r.get("posit_prop_sug") is not None
                    else None
                ),
                "cob_prop": (
                    int(r["cob_prop_sug"])
                    if r.get("cob_prop_sug") is not None
                    else None
                ),
                "meta_calc": meta_c,
                "meta_man": man or None,
                "ajuste": round((final / auto - 1) * 100, 1) if auto > 0 and man > 0 else None,
                "meta_final": final or None,
                "realizado": round(_f(r, "realizado_mes"), 0),
            }
        )
    cols = [fld for fld, _ in AGGRID_FIELD_LABELS]
    return pd.DataFrame(data, columns=cols)


def _ajuste_info(r: dict) -> str:
    from app.constants import MESES_NOME

    origem = r.get("ajuste_origem")
    mes_o = r.get("ajuste_mes_origem")
    if origem == "herdado" and mes_o:
        return f"Ajuste de {MESES_NOME[int(mes_o)]} (deste mês em diante)."
    if origem == "salvo" and abs(_f(r, "ajuste_plano_pct")) >= 0.05:
        return "Ajuste salvo neste mês."
    return ""


def meta_final_row(r: dict) -> float:
    man = _f(r, "meta_manual")
    return man if man > 0 else _f(r, "meta_prop_mes_rs")


def patch_rows_from_editor(
    prev_rows: list[dict],
    edited: pd.DataFrame,
    skip_keys: frozenset[str] | None = None,
) -> list[dict]:
    skip = skip_keys or frozenset()
    if "Colaborador" in edited.columns:
        edited = edited[edited["Colaborador"].astype(str).str.upper() != "TOTAL"].reset_index(drop=True)
    out = []
    n = min(len(prev_rows), len(edited))
    for i in range(n):
        base = dict(prev_rows[i])
        row = edited.iloc[i]
        for key, label in EDITABLE_LABELS.items():
            if key in skip:
                continue
            base[key] = _f(row, label)
        out.append(base)
    return out


def patch_rows_from_aggrid(
    prev_rows: list[dict],
    edited: pd.DataFrame,
    skip_keys: frozenset[str] | None = None,
) -> list[dict]:
    skip = skip_keys or frozenset()
    if "colab" in edited.columns:
        edited = edited[edited["colab"].astype(str).str.upper() != "TOTAL"].reset_index(drop=True)
    elif "Colaborador" in edited.columns:
        return patch_rows_from_editor(prev_rows, edited, skip)
    if "vid" in edited.columns:
        by_vid = {
            int(r["vid"]): r
            for _, r in edited.iterrows()
            if pd.notna(r.get("vid"))
        }
        out = []
        for prev in prev_rows:
            base = dict(prev)
            row = by_vid.get(int(prev["vendedor"]))
            if row is not None:
                for key, field in AGGRID_KEY_TO_FIELD.items():
                    if key in skip:
                        continue
                    base[key] = _f(row, field)
            out.append(base)
        return out
    out = []
    n = min(len(prev_rows), len(edited))
    for i in range(n):
        base = dict(prev_rows[i])
        row = edited.iloc[i]
        for key, field in AGGRID_KEY_TO_FIELD.items():
            if key in skip:
                continue
            base[key] = _f(row, field)
        out.append(base)
    return out


def rows_from_aggrid_df(
    prev_rows: list[dict],
    agdf: pd.DataFrame,
    taxa: float,
    skip_keys: frozenset[str] | None = None,
) -> list[dict]:
    if agdf is not None and "colab" in agdf.columns:
        patched = patch_rows_from_aggrid(prev_rows, agdf, skip_keys)
    else:
        patched = patch_rows_from_editor(prev_rows, agdf, skip_keys)
    return [recalc_row_formulas_only(p, taxa) for p in patched]
