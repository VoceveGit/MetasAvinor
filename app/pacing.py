"""Ritmo mensal → semanal/diário (meta prescrita + ajuste 'Real')."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from app.dates_util import month_bounds


@dataclass(frozen=True)
class MonthWeek:
    index: int
    ini: date
    fim_exclusive: date
    label: str

    @property
    def ini_day(self) -> int:
        return self.ini.day

    @property
    def fim_day(self) -> int:
        return self.fim_exclusive.day - 1


def weeks_in_month(ano: int, mes: int) -> list[MonthWeek]:
    """Semanas do mês: 01–07, 08–14, … (blocos de 7 a partir do dia 1)."""
    start, end = month_bounds(ano, mes)
    n_days = (end - start).days
    blocks: list[MonthWeek] = []
    day = 1
    idx = 0
    while day <= n_days:
        d_ini = date(ano, mes, day)
        d_end_day = min(day + 6, n_days)
        d_fim = date(ano, mes, d_end_day) + timedelta(days=1)
        blocks.append(
            MonthWeek(
                index=idx,
                ini=d_ini,
                fim_exclusive=d_fim,
                label=f"Semana {idx + 1} · {day:02d} a {d_end_day:02d}",
            )
        )
        day += 7
        idx += 1
    return blocks


def week_for_date(ano: int, mes: int, d: date) -> MonthWeek:
    weeks = weeks_in_month(ano, mes)
    for w in weeks:
        if w.ini <= d < w.fim_exclusive:
            return w
    return weeks[-1]


def days_in_month(ano: int, mes: int) -> int:
    start, end = month_bounds(ano, mes)
    return (end - start).days


def day_bounds(ano: int, mes: int, day: int) -> tuple[date, date]:
    d = date(ano, mes, day)
    return d, d + timedelta(days=1)


@dataclass
class PacingFat:
    meta_mes: float
    meta_periodo_planejada: float
    meta_periodo_real: float
    realizado_periodo: float
    realizado_mes_acum_antes: float
    gap_acum_antes: float
    falta_periodo: float
    ating_pct: float
    ajuste_label: str
    ajuste_tone: str  # ok | behind | ahead


@dataclass
class PacingCob:
    meta_mes_clientes: int
    meta_periodo_planejada: float
    meta_periodo_real: float
    clientes_periodo: int
    ating_pct: float
    ajuste_label: str
    ajuste_tone: str


def _ajuste_meta(
    meta_mes: float,
    n_periods: int,
    period_index: int,
    realizado_antes: float,
) -> tuple[float, float, float, str, str]:
    """Retorna planejada, real ajustada, gap antes, label, tone."""
    if meta_mes <= 0 or n_periods <= 0:
        return 0.0, 0.0, 0.0, "", "ok"
    planejada = meta_mes / n_periods
    deveria_ate = period_index * planejada
    gap = realizado_antes - deveria_ate
    restantes = max(n_periods - period_index, 1)
    meta_real = planejada + (-gap / restantes)
    if abs(gap) < 1:
        label = "No ritmo do mês"
        tone = "ok"
    elif gap < 0:
        label = f"A recuperar no mês: {abs(gap):,.0f} R$".replace(",", ".")
        tone = "behind"
    else:
        label = f"Folga acumulada: {gap:,.0f} R$".replace(",", ".")
        tone = "ahead"
    return planejada, max(meta_real, 0.0), gap, label, tone


def pacing_faturamento_mensal(meta_mes: float, realizado_mes: float) -> PacingFat:
    ating = (realizado_mes / meta_mes * 100) if meta_mes > 0 else 0.0
    falta = max(meta_mes - realizado_mes, 0.0)
    return PacingFat(
        meta_mes=meta_mes,
        meta_periodo_planejada=meta_mes,
        meta_periodo_real=meta_mes,
        realizado_periodo=realizado_mes,
        realizado_mes_acum_antes=0.0,
        gap_acum_antes=0.0,
        falta_periodo=falta,
        ating_pct=min(ating, 999.0),
        ajuste_label="Visão do mês inteiro",
        ajuste_tone="ok",
    )


def pacing_faturamento_semana(
    meta_mes: float,
    realizado_periodo: float,
    realizado_antes: float,
    week: MonthWeek,
    n_weeks: int,
) -> PacingFat:
    planejada, meta_real, gap, label, tone = _ajuste_meta(
        meta_mes, n_weeks, week.index, realizado_antes
    )
    meta_uso = meta_real
    ating = (realizado_periodo / meta_uso * 100) if meta_uso > 0 else 0.0
    falta = max(meta_uso - realizado_periodo, 0.0)
    return PacingFat(
        meta_mes=meta_mes,
        meta_periodo_planejada=planejada,
        meta_periodo_real=meta_real,
        realizado_periodo=realizado_periodo,
        realizado_mes_acum_antes=realizado_antes,
        gap_acum_antes=gap,
        falta_periodo=falta,
        ating_pct=min(ating, 999.0),
        ajuste_label=label,
        ajuste_tone=tone,
    )


def pacing_faturamento_dia(
    meta_mes: float,
    realizado_periodo: float,
    realizado_antes: float,
    day_index: int,
    n_days: int,
) -> PacingFat:
    planejada, meta_real, gap, label, tone = _ajuste_meta(
        meta_mes, n_days, day_index, realizado_antes
    )
    meta_uso = meta_real
    ating = (realizado_periodo / meta_uso * 100) if meta_uso > 0 else 0.0
    falta = max(meta_uso - realizado_periodo, 0.0)
    return PacingFat(
        meta_mes=meta_mes,
        meta_periodo_planejada=planejada,
        meta_periodo_real=meta_real,
        realizado_periodo=realizado_periodo,
        realizado_mes_acum_antes=realizado_antes,
        gap_acum_antes=gap,
        falta_periodo=falta,
        ating_pct=min(ating, 999.0),
        ajuste_label=label,
        ajuste_tone=tone,
    )


def pacing_faturamento_janela(
    meta_mes: float,
    realizado_janela: float,
    peso_periodo: float,
) -> PacingFat:
    """Somente o período (ex.: semana 2 isolada); peso = fração de dias úteis do mês."""
    planejada = meta_mes * max(peso_periodo, 0.0)
    ating = (realizado_janela / planejada * 100) if planejada > 0 else 0.0
    falta = max(planejada - realizado_janela, 0.0)
    return PacingFat(
        meta_mes=meta_mes,
        meta_periodo_planejada=planejada,
        meta_periodo_real=planejada,
        realizado_periodo=realizado_janela,
        realizado_mes_acum_antes=0.0,
        gap_acum_antes=0.0,
        falta_periodo=falta,
        ating_pct=min(ating, 999.0),
        ajuste_label="Somente este período",
        ajuste_tone="ok",
    )


def pacing_faturamento_acumulado(
    meta_mes: float,
    realizado_acum: float,
    peso_acum: float,
) -> PacingFat:
    """Do dia 1 até o fim do período selecionado; peso = fração de dias úteis já cobertos."""
    meta_acum = meta_mes * max(peso_acum, 0.0)
    gap = realizado_acum - meta_acum
    falta = max(meta_acum - realizado_acum, 0.0)
    ating = (realizado_acum / meta_acum * 100) if meta_acum > 0 else 0.0
    if abs(gap) < 1:
        label = "Acumulado no ritmo do mês"
        tone = "ok"
    elif gap < 0:
        label = f"Acumulado: faltam {falta:,.0f} R$ até aqui".replace(",", ".")
        tone = "behind"
    else:
        label = f"Acumulado: folga de {gap:,.0f} R$".replace(",", ".")
        tone = "ahead"
    return PacingFat(
        meta_mes=meta_mes,
        meta_periodo_planejada=meta_acum,
        meta_periodo_real=meta_acum,
        realizado_periodo=realizado_acum,
        realizado_mes_acum_antes=0.0,
        gap_acum_antes=gap,
        falta_periodo=falta,
        ating_pct=min(ating, 999.0),
        ajuste_label=label,
        ajuste_tone=tone,
    )


def pacing_cobertura_janela(
    meta_mes_clientes: int,
    clientes_janela: int,
    peso_periodo: float,
) -> PacingCob:
    meta_j = float(meta_mes_clientes) * max(peso_periodo, 0.0)
    ating = (clientes_janela / meta_j * 100) if meta_j > 0 else 0.0
    return PacingCob(
        meta_mes_clientes=meta_mes_clientes,
        meta_periodo_planejada=meta_j,
        meta_periodo_real=meta_j,
        clientes_periodo=clientes_janela,
        ating_pct=min(ating, 999.0),
        ajuste_label="Somente este período",
        ajuste_tone="ok",
    )


def pacing_cobertura_acumulada(
    meta_mes_clientes: int,
    clientes_acum: int,
    peso_acum: float,
) -> PacingCob:
    meta_acum = float(meta_mes_clientes) * max(peso_acum, 0.0)
    gap = clientes_acum - meta_acum
    ating = (clientes_acum / meta_acum * 100) if meta_acum > 0 else 0.0
    if abs(gap) < 0.5:
        label = "Clientes acumulados no ritmo"
        tone = "ok"
    elif gap < 0:
        label = f"Acumulado: faltam {int(round(meta_acum - clientes_acum))} clientes"
        tone = "behind"
    else:
        label = f"Acumulado: folga de {int(round(gap))} clientes"
        tone = "ahead"
    return PacingCob(
        meta_mes_clientes=meta_mes_clientes,
        meta_periodo_planejada=meta_acum,
        meta_periodo_real=meta_acum,
        clientes_periodo=clientes_acum,
        ating_pct=min(ating, 999.0),
        ajuste_label=label,
        ajuste_tone=tone,
    )


def pacing_cobertura(
    meta_mes_clientes: int,
    clientes_periodo: int,
    clientes_antes: int,
    period_index: int,
    n_periods: int,
) -> PacingCob:
    if meta_mes_clientes <= 0 or n_periods <= 0:
        return PacingCob(0, 0.0, 0.0, clientes_periodo, 0.0, "", "ok")
    planejada_f, meta_real_f, gap, label, tone = _ajuste_meta(
        float(meta_mes_clientes), n_periods, period_index, float(clientes_antes)
    )
    meta_uso = meta_real_f
    ating = (clientes_periodo / meta_uso * 100) if meta_uso > 0 else 0.0
    return PacingCob(
        meta_mes_clientes=meta_mes_clientes,
        meta_periodo_planejada=planejada_f,
        meta_periodo_real=meta_real_f,
        clientes_periodo=clientes_periodo,
        ating_pct=min(ating, 999.0),
        ajuste_label=label,
        ajuste_tone=tone,
    )
