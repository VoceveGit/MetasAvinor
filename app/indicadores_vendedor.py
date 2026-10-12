from __future__ import annotations

from app.data import load_metricas_vendedor_trimestre
from app.meta_frigosol import estimate_oportunidades_mes


def calc_indicadores_3m(
    vendedor_id: int,
    ano: int,
    mes: int,
    carteira: int,
    oportunidades_mes_ref: int | None,
) -> dict:
    """
    Indicadores dos 3 meses fechados antes do mês de referência — mesmas contas da aba PAINEL (Frigosol).
    """
    hist = load_metricas_vendedor_trimestre(vendedor_id, ano, mes)
    oport_mes = (
        int(oportunidades_mes_ref)
        if oportunidades_mes_ref is not None and oportunidades_mes_ref >= 0
        else estimate_oportunidades_mes(carteira)
    )

    cob_media = float(hist.get("cob_media") or 0)
    pos_media = float(hist.get("pos_media") or 0)
    fat_media = float(hist.get("fat_media") or 0)
    rec_media = float(hist.get("recorrencia") or 0)
    if rec_media <= 0 and cob_media > 0 and pos_media > 0:
        rec_media = pos_media / cob_media

    tx_conv_oport_hist_pct = (pos_media / oport_mes * 100.0) if oport_mes > 0 else 0.0
    cobertura_hist_pct = (cob_media / carteira * 100.0) if carteira > 0 else 0.0
    ticket_historico = (fat_media / pos_media) if pos_media > 0 else 0.0

    return {
        "oportunidades_mes": oport_mes,
        "oportunidades_media_3m": float(oport_mes),
        "tx_conv_oport_hist_pct": tx_conv_oport_hist_pct,
        "cobertura_hist_pct": cobertura_hist_pct,
        "cobertura_media_clientes_3m": cob_media,
        "faturamento_media_3m": fat_media,
        "positivacao_media_3m": pos_media,
        "recorrencia_media": rec_media,
        "ticket_historico": ticket_historico,
    }
