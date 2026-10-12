"""Meta empresa proporcional ao histórico de faturamento (3 meses)."""

from __future__ import annotations

from app.data import load_faturamento_vendedores_janela
from app.dates_util import business_days_in_month, three_months_prior_bounds
from app.pacing import weeks_in_month
from app.premissas import PremissaEmpresa


def meta_empresa_mensal_ref(emp: PremissaEmpresa) -> float:
    """Mensal de referência: meta anual ÷ 12, senão meta mensal salva."""
    anual = float(emp.meta_empresa_anual_rs or 0)
    if anual > 0:
        return anual / 12.0
    return float(emp.meta_empresa_rs or 0)


def pesos_faturamento_3m(ano: int, mes: int, vendedor_ids: list[int]) -> dict[int, float]:
    """Peso 0–1 por vendedor (soma = 1 entre os IDs informados com fat > 0)."""
    if not vendedor_ids:
        return {}
    ini, fim = three_months_prior_bounds(ano, mes)
    df = load_faturamento_vendedores_janela(ini, fim)
    if df.empty:
        return {vid: 0.0 for vid in vendedor_ids}
    fat_by_vid = {
        int(r.vendedor): float(r.faturamento or 0)
        for r in df.itertuples()
    }
    subset = {vid: fat_by_vid.get(vid, 0.0) for vid in vendedor_ids}
    total = sum(subset.values())
    if total <= 0:
        n = len(vendedor_ids)
        return {vid: 1.0 / n for vid in vendedor_ids}
    return {vid: subset[vid] / total for vid in vendedor_ids}


def _cobertura_sugerida_prop(row: dict, meta_prop: float) -> int | None:
    cart = int(row.get("carteira") or 0)
    ticket = float(row.get("ticket_historico") or 0)
    rec = float(row.get("recorrencia_media") or 0)
    if meta_prop > 0 and ticket > 0 and rec > 0:
        cob = int(round(meta_prop / (ticket * rec)))
        return min(cob, cart) if cart > 0 else cob
    cob_hist_pct = float(row.get("cobertura_hist_pct") or 0)
    if cart > 0 and cob_hist_pct > 0:
        return min(int(round(cart * cob_hist_pct / 100.0)), cart)
    cob_media = float(row.get("cob_media_clientes_3m") or 0)
    if cob_media > 0 and cart > 0:
        return min(int(round(cob_media)), cart)
    return None


def aplicar_colunas_proporcionais(
    rows: list[dict],
    ano: int,
    mes: int,
    emp: PremissaEmpresa,
) -> list[dict]:
    """Preenche peso %, meta proporcional do mês e positivação sugerida (somente leitura)."""
    meta_mes = meta_empresa_mensal_ref(emp)
    vids = [int(r["vendedor"]) for r in rows]
    pesos = pesos_faturamento_3m(ano, mes, vids)
    n_weeks = max(len(weeks_in_month(ano, mes)), 1)
    n_uteis = max(business_days_in_month(ano, mes), 1)
    out: list[dict] = []
    for row in rows:
        r = dict(row)
        vid = int(r["vendedor"])
        peso = pesos.get(vid, 0.0)
        r["peso_fat_3m_pct"] = round(peso * 100.0, 2)
        meta_prop = meta_mes * peso if meta_mes > 0 else 0.0
        r["meta_prop_mes_rs"] = round(meta_prop, 0)
        r["meta_prop_sem_rs"] = round(meta_prop / n_weeks, 0) if meta_prop > 0 else 0
        r["meta_prop_dia_rs"] = round(meta_prop / n_uteis, 0) if meta_prop > 0 else 0
        ticket = float(r.get("ticket_historico") or 0)
        r["cob_prop_sug"] = _cobertura_sugerida_prop(r, meta_prop)
        rec_meta = float(r.get("recorrencia_meta") or 0)
        rec_hist = float(r.get("recorrencia_media") or 0)
        rec_use = rec_meta if rec_meta > 0 else rec_hist
        cob_sug = r.get("cob_prop_sug")
        if cob_sug and int(cob_sug) > 0 and rec_use > 0:
            r["posit_prop_sug"] = int(round(int(cob_sug) * rec_use))
        elif meta_prop > 0 and ticket > 0:
            r["posit_prop_sug"] = int(round(meta_prop / ticket))
        else:
            r["posit_prop_sug"] = None
        out.append(r)
    return out


def enrich_row_proporcional(row: dict, ano: int, mes: int, emp: PremissaEmpresa | None = None) -> dict:
    from app.premissas import get_premissa_empresa

    emp = emp or get_premissa_empresa(ano, mes)
    return aplicar_colunas_proporcionais([row], ano, mes, emp)[0]
