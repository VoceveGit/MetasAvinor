from datetime import date, timedelta


def three_months_prior_bounds(ano: int, mes: int) -> tuple[date, date]:
    """Três meses completos imediatamente anteriores ao mês de meta [início, fim)."""
    y, m = ano, mes - 3
    while m < 1:
        m += 12
        y -= 1
    return date(y, m, 1), date(ano, mes, 1)


def month_bounds(ano: int, mes: int) -> tuple[date, date]:
    start = date(ano, mes, 1)
    if mes == 12:
        end = date(ano + 1, 1, 1)
    else:
        end = date(ano, mes + 1, 1)
    return start, end


def week_bounds(d: date) -> tuple[date, date]:
    start = d - timedelta(days=d.weekday())
    end = start + timedelta(days=7)
    return start, end


def business_days_between(inicio: date, fim_exclusive: date) -> int:
    """Dias úteis (seg–sex) em [inicio, fim_exclusive)."""
    d = inicio
    n = 0
    while d < fim_exclusive:
        if d.weekday() < 5:
            n += 1
        d += timedelta(days=1)
    return n


def business_days_in_month(ano: int, mes: int) -> int:
    start, end = month_bounds(ano, mes)
    return business_days_between(start, end)


def dias_uteis_intervalo(inicio: date, fim_exclusive: date) -> list[date]:
    """Dias úteis (seg–sex) em [inicio, fim_exclusive)."""
    out: list[date] = []
    d = inicio
    while d < fim_exclusive:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def semanas_mes(ano: int, mes: int) -> list[tuple[date, date]]:
    """Semanas (seg–dom) do mês, cortadas nas bordas: [(início, fim exclusivo)]."""
    ini, fim = month_bounds(ano, mes)
    out: list[tuple[date, date]] = []
    d = ini
    while d < fim:
        nxt = min(d - timedelta(days=d.weekday()) + timedelta(days=7), fim)
        out.append((d, nxt))
        d = nxt
    return out


def semana_do_mes(d: date) -> int:
    """Índice 0-based da semana do mês que contém d."""
    semanas = semanas_mes(d.year, d.month)
    for i, (a, b) in enumerate(semanas):
        if a <= d < b:
            return i
    return max(len(semanas) - 1, 0)


def business_days_elapsed_in_month(ano: int, mes: int, ref: date | None = None) -> int:
    ref = ref or date.today()
    start, end = month_bounds(ano, mes)
    if ref < start:
        return 0
    limit = min(ref, end - timedelta(days=1))
    d = start
    n = 0
    while d <= limit:
        if d.weekday() < 5:
            n += 1
        d += timedelta(days=1)
    return n
