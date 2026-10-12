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


def business_days_in_month(ano: int, mes: int) -> int:
    start, end = month_bounds(ano, mes)
    d = start
    n = 0
    while d < end:
        if d.weekday() < 5:
            n += 1
        d += timedelta(days=1)
    return n


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
