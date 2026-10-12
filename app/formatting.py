def fmt_brl_table(value: float | int | None, decimals: int = 0) -> str:
    """Tabelas: sempre R$ com milhar BR (ex.: R$ 812.632). Vazio/None → —."""
    if value is None:
        return "—"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "—"
    if v != v:  # NaN
        return "—"
    if abs(v) < 0.5 and decimals == 0:
        return "—"
    neg = v < 0
    v = abs(v)
    if decimals > 0:
        s = f"{v:,.{decimals}f}"
    else:
        s = f"{int(round(v)):,}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"-R$ {s}" if neg else f"R$ {s}"


def fmt_pct_table(value: float | int | None, decimals: int = 1) -> str:
    if value is None or (isinstance(value, float) and value != value):
        return "—"
    return f"{float(value):.{decimals}f}%"


def fmt_int_table(value: float | int | None) -> str:
    if value is None or (isinstance(value, float) and value != value):
        return "—"
    return f"{int(round(float(value))):,}".replace(",", ".")


def fmt_brl_cell(value: float | int | None) -> str:
    if value is None or (isinstance(value, float) and value != value):
        return "—"
    v = float(value)
    neg = v < 0
    v = abs(v)
    if v >= 1_000_000:
        s = f"R$ {v/1_000_000:,.2f} mi"
    elif v >= 1_000:
        s = f"R$ {v:,.0f}"
    else:
        s = f"R$ {v:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"-{s}" if neg else s


def fmt_pct(value: float | None) -> str:
    if value is None or (isinstance(value, float) and value != value):
        return "—"
    return f"{float(value):.0f}%"
