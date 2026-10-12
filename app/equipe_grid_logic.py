from __future__ import annotations

import pandas as pd

from app.data import (
    load_carteira_ativos,
    load_metricas_vendedor_trimestre,
    load_oportunidades_rotas_equipe,
)
from app.indicadores_vendedor import calc_indicadores_3m
from app.meta_arredondamento import (
    sugerir_pct_meta,
    sugerir_recorrencia_meta,
    sugerir_ticket_meta,
    sugerir_tx_cobertura_projetada,
)
from app.meta_frigosol import montar_bloco_frigosol
from app.premissas import PremissaVendedor, get_premissa, vendedor_tem_premissa

# Chaves internas → rótulos iguais à aba PAINEL (Frigosol)
EDITABLE_KEYS = (
    "conv_meta_pct",
    "tx_conv_projetada_pct",
    "ticket_meta",
    "recorrencia_meta",
    "meta_manual",
)

EDITABLE_LABELS = {
    "conv_meta_pct": "Conversão",
    "tx_conv_projetada_pct": "TX conv. projetada",
    "ticket_meta": "Ticket médio",
    "recorrencia_meta": "Recorrência",
    "meta_manual": "Meta manual (R$)",
}

# Campos ASCII no AgGrid (evita bug de JS com "." e acentos nos nomes de coluna)
AGGRID_FIELD_LABELS: tuple[tuple[str, str], ...] = (
    ("colab", "Colaborador"),
    ("cart", "Carteira"),
    ("oport", "Oportunidades"),
    ("tx_oport", "TX conv. oport."),
    ("conv", "Conversão"),
    ("oport_calc", "Oport. calc."),
    ("cob_media", "Cobertura média"),
    ("tx_cob_hist", "TX conv. (média)"),
    ("tx_proj", "TX conv. projetada"),
    ("cob", "Cobertura"),
    ("dif_cob", "Dif. cart. × cob."),
    ("fat_media", "Fat. média"),
    ("pos_media", "Positivação média"),
    ("ticket_hist", "Ticket histórico"),
    ("ticket", "Ticket médio"),
    ("rec_media", "Recorrência média"),
    ("rec", "Recorrência"),
    ("peso_3m", "Peso fat. 3m %"),
    ("meta_prop", "Meta prop. mês"),
    ("meta_prop_sem", "Meta prop. sem."),
    ("meta_prop_dia", "Meta prop. dia útil"),
    ("pos_prop", "Posit. sug. prop."),
    ("cob_prop", "Cobert. sug. prop."),
    ("meta_calc", "Meta calc."),
    ("meta_man", "Meta manual (R$)"),
    ("realizado", "Realizado (mês)"),
)

AGGRID_LABEL_TO_FIELD = {lbl: fld for fld, lbl in AGGRID_FIELD_LABELS}
AGGRID_EDITABLE_FIELDS = frozenset({"conv", "tx_proj", "ticket", "rec", "meta_man"})
AGGRID_KEY_TO_FIELD = {
    "conv_meta_pct": "conv",
    "tx_conv_projetada_pct": "tx_proj",
    "ticket_meta": "ticket",
    "recorrencia_meta": "rec",
    "meta_manual": "meta_man",
}

GRID_VIEW_HEIGHT = 420


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
        meta_faturamento_rs=manual,
        usar_meta_oficial_rs=manual > 0,
        taxa_cobertura=0.9,
    )


def _apply_bloco_to_row(out: dict, bloco) -> dict:
    out["oport_calc_pos"] = bloco.oport_calc_positivacao
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


def recalc_row_formulas_only(row: dict, taxa: float) -> dict:
    """Só fórmulas da planilha — sem consulta ao banco (edição na grade)."""
    out = dict(row)
    cart = int(out.get("carteira") or 0)
    oport = int(out.get("oportunidades_mes") or 0)
    conv = _f(out, "conv_meta_pct")
    txp = _f(out, "tx_conv_projetada_pct")
    ticket = _f(out, "ticket_meta")
    rec = _f(out, "recorrencia_meta")
    manual = _f(out, "meta_manual")

    cob = round(cart * txp / 100.0) if txp > 0 and cart > 0 else 0
    if cart > 0 and cob > cart:
        cob = cart
    if cob > 0 and rec > 0:
        out["oport_calc_pos"] = round(cob * rec)
    elif conv > 0 and oport > 0:
        out["oport_calc_pos"] = round(oport * conv / 100.0)
    else:
        out["oport_calc_pos"] = 0
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
        "oport_meta": _loader_num(r, "oport_meta"),
        "meta_manual": _loader_num(r, "meta_manual"),
        "realizado_mes": float(r["realizado_mes"]),
        "participacao_empresa": r.get("participacao_empresa"),
    }
    out = recalc_row_derivados(base, ano, mes, taxa)
    return aplicar_premissa_salva(out, ano, mes, taxa)


def loader_rows_to_state(df: pd.DataFrame, ano: int, mes: int, taxa: float) -> list[dict]:
    return [row_from_loader(r.to_dict(), ano, mes, taxa) for _, r in df.iterrows()]


def aplicar_sugestoes_arredondadas(rows: list[dict], ano: int, mes: int, taxa: float) -> list[dict]:
    default_tx = round(taxa * 100.0, 0) if taxa > 0 else 90.0
    out = []
    for row in rows:
        r = dict(row)
        if _f(r, "conv_meta_pct") <= 0:
            r["conv_meta_pct"] = sugerir_pct_meta(_f(r, "tx_conv_hist_pct"))
        if _f(r, "tx_conv_projetada_pct") <= 0:
            r["tx_conv_projetada_pct"] = sugerir_tx_cobertura_projetada(
                _f(r, "cobertura_hist_pct"), default_tx
            )
        if _f(r, "ticket_meta") <= 0:
            r["ticket_meta"] = sugerir_ticket_meta(_f(r, "ticket_historico"))
        if _f(r, "recorrencia_meta") <= 0:
            r["recorrencia_meta"] = sugerir_recorrencia_meta(_f(r, "recorrencia_media"))
        out.append(recalc_row_formulas_only(r, taxa))
    return out


def editable_fields_changed(prev: list[dict], new: list[dict]) -> bool:
    n = min(len(prev), len(new))
    for i in range(n):
        for k in EDITABLE_KEYS:
            if _f(prev[i], k) != _f(new[i], k):
                return True
    return False


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

    def _sum_calc_oport() -> float:
        total = 0.0
        for _, row in d.iterrows():
            if pd.isna(row.get("conv")):
                continue
            conv = float(row["conv"])
            oport = float(row.get("oport") or 0)
            total += round(oport * conv / 100.0)
        return total

    def _sum_calc_cob() -> float:
        total = 0.0
        for _, row in d.iterrows():
            if pd.isna(row.get("tx_proj")):
                continue
            txp = float(row["tx_proj"])
            cart = float(row.get("cart") or 0)
            total += round(cart * txp / 100.0)
        return total

    def _sum_dif() -> float:
        total = 0.0
        for _, row in d.iterrows():
            if pd.isna(row.get("tx_proj")):
                continue
            txp = float(row["tx_proj"])
            cart = float(row.get("cart") or 0)
            cob = round(cart * txp / 100.0)
            if txp <= 0:
                total += 0.0
            else:
                total += max(cart - cob, 0.0)
        return total

    def _sum_meta_calc() -> float:
        total = 0.0
        for _, row in d.iterrows():
            if pd.isna(row.get("tx_proj")):
                continue
            txp = float(row["tx_proj"])
            if txp <= 0:
                continue
            cart = float(row.get("cart") or 0)
            ticket = float(row.get("ticket") or 0) if not pd.isna(row.get("ticket")) else 0.0
            rec = float(row.get("rec") or 0) if not pd.isna(row.get("rec")) else 0.0
            if ticket <= 0 or rec <= 0:
                continue
            cob = round(cart * txp / 100.0)
            total += round(ticket * rec * cob)
        return total

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

    tx_oport = (oport_calc / oport * 100.0) if oport > 0 else 0.0
    conv_vals = pd.to_numeric(d.get("conv"), errors="coerce").fillna(0)
    conv_media = float(conv_vals.mean()) if len(conv_vals) else 0.0
    tx_cob_media = (cob_media / cart * 100.0) if cart > 0 else 0.0
    tx_proj = float(pd.to_numeric(d.get("tx_proj"), errors="coerce").fillna(0).mean())

    return {
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
        "ticket_hist": None,
        "ticket": None,
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

    tx_oport = (oport_calc / oport * 100.0) if oport > 0 else 0.0
    conv_vals = pd.to_numeric(d.get("Conversão"), errors="coerce").fillna(0)
    conv_media = float(conv_vals.mean()) if len(conv_vals) else 0.0
    tx_cob_media = (cob_media / cart * 100.0) if cart > 0 else 0.0
    tx_proj = float(pd.to_numeric(d.get("TX conv. projetada"), errors="coerce").fillna(0).mean())

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
        cob_val = int(_f(r, "cobertura_meta_clientes")) if txp > 0 and cart > 0 else None
        ocalc = int(round(_f(r, "oport_calc_pos"))) if conv > 0 else None
        dif_val = int(_f(r, "diff_carteira_cob")) if txp > 0 else None
        meta_c = int(round(_f(r, "meta_formula"))) if ticket > 0 and rec > 0 and txp > 0 else None
        data.append(
            {
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
                "ticket_hist": round(_f(r, "ticket_historico"), 0),
                "ticket": round(ticket, 0) or None,
                "rec_media": round(_f(r, "recorrencia_media"), 1),
                "rec": round(rec, 1) or None,
                "peso_3m": _f(r, "peso_fat_3m_pct") or None,
                "meta_prop": round(_f(r, "meta_prop_mes_rs"), 0) or None,
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
                "meta_man": round(_f(r, "meta_manual"), 0) or None,
                "realizado": round(_f(r, "realizado_mes"), 0),
            }
        )
    cols = [fld for fld, _ in AGGRID_FIELD_LABELS]
    return pd.DataFrame(data, columns=cols)


def patch_rows_from_editor(prev_rows: list[dict], edited: pd.DataFrame) -> list[dict]:
    if "Colaborador" in edited.columns:
        edited = edited[edited["Colaborador"].astype(str).str.upper() != "TOTAL"].reset_index(drop=True)
    out = []
    n = min(len(prev_rows), len(edited))
    for i in range(n):
        base = dict(prev_rows[i])
        row = edited.iloc[i]
        for key, label in EDITABLE_LABELS.items():
            base[key] = _f(row, label)
        out.append(base)
    return out


def patch_rows_from_aggrid(prev_rows: list[dict], edited: pd.DataFrame) -> list[dict]:
    if "colab" in edited.columns:
        edited = edited[edited["colab"].astype(str).str.upper() != "TOTAL"].reset_index(drop=True)
    elif "Colaborador" in edited.columns:
        return patch_rows_from_editor(prev_rows, edited)
    out = []
    n = min(len(prev_rows), len(edited))
    for i in range(n):
        base = dict(prev_rows[i])
        row = edited.iloc[i]
        for key, field in AGGRID_KEY_TO_FIELD.items():
            base[key] = _f(row, field)
        out.append(base)
    return out


def rows_from_aggrid_df(prev_rows: list[dict], agdf: pd.DataFrame, taxa: float) -> list[dict]:
    if agdf is not None and "colab" in agdf.columns:
        patched = patch_rows_from_aggrid(prev_rows, agdf)
    else:
        patched = patch_rows_from_editor(prev_rows, agdf)
    return [recalc_row_formulas_only(p, taxa) for p in patched]
