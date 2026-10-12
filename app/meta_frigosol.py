from __future__ import annotations

from dataclasses import dataclass

from app.premissas import PremissaVendedor


@dataclass
class BlocoFrigosol:
    carteira: int
    oportunidades_mes: int
    oportunidades_fonte_rotas: bool
    tx_conv_oport_hist: float
    conversao_meta: float
    oport_calc_positivacao: float
    cobertura_media_3m: float
    cobertura_meta: float
    diff_carteira_cobertura: float
    faturamento_media_3m: float
    positivacao_media_3m: float
    ticket_historico: float
    ticket_meta: float
    recorrencia_media: float
    recorrencia_meta: float
    meta_faturamento: float
    meta_formula: float
    oportunidades_estimada: bool
    tx_conv_projetada_frac: float


def estimate_oportunidades_mes(carteira: int, semanas_no_mes: int = 4) -> int:
    """Frigosol: soma(dias de atendimento na semana) × ~4 semanas. Sem cadastro de dias: ~1,04 dia/sem/cliente."""
    dias_por_cliente_semana = 1.04
    return int(round(carteira * dias_por_cliente_semana * semanas_no_mes))


def _tx_cobertura_projetada_pct(prem: PremissaVendedor, taxa_cobertura: float) -> float:
    if prem.tx_conv_projetada_pct > 0:
        return float(prem.tx_conv_projetada_pct)
    if prem.cobertura_meta_pct > 0:
        return float(prem.cobertura_meta_pct)
    return float(prem.taxa_cobertura or taxa_cobertura) * 100.0


def montar_bloco_frigosol(
    carteira: int,
    hist: dict,
    prem: PremissaVendedor,
    taxa_cobertura: float,
    real_clientes_mes: int | None = None,
    oportunidades_rotas: int | None = None,
) -> BlocoFrigosol:
    fonte_rotas = False
    if prem.oportunidades_mes > 0:
        oport = int(prem.oportunidades_mes)
        oport_estimada = False
    elif oportunidades_rotas is not None and oportunidades_rotas >= 0:
        oport = int(oportunidades_rotas)
        oport_estimada = False
        fonte_rotas = True
    else:
        oport_estimada = True
        oport = estimate_oportunidades_mes(carteira)

    fat_media = float(hist.get("fat_media") or 0)
    cob_media = float(hist.get("cob_media") or 0)
    pos_media = float(hist.get("pos_media") or 0)
    rec_hist = float(hist.get("recorrencia") or 0)
    if rec_hist <= 0 and cob_media > 0 and pos_media > 0:
        rec_hist = pos_media / cob_media

    if oport > 0 and pos_media > 0:
        tx_hist = min(1.0, pos_media / oport)
        ticket_hist = fat_media / pos_media if pos_media > 0 else 0.0
    else:
        tx_hist = 0.0
        ticket_hist = float(hist.get("ticket") or 0)

    conv_meta_frac = (
        min(max(prem.conversao_meta_pct / 100.0, 0.0), 1.0)
        if prem.conversao_meta_pct > 0
        else 0.0
    )

    if prem.meta_cobertura_qtd > 0:
        cob_meta = int(round(float(prem.meta_cobertura_qtd)))
        if carteira > 0:
            cob_meta = min(cob_meta, carteira)
        tx_proj_frac = cob_meta / carteira if carteira > 0 else 0.0
    elif prem.tx_conv_projetada_pct > 0 or prem.cobertura_meta_pct > 0:
        tx_proj_pct = _tx_cobertura_projetada_pct(prem, taxa_cobertura)
        tx_proj_frac = min(max(tx_proj_pct / 100.0, 0.0), 1.0)
        cob_meta = round(carteira * tx_proj_frac) if carteira > 0 else 0
        if carteira > 0:
            cob_meta = min(int(cob_meta), carteira)
    else:
        tx_proj_frac = 0.0
        cob_meta = 0
    diff_cart = max(carteira - cob_meta, 0) if cob_meta > 0 else 0

    ticket_meta = prem.ticket_meta if prem.ticket_meta > 0 else ticket_hist
    rec_meta = prem.meta_recorrencia if prem.meta_recorrencia > 0 else rec_hist

    if cob_meta > 0 and rec_meta > 0:
        oport_calc_pos = float(cob_meta) * float(rec_meta)
    elif conv_meta_frac > 0 and oport > 0:
        oport_calc_pos = oport * conv_meta_frac
    else:
        oport_calc_pos = 0.0
    if prem.ticket_meta > 0 and prem.meta_recorrencia > 0 and cob_meta > 0:
        meta_formula = prem.ticket_meta * prem.meta_recorrencia * cob_meta
    else:
        meta_formula = 0.0
    meta_fat = (
        prem.meta_faturamento_rs
        if prem.usar_meta_oficial_rs and prem.meta_faturamento_rs > 0
        else meta_formula
    )

    return BlocoFrigosol(
        carteira=carteira,
        oportunidades_mes=oport,
        oportunidades_fonte_rotas=fonte_rotas,
        tx_conv_oport_hist=tx_hist,
        conversao_meta=conv_meta_frac,
        oport_calc_positivacao=oport_calc_pos,
        cobertura_media_3m=cob_media,
        cobertura_meta=cob_meta,
        diff_carteira_cobertura=diff_cart,
        faturamento_media_3m=fat_media,
        positivacao_media_3m=pos_media,
        ticket_historico=ticket_hist,
        ticket_meta=ticket_meta,
        recorrencia_media=rec_hist,
        recorrencia_meta=rec_meta,
        meta_faturamento=meta_fat,
        meta_formula=meta_formula,
        oportunidades_estimada=oport_estimada,
        tx_conv_projetada_frac=tx_proj_frac,
    )


def meta_faturamento_em_uso(bloco: BlocoFrigosol) -> float:
    return bloco.meta_faturamento
