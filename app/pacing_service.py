"""Monta ritmo (faturamento + cobertura) para um vendedor."""

from __future__ import annotations

from typing import Any

from app.data import load_vendedor_realizado_intervalo
from app.dates_util import month_bounds
from app.pacing import (
    PacingCob,
    PacingFat,
    pacing_cobertura_acumulada,
    pacing_cobertura_janela,
    pacing_faturamento_acumulado,
    pacing_faturamento_janela,
    pacing_faturamento_mensal,
)
from app.pacing_ui import PacingView

Metrics = dict[str, Any]


def _is_cumulativo(modo_ref: str, view: PacingView) -> bool:
    return modo_ref == "Real" and view.lente in ("Semanal", "Diário")


def meta_periodo_display(
    meta_mes_prescrita: float,
    modo: str,
    lente: str,
    pacing_fat: PacingFat,
) -> float:
    if modo == "Real" and lente in ("Semanal", "Diário"):
        if meta_mes_prescrita > 0 and pacing_fat.meta_mes > 0:
            return meta_mes_prescrita * (
                pacing_fat.meta_periodo_planejada / pacing_fat.meta_mes
            )
        return pacing_fat.meta_periodo_planejada
    if modo == "Real":
        if meta_mes_prescrita <= 0 or pacing_fat.meta_mes <= 0:
            return pacing_fat.meta_periodo_real
        scale = meta_mes_prescrita / pacing_fat.meta_mes
        return pacing_fat.meta_periodo_real * scale
    if lente == "Mensal":
        return meta_mes_prescrita
    if meta_mes_prescrita > 0 and pacing_fat.meta_mes > 0:
        return meta_mes_prescrita * (pacing_fat.meta_periodo_planejada / pacing_fat.meta_mes)
    return pacing_fat.meta_periodo_planejada


def _get_metrics(
    vendedor_id: int,
    ini,
    fim,
    cache: dict[tuple[int, str, str], Metrics] | None,
) -> Metrics:
    if cache is not None:
        key = (vendedor_id, ini.isoformat(), fim.isoformat())
        if key in cache:
            return cache[key]
    return load_vendedor_realizado_intervalo(vendedor_id, ini, fim)


def build_pacing_fat(
    meta_mes: float,
    view: PacingView,
    vendedor_id: int,
    modo_ref: str = "Calculada",
    metrics_cache: dict[tuple[int, str, str], Metrics] | None = None,
) -> PacingFat:
    m_ini, m_fim = month_bounds(view.selected_day.year, view.selected_day.month)

    if view.lente == "Mensal":
        mes = _get_metrics(vendedor_id, m_ini, m_fim, metrics_cache)
        return pacing_faturamento_mensal(meta_mes, float(mes["faturamento"]))

    if _is_cumulativo(modo_ref, view):
        acum = _get_metrics(vendedor_id, m_ini, view.fim_exclusive, metrics_cache)
        return pacing_faturamento_acumulado(meta_mes, float(acum["faturamento"]), view.peso_acum)

    periodo = _get_metrics(vendedor_id, view.ini, view.fim_exclusive, metrics_cache)
    return pacing_faturamento_janela(meta_mes, float(periodo["faturamento"]), view.peso_periodo)


def build_pacing_fat_equipe(
    meta_mes: float,
    view: PacingView,
    vendedor_ids: list[int],
    modo_ref: str = "Calculada",
    metrics_cache: dict[tuple[int, str, str], Metrics] | None = None,
) -> PacingFat:
    m_ini, m_fim = month_bounds(view.selected_day.year, view.selected_day.month)

    def sum_metric(ini, fim, field: str) -> float:
        total = 0.0
        for vid in vendedor_ids:
            total += float(_get_metrics(vid, ini, fim, metrics_cache)[field])
        return total

    if view.lente == "Mensal":
        return pacing_faturamento_mensal(meta_mes, sum_metric(m_ini, m_fim, "faturamento"))

    if _is_cumulativo(modo_ref, view):
        return pacing_faturamento_acumulado(
            meta_mes,
            sum_metric(m_ini, view.fim_exclusive, "faturamento"),
            view.peso_acum,
        )

    return pacing_faturamento_janela(
        meta_mes,
        sum_metric(view.ini, view.fim_exclusive, "faturamento"),
        view.peso_periodo,
    )


def build_pacing_cob(
    meta_mes_clientes: int,
    view: PacingView,
    vendedor_id: int,
    modo_ref: str = "Calculada",
    metrics_cache: dict[tuple[int, str, str], Metrics] | None = None,
) -> PacingCob:
    m_ini, m_fim = month_bounds(view.selected_day.year, view.selected_day.month)

    if view.lente == "Mensal":
        mes = _get_metrics(vendedor_id, m_ini, m_fim, metrics_cache)
        return pacing_cobertura_acumulada(meta_mes_clientes, int(mes["clientes"]), 1.0)

    if _is_cumulativo(modo_ref, view):
        acum = _get_metrics(vendedor_id, m_ini, view.fim_exclusive, metrics_cache)
        return pacing_cobertura_acumulada(meta_mes_clientes, int(acum["clientes"]), view.peso_acum)

    periodo = _get_metrics(vendedor_id, view.ini, view.fim_exclusive, metrics_cache)
    return pacing_cobertura_janela(meta_mes_clientes, int(periodo["clientes"]), view.peso_periodo)
