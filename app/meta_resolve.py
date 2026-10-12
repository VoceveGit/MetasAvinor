"""Escolha de meta mensal (manual / calculada / proporcional) para cards."""


def resolve_meta_mes_cob(
    meta_ref: str,
    row: dict,
    meta_man: float,
    meta_calc: float,
    carteira: int,
) -> tuple[float, str, int]:
    meta_prop = float(row.get("meta_prop_mes_rs") or 0)
    cob_meta = int(float(row.get("cobertura_meta_clientes") or 0))

    if meta_ref == "Proporcional" and meta_prop > 0:
        meta_mes = meta_prop
        meta_tipo = "proporcional"
        cob_sug = row.get("cob_prop_sug")
        if cob_sug is not None:
            cob_meta = int(cob_sug)
    elif meta_ref == "Manual":
        meta_mes = meta_man if meta_man > 0 else meta_calc
        meta_tipo = "manual"
    else:
        meta_mes = meta_calc if meta_calc > 0 else meta_man
        meta_tipo = "calculada"

    if cob_meta <= 0 and carteira > 0:
        txp = float(row.get("tx_conv_projetada_pct") or row.get("cobertura_meta_pct") or 0)
        if txp > 0:
            cob_meta = int(round(carteira * txp / 100))
    return meta_mes, meta_tipo, cob_meta
