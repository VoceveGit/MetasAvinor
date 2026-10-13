from datetime import date

import pandas as pd
import streamlit as st

from app.constants import MESES_CURTO, label_mes
from app.db import read_sql


@st.cache_data(ttl=300, show_spinner=False)
def load_vendedores() -> pd.DataFrame:
    return read_sql(
        """
        SELECT vendedor, MAX(nome) AS nome
        FROM faturamento_avinor
        WHERE vendedor > 0
        GROUP BY vendedor
        ORDER BY nome
        """
    )


@st.cache_data(ttl=300, show_spinner=False)
def load_carteira_ativos(vendedor_id: int) -> int:
    row = read_sql(
        """
        SELECT COUNT(*) AS c
        FROM base_clientes_avinor
        WHERE `Vendedor` = %s AND `Situação` = 'Ativo'
        """,
        (vendedor_id,),
    )
    return int(row.iloc[0]["c"])


def _filtros_sql(
    apenas_positivos: bool,
    excluir_sem_vendedor: bool,
    vendedor_id: int | None,
) -> tuple[str, list]:
    conditions: list[str] = []
    params: list = []
    if apenas_positivos:
        conditions.append("valor_total_faturado > 0")
    if excluir_sem_vendedor:
        conditions.append("vendedor > 0")
    if vendedor_id is not None:
        conditions.append("vendedor = %s")
        params.append(vendedor_id)
    return (" AND ".join(conditions) if conditions else "1=1"), params


@st.cache_data(ttl=300, show_spinner=False)
def load_faturamento_mensal(
    anos: tuple[int, ...],
    vendedor_id: int | None,
    apenas_positivos: bool,
    excluir_sem_vendedor: bool,
) -> pd.DataFrame:
    extra, params = _filtros_sql(apenas_positivos, excluir_sem_vendedor, vendedor_id)
    df = read_sql(
        f"""
        SELECT
            YEAR(data) AS ano,
            MONTH(data) AS mes,
            SUM(valor_total_faturado) AS faturamento,
            COUNT(DISTINCT cliente) AS clientes,
            COUNT(DISTINCT CONCAT(serie, '-', numero)) AS notas
        FROM faturamento_avinor
        WHERE YEAR(data) IN ({",".join(str(a) for a in anos)}) AND {extra}
        GROUP BY YEAR(data), MONTH(data)
        ORDER BY ano, mes
        """,
        tuple(params) if params else None,
    )
    df["mes_label"] = df["mes"].map(MESES_CURTO)
    return df


@st.cache_data(ttl=300, show_spinner=False)
def load_resumo_ano(
    ano: int,
    vendedor_id: int | None,
    apenas_positivos: bool,
    excluir_sem_vendedor: bool,
) -> dict:
    extra, params = _filtros_sql(apenas_positivos, excluir_sem_vendedor, vendedor_id)
    params = [ano] + params
    row = read_sql(
        f"""
        SELECT
            COALESCE(SUM(valor_total_faturado), 0) AS faturamento,
            COUNT(DISTINCT cliente) AS clientes,
            COUNT(DISTINCT CONCAT(serie, '-', numero)) AS notas
        FROM faturamento_avinor
        WHERE YEAR(data) = %s AND {extra}
        """,
        tuple(params),
    ).iloc[0]
    fat = float(row["faturamento"])
    notas = int(row["notas"]) or 1
    clientes = int(row["clientes"]) or 1
    return {
        "faturamento": fat,
        "clientes": clientes,
        "notas": int(row["notas"]),
        "ticket_nota": fat / notas,
        "ticket_cliente": fat / clientes,
    }


@st.cache_data(ttl=300, show_spinner=False)
def load_resumo_periodo(
    inicio: date,
    fim_exclusive: date,
    vendedor_id: int | None,
    apenas_positivos: bool,
    excluir_sem_vendedor: bool,
) -> dict:
    extra, params = _filtros_sql(apenas_positivos, excluir_sem_vendedor, vendedor_id)
    params = [inicio.isoformat(), fim_exclusive.isoformat()] + params
    row = read_sql(
        f"""
        SELECT
            COALESCE(SUM(valor_total_faturado), 0) AS faturamento,
            COUNT(DISTINCT cliente) AS clientes,
            COUNT(DISTINCT CONCAT(serie, '-', numero)) AS notas
        FROM faturamento_avinor
        WHERE data >= %s AND data < %s AND {extra}
        """,
        tuple(params),
    ).iloc[0]
    fat = float(row["faturamento"])
    notas = int(row["notas"]) or 1
    clientes = int(row["clientes"]) or 1
    cob = clientes
    conv = (notas / cob) if cob else 0
    return {
        "faturamento": fat,
        "clientes": clientes,
        "notas": int(row["notas"]),
        "ticket_nota": fat / notas,
        "conversao_proxy": min(conv / 5.0, 1.0) if conv else 0,
    }


@st.cache_data(ttl=300, show_spinner=False)
def load_faturamento_diario_mes(
    ano: int,
    mes: int,
    vendedor_id: int | None,
    apenas_positivos: bool,
    excluir_sem_vendedor: bool,
) -> pd.DataFrame:
    """Faturamento por dia no mês (para evolução acumulada na Visão geral)."""
    from app.dates_util import month_bounds

    ini, fim = month_bounds(ano, mes)
    extra, params = _filtros_sql(apenas_positivos, excluir_sem_vendedor, vendedor_id)
    params = [ini.isoformat(), fim.isoformat()] + params
    return read_sql(
        f"""
        SELECT
            DATE(data) AS dia,
            COALESCE(SUM(valor_total_faturado), 0) AS faturamento
        FROM faturamento_avinor
        WHERE data >= %s AND data < %s AND {extra}
        GROUP BY DATE(data)
        ORDER BY dia
        """,
        tuple(params),
    )


_CARTEIRA_JOIN = """
INNER JOIN base_clientes_avinor b
    ON b.`Cliente` = f.cliente
   AND b.`Vendedor` = f.vendedor
   AND b.`Situação` = 'Ativo'
"""


@st.cache_data(ttl=1800, show_spinner=False)
def _load_vendedores_meses_lote(ano: int, mes_meta: int, qtd: int = 3) -> dict[int, pd.DataFrame]:
    """Histórico mensal de todos os vendedores numa query só (evita uma conexão por vendedor)."""
    df = read_sql(
        f"""
        SELECT
            f.vendedor AS vendedor,
            YEAR(f.data) AS ano,
            MONTH(f.data) AS mes,
            COALESCE(SUM(f.valor_produto), 0) AS faturamento,
            COUNT(DISTINCT f.cliente) AS clientes,
            COUNT(DISTINCT CONCAT(f.serie, '-', f.numero)) AS positivacao,
            COUNT(DISTINCT CONCAT(f.serie, '-', f.numero)) AS notas
        FROM faturamento_avinor f
        {_CARTEIRA_JOIN}
        WHERE f.valor_total_faturado > 0
          AND f.data >= DATE_SUB(DATE(CONCAT(%s, '-', %s, '-01')), INTERVAL %s MONTH)
          AND f.data < DATE(CONCAT(%s, '-', %s, '-01'))
        GROUP BY f.vendedor, YEAR(f.data), MONTH(f.data)
        ORDER BY vendedor, ano, mes
        """,
        (ano, mes_meta, qtd, ano, mes_meta),
    )
    if df.empty:
        return {}
    return {
        int(vid): g.drop(columns=["vendedor"]).reset_index(drop=True)
        for vid, g in df.groupby("vendedor")
    }


@st.cache_data(ttl=1800, show_spinner=False)
def crescimento_ticket_lote(ano: int, mes_meta: int) -> tuple[dict[int, tuple[float, float]], float | None]:
    """Ticket (fat ÷ notas) dos 3 meses fechados vs os mesmos 3 meses do ano anterior.

    Retorna ({vendedor: (ticket_atual, ticket_ano_anterior)}, crescimento da equipe ou None).
    """
    atual = _load_vendedores_meses_lote(ano, mes_meta, 3)
    antes = _load_vendedores_meses_lote(ano - 1, mes_meta, 3)

    def _tk(df: pd.DataFrame | None) -> float:
        if df is None or df.empty:
            return 0.0
        n = float(df["positivacao"].sum())
        return float(df["faturamento"].sum()) / n if n > 0 else 0.0

    por = {vid: (_tk(df), _tk(antes.get(vid))) for vid, df in atual.items()}
    eq_a = _tk(pd.concat(atual.values())) if atual else 0.0
    eq_b = _tk(pd.concat(antes.values())) if antes else 0.0
    return por, (eq_a / eq_b - 1) if eq_a > 0 and eq_b > 0 else None


@st.cache_data(ttl=300, show_spinner=False)
def load_vendedor_meses(vendedor_id: int, ano: int, mes_meta: int, qtd: int = 3) -> pd.DataFrame:
    """
    Histórico dos `qtd` meses fechados antes de `mes_meta`, só com clientes da carteira ativa.
    Positivação = notas fiscais (cada venda conta uma vez, mesmo com vários itens).
    """
    lote = _load_vendedores_meses_lote(ano, mes_meta, qtd)
    df = lote.get(int(vendedor_id))
    if df is None or df.empty:
        return pd.DataFrame(columns=["ano", "mes", "faturamento", "clientes", "positivacao", "notas"])
    df = df.copy()
    df["periodo"] = df.apply(lambda r: label_mes(int(r["ano"]), int(r["mes"])), axis=1)
    df["ticket"] = df["faturamento"] / df["positivacao"].replace(0, pd.NA)
    df["recorrencia"] = df["positivacao"] / df["clientes"].replace(0, pd.NA)
    return df


@st.cache_data(ttl=300, show_spinner=False)
def load_faturamento_vendedores_janela(inicio: date, fim_exclusive: date) -> pd.DataFrame:
    """Faturamento por vendedor em [inicio, fim_exclusive)."""
    return read_sql(
        """
        SELECT
            vendedor,
            COALESCE(SUM(valor_total_faturado), 0) AS faturamento
        FROM faturamento_avinor
        WHERE valor_total_faturado > 0
          AND data >= %s AND data < %s
        GROUP BY vendedor
        """,
        (inicio, fim_exclusive),
    )


@st.cache_data(ttl=600, show_spinner=False)
def load_fat_empresa_mensal(anos: tuple[int, ...]) -> dict[tuple[int, int], float]:
    """Faturamento da empresa por (ano, mês) — base do plano anual e da sazonalidade."""
    if not anos:
        return {}
    df = read_sql(
        f"""
        SELECT YEAR(data) AS ano, MONTH(data) AS mes,
               COALESCE(SUM(valor_total_faturado), 0) AS faturamento
        FROM faturamento_avinor
        WHERE valor_total_faturado > 0
          AND YEAR(data) IN ({",".join(str(int(a)) for a in anos)})
        GROUP BY YEAR(data), MONTH(data)
        """
    )
    return {(int(r.ano), int(r.mes)): float(r.faturamento or 0) for r in df.itertuples()}


@st.cache_data(ttl=300, show_spinner=False)
def load_fat_vendedor_mes_ano(ano: int) -> dict[tuple[int, int], float]:
    """Faturamento por (vendedor, mês) no ano — uma query para a compensação."""
    df = read_sql(
        """
        SELECT vendedor, MONTH(data) AS mes,
               COALESCE(SUM(valor_total_faturado), 0) AS faturamento
        FROM faturamento_avinor
        WHERE valor_total_faturado > 0 AND vendedor > 0
          AND data >= %s AND data < %s
        GROUP BY vendedor, MONTH(data)
        """,
        (date(ano, 1, 1).isoformat(), date(ano + 1, 1, 1).isoformat()),
    )
    return {(int(r.vendedor), int(r.mes)): float(r.faturamento or 0) for r in df.itertuples()}


@st.cache_data(ttl=300, show_spinner=False)
def load_metricas_vendedor_trimestre(vendedor_id: int, ano: int, mes_meta: int) -> dict:
    """Médias dos 3 meses fechados antes do mês da meta."""
    df = load_vendedor_meses(vendedor_id, ano, mes_meta, 3)
    if df.empty:
        return {
            "fat_media": 0,
            "cob_media": 0,
            "pos_media": 0,
            "ticket": 0,
            "recorrencia": 0,
            "meses": df,
        }
    fat_media = float(df["faturamento"].mean())
    cob_media = float(df["clientes"].mean())
    pos_media = float(df["positivacao"].mean())
    ticket = fat_media / pos_media if pos_media else 0
    rec = pos_media / cob_media if cob_media else 0
    return {
        "fat_media": fat_media,
        "cob_media": cob_media,
        "pos_media": pos_media,
        "ticket": ticket,
        "recorrencia": rec,
        "meses": df,
    }


def calc_meta_sugerida(
    carteira: int,
    taxa_cobertura: float,
    ticket: float,
    recorrencia: float,
) -> float:
    cobertura = carteira * taxa_cobertura
    return ticket * recorrencia * cobertura


@st.cache_data(ttl=300, show_spinner=False)
def load_meta_vs_realizado_historico(
    vendedor_id: int,
    ano: int,
    mes_ref: int,
    taxa: float,
    meses_atras: int = 3,
) -> pd.DataFrame:
    rows = []
    carteira = load_carteira_ativos(vendedor_id)
    y, m = ano, mes_ref
    for _ in range(meses_atras):
        m -= 1
        if m < 1:
            m = 12
            y -= 1
        hist = load_metricas_vendedor_trimestre(vendedor_id, y, m)
        meta = calc_meta_sugerida(
            carteira,
            taxa,
            hist["ticket"] or 0,
            hist["recorrencia"] or 0,
        )
        real = read_sql(
            """
            SELECT COALESCE(SUM(valor_total_faturado), 0) AS fat
            FROM faturamento_avinor
            WHERE vendedor = %s AND valor_total_faturado > 0
              AND YEAR(data) = %s AND MONTH(data) = %s
            """,
            (vendedor_id, y, m),
        ).iloc[0]["fat"]
        real = float(real)
        rows.append(
            {
                "periodo": label_mes(y, m),
                "ano": y,
                "mes": m,
                "meta_sugerida": meta,
                "realizado": real,
                "atingimento": (real / meta * 100) if meta > 0 else 0,
                "bateu": real >= meta if meta > 0 else False,
            }
        )
    return pd.DataFrame(rows)


@st.cache_data(ttl=300, show_spinner=False)
def load_ranking_periodo(inicio: date, fim_exclusive: date, limit: int = 50) -> pd.DataFrame:
    df = read_sql(
        """
        SELECT
            vendedor,
            MAX(nome) AS nome,
            SUM(valor_total_faturado) AS faturamento,
            COUNT(DISTINCT cliente) AS clientes,
            COUNT(DISTINCT CONCAT(serie, '-', numero)) AS notas
        FROM faturamento_avinor
        WHERE data >= %s AND data < %s
          AND valor_total_faturado > 0 AND vendedor > 0
        GROUP BY vendedor
        ORDER BY faturamento DESC
        LIMIT %s
        """,
        (inicio.isoformat(), fim_exclusive.isoformat(), limit),
    )
    if df.empty:
        return df
    total = float(df["faturamento"].sum()) or 1.0
    df["pct_faturamento"] = df["faturamento"] / total * 100
    df["tx_recorrencia"] = df["notas"] / df["clientes"].replace(0, pd.NA)
    carteiras = read_sql(
        """
        SELECT `Vendedor` AS vendedor, COUNT(*) AS carteira
        FROM base_clientes_avinor
        WHERE `Situação` = 'Ativo'
        GROUP BY `Vendedor`
        """
    )
    df = df.merge(carteiras, on="vendedor", how="left")
    df["carteira"] = df["carteira"].fillna(0)
    df["tx_cobertura"] = (df["clientes"] / df["carteira"].replace(0, pd.NA)).clip(upper=1.0)
    return df


@st.cache_data(ttl=300, show_spinner=False)
def load_vendedor_realizado_intervalo(
    vendedor_id: int,
    inicio: date,
    fim_exclusive: date,
) -> dict:
    """Faturamento, clientes e notas no intervalo [inicio, fim_exclusive)."""
    row = read_sql(
        """
        SELECT
            COALESCE(SUM(valor_total_faturado), 0) AS faturamento,
            COUNT(DISTINCT cliente) AS clientes,
            COUNT(DISTINCT CONCAT(serie, '-', numero)) AS notas
        FROM faturamento_avinor
        WHERE vendedor = %s
          AND data >= %s AND data < %s
          AND valor_total_faturado > 0
        """,
        (vendedor_id, inicio.isoformat(), fim_exclusive.isoformat()),
    )
    if row.empty:
        return {"faturamento": 0.0, "clientes": 0, "notas": 0}
    r = row.iloc[0]
    return {
        "faturamento": float(r["faturamento"] or 0),
        "clientes": int(r["clientes"] or 0),
        "notas": int(r["notas"] or 0),
    }


@st.cache_data(ttl=300, show_spinner=False)
def load_realizado_vendedores_batch(
    vendedor_ids: tuple[int, ...],
    inicio: date,
    fim_exclusive: date,
) -> dict[int, dict]:
    """Agregado por vendedor no intervalo — uma query para o ranking inteiro."""
    if not vendedor_ids:
        return {}
    placeholders = ", ".join(["%s"] * len(vendedor_ids))
    params: list = list(vendedor_ids) + [inicio.isoformat(), fim_exclusive.isoformat()]
    df = read_sql(
        f"""
        SELECT
            vendedor,
            COALESCE(SUM(valor_total_faturado), 0) AS faturamento,
            COUNT(DISTINCT cliente) AS clientes,
            COUNT(DISTINCT CONCAT(serie, '-', numero)) AS notas
        FROM faturamento_avinor
        WHERE vendedor IN ({placeholders})
          AND data >= %s AND data < %s
          AND valor_total_faturado > 0
        GROUP BY vendedor
        """,
        tuple(params),
    )
    out: dict[int, dict] = {
        int(v): {"faturamento": 0.0, "clientes": 0, "notas": 0} for v in vendedor_ids
    }
    for r in df.itertuples():
        out[int(r.vendedor)] = {
            "faturamento": float(r.faturamento or 0),
            "clientes": int(r.clientes or 0),
            "notas": int(r.notas or 0),
        }
    return out


@st.cache_data(ttl=300, show_spinner=False)
def load_realizado_dia(vendedor_id: int, dia: date) -> float:
    row = read_sql(
        """
        SELECT COALESCE(SUM(valor_total_faturado), 0) AS fat
        FROM faturamento_avinor
        WHERE vendedor = %s AND valor_total_faturado > 0
          AND DATE(data) = %s
        """,
        (vendedor_id, dia.isoformat()),
    )
    return float(row.iloc[0]["fat"])


@st.cache_data(ttl=300, show_spinner=False)
def load_carteira_clientes(vendedor_id: int, limit: int = 150) -> pd.DataFrame:
    return read_sql(
        """
        SELECT
            bc.Cliente AS cliente,
            bc.`Nome Fantasia` AS nome,
            bc.Cidade AS cidade,
            bc.UF AS uf,
            bc.`Situação` AS situacao,
            agg.ultima_compra,
            ult.valor_ultima_nota,
            agg.faturamento_total
        FROM base_clientes_avinor bc
        LEFT JOIN (
            SELECT
                cliente,
                MAX(data) AS ultima_compra,
                SUM(valor_total_faturado) AS faturamento_total
            FROM faturamento_avinor
            WHERE vendedor = %s AND valor_total_faturado > 0
            GROUP BY cliente
        ) agg ON agg.cliente = bc.Cliente
        LEFT JOIN (
            SELECT f.cliente, f.data, SUM(f.valor_total_faturado) AS valor_ultima_nota
            FROM faturamento_avinor f
            INNER JOIN (
                SELECT cliente, MAX(data) AS md
                FROM faturamento_avinor
                WHERE vendedor = %s AND valor_total_faturado > 0
                GROUP BY cliente
            ) u ON u.cliente = f.cliente AND u.md = f.data
            WHERE f.vendedor = %s
            GROUP BY f.cliente, f.data
        ) ult ON ult.cliente = bc.Cliente
        WHERE bc.`Vendedor` = %s
        ORDER BY agg.ultima_compra DESC
        LIMIT %s
        """,
        (vendedor_id, vendedor_id, vendedor_id, vendedor_id, limit),
    )


@st.cache_data(ttl=300, show_spinner=False)
def load_realizado_mes(vendedor_id: int, ano: int, mes: int) -> dict:
    row = read_sql(
        """
        SELECT
            COALESCE(SUM(valor_total_faturado), 0) AS fat,
            COUNT(DISTINCT cliente) AS clientes,
            COUNT(DISTINCT CONCAT(serie, '-', numero)) AS notas
        FROM faturamento_avinor
        WHERE vendedor = %s AND valor_total_faturado > 0
          AND YEAR(data) = %s AND MONTH(data) = %s
        """,
        (vendedor_id, ano, mes),
    ).iloc[0]
    return {
        "faturamento": float(row["fat"]),
        "clientes": int(row["clientes"]),
        "notas": int(row["notas"]),
    }


@st.cache_data(ttl=300, show_spinner=False)
def build_linhas_historico_meses(
    vendedor_id: int,
    ano: int,
    mes_ref: int,
    taxa: float,
) -> pd.DataFrame:
    """Últimos 3 meses fechados antes do mês de referência, com meta sugerida e realizado."""
    carteira = load_carteira_ativos(vendedor_id)
    rows = []
    y, m = ano, mes_ref
    for _ in range(3):
        m -= 1
        if m < 1:
            m = 12
            y -= 1
        hist = load_metricas_vendedor_trimestre(vendedor_id, y, m)
        meta = calc_meta_sugerida(
            carteira, taxa, hist["ticket"] or 0, hist["recorrencia"] or 0
        )
        real = load_realizado_mes(vendedor_id, y, m)
        fat = real["faturamento"]
        ating = (fat / meta * 100) if meta > 0 else 0
        rows.append(
            {
                "periodo": label_mes(y, m),
                "clientes": real["clientes"],
                "notas": real["notas"],
                "faturamento": fat,
                "meta_sugerida": meta,
                "atingimento": ating,
                "bateu": fat >= meta if meta > 0 else False,
            }
        )
    return pd.DataFrame(rows).iloc[::-1].reset_index(drop=True)


@st.cache_data(ttl=300, show_spinner=False)
def load_oportunidades_rotas_equipe() -> pd.DataFrame:
    """Oportunidades/mês por vendedor (planilha ROTAS AVINOR × carteira ativa)."""
    from app.rotas_oportunidades import build_oportunidades_por_vendedor

    return build_oportunidades_por_vendedor()


def _oportunidades_rotas_vendedor(vendedor_id: int) -> int | None:
    df = load_oportunidades_rotas_equipe()
    row = df.loc[df["vendedor"] == vendedor_id]
    if row.empty:
        return None
    return int(row.iloc[0]["oportunidades_mes"])


@st.cache_data(ttl=300, show_spinner=False)
def load_oportunidades_por_vendedor() -> pd.DataFrame:
    """Negócios em pipeline Vendas ainda em aberto (grupo P), por código de vendedor."""
    return read_sql(
        """
        SELECT bc.`Vendedor` AS vendedor,
               COUNT(DISTINCT d.id) AS oportunidades
        FROM deals_avinor d
        INNER JOIN base_clientes_avinor bc
          ON bc.Cliente = CAST(d.empresa AS UNSIGNED)
        WHERE d.pipeline = 'Vendas'
          AND d.grupo_de_fase = 'P'
          AND d.empresa REGEXP '^[0-9]+$'
        GROUP BY bc.`Vendedor`
        """
    )


@st.cache_data(ttl=120, show_spinner=False)
def load_historico_meta_vendedor(
    vendedor_id: int,
    ano: int,
    mes: int,
    taxa: float,
) -> pd.DataFrame:
    carteira = load_carteira_ativos(vendedor_id)
    hist = load_metricas_vendedor_trimestre(vendedor_id, ano, mes)
    meta_calc = calc_meta_sugerida(
        carteira, taxa, hist["ticket"] or 0, hist["recorrencia"] or 0
    )
    linhas = build_linhas_historico_meses(vendedor_id, ano, mes, taxa)
    real_mes = load_realizado_mes(vendedor_id, ano, mes)
    ating_mes = (real_mes["faturamento"] / meta_calc * 100) if meta_calc > 0 else 0
    linha_atual = pd.DataFrame(
        [
            {
                "periodo": f"{label_mes(ano, mes)} (em andamento)",
                "clientes": real_mes["clientes"],
                "notas": real_mes["notas"],
                "faturamento": real_mes["faturamento"],
                "meta_sugerida": meta_calc,
                "atingimento": ating_mes,
                "bateu": real_mes["faturamento"] >= meta_calc if meta_calc > 0 else False,
            }
        ]
    )
    return pd.concat([linhas, linha_atual], ignore_index=True)


@st.cache_data(ttl=300, show_spinner=False)
def load_panorama_metas_equipe(
    ano: int,
    mes: int,
    taxa: float,
    limit: int = 40,
) -> pd.DataFrame:
    from app.dates_util import month_bounds

    ini, fim = month_bounds(ano, mes)
    ranking = load_ranking_periodo(ini, fim, limit)
    if ranking.empty:
        return ranking

    from app.meta_frigosol import montar_bloco_frigosol
    from app.premissas import get_premissa

    oport_df = load_oportunidades_rotas_equipe()
    oport_map = (
        dict(zip(oport_df["vendedor"].astype(int), oport_df["oportunidades_mes"].astype(int)))
        if not oport_df.empty
        else {}
    )

    rows = []
    for r in ranking.itertuples():
        hist = load_metricas_vendedor_trimestre(r.vendedor, ano, mes)
        cart = int(r.carteira) if pd.notna(r.carteira) else load_carteira_ativos(r.vendedor)
        prem = get_premissa(r.vendedor, ano, mes)
        clientes_mes = int(r.clientes)
        oport_rotas = oport_map.get(int(r.vendedor))
        bloco = montar_bloco_frigosol(
            cart, hist, prem, taxa, clientes_mes, oportunidades_rotas=oport_rotas
        )
        meta = bloco.meta_faturamento
        real = float(r.faturamento)
        ating = (real / meta * 100) if meta > 0 else 0
        cob_media_pct = (bloco.cobertura_media_3m / cart * 100) if cart > 0 else None
        tx_cob_mes = float(r.tx_cobertura) * 100 if pd.notna(r.tx_cobertura) else None
        rows.append(
            {
                "vendedor": r.vendedor,
                "nome": r.nome,
                "carteira": cart,
                "oportunidades": bloco.oportunidades_mes,
                "tx_conv_oport": bloco.tx_conv_oport_hist * 100,
                "conversao_meta": bloco.conversao_meta * 100,
                "oport_calc_pos": bloco.oport_calc_positivacao,
                "cob_media_3m": bloco.cobertura_media_3m,
                "cob_media_pct": cob_media_pct,
                "cobertura_meta": bloco.cobertura_meta,
                "cobertura_qtd": clientes_mes,
                "cobertura_pct_mes": tx_cob_mes,
                "diff_carteira_cob": bloco.diff_carteira_cobertura,
                "ticket_meta": bloco.ticket_meta,
                "recorrencia": bloco.recorrencia_meta,
                "recorrencia_hist": bloco.recorrencia_media,
                "clientes": clientes_mes,
                "meta_sugerida": meta,
                "meta_formula": bloco.meta_formula,
                "realizado": real,
                "atingimento": min(ating, 999),
                "progresso": min(ating, 100),
                "bateu": real >= meta if meta > 0 else False,
                "oport_estimada": bloco.oportunidades_estimada,
                "oport_fonte_rotas": bloco.oportunidades_fonte_rotas,
            }
        )
    return pd.DataFrame(rows)


@st.cache_data(ttl=300, show_spinner=False)
def load_equipe_mes(ano: int, mes: int, limit: int) -> pd.DataFrame:
    """Quem vendeu no mês da meta ou nos 3 meses fechados antes (mês futuro também tem equipe)."""
    from app.dates_util import month_bounds, three_months_prior_bounds

    ini, fim = month_bounds(ano, mes)
    h_ini, h_fim = three_months_prior_bounds(ano, mes)
    mes_df = load_ranking_periodo(ini, fim, limit)
    hist_df = load_ranking_periodo(h_ini, h_fim, limit)
    if hist_df.empty:
        return mes_df
    novos = hist_df[~hist_df["vendedor"].isin(mes_df["vendedor"] if not mes_df.empty else [])].copy()
    for col in ("faturamento", "clientes", "notas", "pct_faturamento", "tx_recorrencia", "tx_cobertura"):
        if col in novos.columns:
            novos[col] = 0
    out = pd.concat([mes_df, novos], ignore_index=True) if not mes_df.empty else novos
    return out.head(limit).reset_index(drop=True)


@st.cache_data(ttl=300, show_spinner=False)
def load_grid_metas_colaboradores(
    ano: int,
    mes: int,
    taxa: float,
    limit: int = 80,
) -> pd.DataFrame:
    """Tabela estilo planilha Mari: histórico 3m + colunas editáveis (meta esperada)."""
    from app.indicadores_vendedor import calc_indicadores_3m
    from app.meta_frigosol import montar_bloco_frigosol
    from app.plano_metas import meta_empresa_mes
    from app.premissas import get_premissa

    ranking = load_equipe_mes(ano, mes, limit)
    if ranking.empty:
        return ranking

    meta_emp = meta_empresa_mes(ano, mes)

    oport_df = load_oportunidades_rotas_equipe()
    oport_map = (
        dict(zip(oport_df["vendedor"].astype(int), oport_df["oportunidades_mes"].astype(int)))
        if not oport_df.empty
        else {}
    )

    rows = []
    for r in ranking.itertuples():
        vid = int(r.vendedor)
        hist = load_metricas_vendedor_trimestre(vid, ano, mes)
        cart = int(r.carteira) if pd.notna(r.carteira) else load_carteira_ativos(vid)
        clientes_mes = int(r.clientes)
        oport_rotas = oport_map.get(vid)
        prem = get_premissa(vid, ano, mes)
        ind = calc_indicadores_3m(vid, ano, mes, cart, oport_rotas)
        bloco = montar_bloco_frigosol(
            cart, hist, prem, taxa, clientes_mes, oportunidades_rotas=oport_rotas
        )
        manual = (
            float(prem.meta_faturamento_rs)
            if prem.usar_meta_oficial_rs and prem.meta_faturamento_rs > 0
            else None
        )

        tx_proj = prem.tx_conv_projetada_pct if prem.tx_conv_projetada_pct > 0 else prem.cobertura_meta_pct

        rows.append(
            {
                "vendedor": vid,
                "nome": r.nome,
                "carteira": cart,
                "oportunidades_mes": ind["oportunidades_mes"],
                "oport_media_3m": ind["oportunidades_media_3m"],
                "tx_conv_hist_pct": ind["tx_conv_oport_hist_pct"],
                "conv_meta_pct": prem.conversao_meta_pct if prem.conversao_meta_pct > 0 else None,
                "oport_calc_pos": bloco.oport_calc_positivacao,
                "cob_media_clientes_3m": ind["cobertura_media_clientes_3m"],
                "cobertura_hist_pct": ind["cobertura_hist_pct"],
                "tx_conv_projetada_pct": tx_proj if tx_proj > 0 else None,
                "cobertura_meta_pct": tx_proj if tx_proj > 0 else None,
                "diff_carteira_cob": bloco.diff_carteira_cobertura,
                "ticket_historico": ind["ticket_historico"],
                "ticket_meta": prem.ticket_meta if prem.ticket_meta > 0 else None,
                "fat_media_3m": ind["faturamento_media_3m"],
                "positivacao_media_3m": ind["positivacao_media_3m"],
                "recorrencia_media": ind["recorrencia_media"],
                "recorrencia_meta": prem.meta_recorrencia if prem.meta_recorrencia > 0 else None,
                "meta_formula": bloco.meta_formula,
                "meta_efetiva": bloco.meta_faturamento,
                "meta_manual": manual,
                "oport_meta": prem.oportunidades_mes if prem.oportunidades_mes > 0 else None,
                "realizado_mes": float(r.faturamento),
                "clientes_mes": clientes_mes,
            }
        )

    df = pd.DataFrame(rows)
    soma_sug = float(df["meta_formula"].sum()) or 0
    if meta_emp > 0 and soma_sug > 0:
        df["participacao_empresa"] = df["meta_formula"] / soma_sug * meta_emp
    else:
        df["participacao_empresa"] = pd.NA
    return df


def meta_vendedor_periodo_mes(
    vendedor_id: int,
    ano: int,
    mes: int,
    taxa: float,
    faturamento_mes: float | None = None,
    carteira: int | None = None,
    clientes_mes: int | None = None,
) -> float:
    """Meta em R$ do mês: premissa salva ou motor (histórico + rotas), como no panorama."""
    from app.meta_frigosol import montar_bloco_frigosol
    from app.premissas import get_premissa

    hist = load_metricas_vendedor_trimestre(vendedor_id, ano, mes)
    cart = carteira if carteira is not None else load_carteira_ativos(vendedor_id)
    prem = get_premissa(vendedor_id, ano, mes)
    oport_df = load_oportunidades_rotas_equipe()
    oport_rotas = None
    if not oport_df.empty:
        row = oport_df.loc[oport_df["vendedor"] == vendedor_id]
        if not row.empty:
            oport_rotas = int(row.iloc[0]["oportunidades_mes"])
    bloco = montar_bloco_frigosol(
        int(cart),
        hist,
        prem,
        taxa,
        clientes_mes,
        oportunidades_rotas=oport_rotas,
    )
    return float(bloco.meta_faturamento)


@st.cache_data(ttl=300, show_spinner=False)
def load_top_vendedores_mes(ano: int, mes: int, limit: int = 50) -> pd.DataFrame:
    from app.dates_util import month_bounds

    ini, fim = month_bounds(ano, mes)
    return load_ranking_periodo(ini, fim, limit)


def _filtro_vendedor_sql(
    vendedor_id: int | None,
    col: str = "vendedor",
) -> tuple[str, list]:
    if vendedor_id is None:
        return "", []
    return f" AND {col} = %s", [vendedor_id]


def _filtro_vendedores_in_sql(
    vendedor_ids: tuple[int, ...],
    col: str = "f.vendedor",
) -> tuple[str, list]:
    if not vendedor_ids:
        return " AND 1=0 ", []
    placeholders = ",".join(["%s"] * len(vendedor_ids))
    return f" AND {col} IN ({placeholders}) ", list(vendedor_ids)


@st.cache_data(ttl=300, show_spinner=False)
def load_faturamento_por_familia(
    inicio: date,
    fim_exclusive: date,
    vendedor_id: int | None = None,
) -> pd.DataFrame:
    extra, params = _filtro_vendedor_sql(vendedor_id)
    params = [inicio.isoformat(), fim_exclusive.isoformat()] + params
    df = read_sql(
        f"""
        SELECT
            COALESCE(NULLIF(TRIM(familia), ''), 'Sem família') AS familia,
            SUM(valor_produto) AS faturamento,
            SUM(COALESCE(peso, 0)) AS peso_kg,
            COUNT(DISTINCT CONCAT(serie, '-', numero)) AS notas,
            COUNT(DISTINCT cliente) AS clientes
        FROM faturamento_avinor
        WHERE data >= %s AND data < %s
          AND valor_produto > 0
          {extra}
        GROUP BY familia
        ORDER BY faturamento DESC
        """,
        tuple(params),
    )
    total = float(df["faturamento"].sum()) or 1.0
    df["pct"] = df["faturamento"] / total * 100
    return df


@st.cache_data(ttl=300, show_spinner=False)
def load_faturamento_top_produtos(
    inicio: date,
    fim_exclusive: date,
    vendedor_id: int | None = None,
    limit: int = 25,
) -> pd.DataFrame:
    extra, params = _filtro_vendedor_sql(vendedor_id)
    params = [inicio.isoformat(), fim_exclusive.isoformat()] + params + [limit]
    df = read_sql(
        f"""
        SELECT
            produto AS codigo,
            COALESCE(NULLIF(TRIM(descricao), ''), 'Sem descrição') AS produto,
            COALESCE(NULLIF(TRIM(familia), ''), 'Sem família') AS familia,
            SUM(valor_produto) AS faturamento,
            SUM(COALESCE(peso, 0)) AS peso_kg,
            COUNT(DISTINCT CONCAT(serie, '-', numero)) AS notas
        FROM faturamento_avinor
        WHERE data >= %s AND data < %s
          AND valor_produto > 0
          {extra}
        GROUP BY produto, descricao, familia
        ORDER BY faturamento DESC
        LIMIT %s
        """,
        tuple(params),
    )
    total = float(df["faturamento"].sum()) or 1.0
    df["pct"] = df["faturamento"] / total * 100
    return df


@st.cache_data(ttl=300, show_spinner=False)
def load_tops_ranking_batch(
    vendedor_ids: tuple[int, ...],
    inicio: date,
    fim_exclusive: date,
    limit_per: int = 3,
) -> tuple[dict[int, list], dict[int, list], dict[int, list]]:
    """
    Top clientes, produtos e cidades por vendedor em uma consulta cada (ROW_NUMBER).
    Cada lista: tuplas (rótulo, detalhe) prontas para HTML do card.
    """
    if not vendedor_ids:
        return {}, {}, {}

    extra, vparams = _filtro_vendedores_in_sql(vendedor_ids, "f.vendedor")
    base_dates = [inicio.isoformat(), fim_exclusive.isoformat()]

    cli_df = read_sql(
        f"""
        SELECT vendedor, cliente, nome, faturamento, notas FROM (
            SELECT
                agg.vendedor,
                agg.cliente,
                agg.nome,
                agg.faturamento,
                agg.notas,
                ROW_NUMBER() OVER (
                    PARTITION BY agg.vendedor ORDER BY agg.faturamento DESC
                ) AS rn
            FROM (
                SELECT
                    f.vendedor,
                    f.cliente,
                    MAX(
                        COALESCE(
                            NULLIF(TRIM(bc.`Nome Fantasia`), ''),
                            NULLIF(TRIM(bc.Nome), ''),
                            CONCAT('Cliente ', f.cliente)
                        )
                    ) AS nome,
                    SUM(f.valor_total_faturado) AS faturamento,
                    COUNT(DISTINCT CONCAT(f.serie, '-', f.numero)) AS notas
                FROM faturamento_avinor f
                LEFT JOIN base_clientes_avinor bc ON bc.Cliente = f.cliente
                WHERE f.data >= %s AND f.data < %s
                  AND f.valor_total_faturado > 0
                  {extra}
                GROUP BY f.vendedor, f.cliente
            ) agg
        ) ranked
        WHERE rn <= %s
        """,
        tuple(base_dates + vparams + [limit_per]),
    )

    prod_df = read_sql(
        f"""
        SELECT vendedor, produto, faturamento FROM (
            SELECT
                agg.vendedor,
                agg.produto,
                agg.faturamento,
                ROW_NUMBER() OVER (
                    PARTITION BY agg.vendedor ORDER BY agg.faturamento DESC
                ) AS rn
            FROM (
                SELECT
                    f.vendedor,
                    COALESCE(NULLIF(TRIM(f.descricao), ''), 'Sem descrição') AS produto,
                    SUM(f.valor_produto) AS faturamento
                FROM faturamento_avinor f
                WHERE f.data >= %s AND f.data < %s
                  AND f.valor_produto > 0
                  {extra}
                GROUP BY f.vendedor, COALESCE(NULLIF(TRIM(f.descricao), ''), 'Sem descrição')
            ) agg
        ) ranked
        WHERE rn <= %s
        """,
        tuple(base_dates + vparams + [limit_per]),
    )

    cid_df = read_sql(
        f"""
        SELECT vendedor, cidade, uf, faturamento FROM (
            SELECT
                agg.vendedor,
                agg.cidade,
                agg.uf,
                agg.faturamento,
                ROW_NUMBER() OVER (
                    PARTITION BY agg.vendedor ORDER BY agg.faturamento DESC
                ) AS rn
            FROM (
                SELECT
                    f.vendedor,
                    UPPER(TRIM(bc.Cidade)) AS cidade,
                    UPPER(TRIM(bc.UF)) AS uf,
                    SUM(f.valor_total_faturado) AS faturamento
                FROM faturamento_avinor f
                INNER JOIN base_clientes_avinor bc ON bc.Cliente = f.cliente
                WHERE f.data >= %s AND f.data < %s
                  AND f.valor_total_faturado > 0
                  AND bc.Cidade IS NOT NULL AND TRIM(bc.Cidade) <> ''
                  {extra}
                GROUP BY f.vendedor, UPPER(TRIM(bc.Cidade)), UPPER(TRIM(bc.UF))
            ) agg
        ) ranked
        WHERE rn <= %s
        """,
        tuple(base_dates + vparams + [limit_per]),
    )

    from app.formatting import fmt_brl_cell

    tops_cli: dict[int, list] = {}
    if not cli_df.empty:
        for r in cli_df.itertuples():
            tops_cli.setdefault(int(r.vendedor), []).append(
                (
                    str(r.nome),
                    f"{fmt_brl_cell(float(r.faturamento))} · {int(r.notas)} notas",
                )
            )

    tops_prod: dict[int, list] = {}
    if not prod_df.empty:
        for r in prod_df.itertuples():
            tops_prod.setdefault(int(r.vendedor), []).append(
                (str(r.produto), fmt_brl_cell(float(r.faturamento)))
            )

    tops_cid: dict[int, list] = {}
    if not cid_df.empty:
        for r in cid_df.itertuples():
            label = f"{r.cidade}/{r.uf}" if r.uf else str(r.cidade)
            tops_cid.setdefault(int(r.vendedor), []).append(
                (label, fmt_brl_cell(float(r.faturamento)))
            )

    return tops_cli, tops_prod, tops_cid


@st.cache_data(ttl=300, show_spinner=False)
def load_faturamento_top_clientes(
    inicio: date,
    fim_exclusive: date,
    vendedor_id: int,
    limit: int = 3,
) -> pd.DataFrame:
    """Top clientes por faturamento no período (vendedor)."""
    df = read_sql(
        """
        SELECT
            f.cliente,
            MAX(
                COALESCE(
                    NULLIF(TRIM(bc.`Nome Fantasia`), ''),
                    NULLIF(TRIM(bc.Nome), ''),
                    CONCAT('Cliente ', f.cliente)
                )
            ) AS nome,
            SUM(f.valor_total_faturado) AS faturamento,
            COUNT(DISTINCT CONCAT(f.serie, '-', f.numero)) AS notas
        FROM faturamento_avinor f
        LEFT JOIN base_clientes_avinor bc ON bc.Cliente = f.cliente
        WHERE f.data >= %s AND f.data < %s
          AND f.valor_total_faturado > 0
          AND f.vendedor = %s
        GROUP BY f.cliente
        ORDER BY faturamento DESC
        LIMIT %s
        """,
        (inicio.isoformat(), fim_exclusive.isoformat(), vendedor_id, limit),
    )
    return df


@st.cache_data(ttl=300, show_spinner=False)
def load_recorrencia_por_cidade(
    inicio: date,
    fim_exclusive: date,
    vendedor_id: int | None = None,
    limit: int = 80,
) -> pd.DataFrame:
    """Faturamento e recorrência (notas ÷ clientes) por cidade do cadastro do cliente."""
    extra, params = _filtro_vendedor_sql(vendedor_id, "f.vendedor")
    params = [inicio.isoformat(), fim_exclusive.isoformat()] + params + [limit]
    df = read_sql(
        f"""
        SELECT
            UPPER(TRIM(bc.Cidade)) AS cidade,
            UPPER(TRIM(bc.UF)) AS uf,
            COUNT(DISTINCT f.cliente) AS clientes,
            COUNT(DISTINCT CONCAT(f.serie, '-', f.numero)) AS notas,
            SUM(f.valor_total_faturado) AS faturamento
        FROM faturamento_avinor f
        INNER JOIN base_clientes_avinor bc ON bc.Cliente = f.cliente
        WHERE f.data >= %s AND f.data < %s
          AND f.valor_total_faturado > 0
          AND bc.Cidade IS NOT NULL AND TRIM(bc.Cidade) <> ''
          {extra}
        GROUP BY UPPER(TRIM(bc.Cidade)), UPPER(TRIM(bc.UF))
        ORDER BY faturamento DESC
        LIMIT %s
        """,
        tuple(params),
    )
    if df.empty:
        return df
    df["recorrencia"] = df["notas"] / df["clientes"].replace(0, pd.NA)
    total = float(df["faturamento"].sum()) or 1.0
    df["pct_faturamento"] = df["faturamento"] / total * 100
    return df


@st.cache_data(ttl=300, show_spinner=False)
def load_preco_medio_produto_vendedor(
    inicio: date,
    fim_exclusive: date,
    limit: int = 50,
    vendedor_id: int | None = None,
    only_below_team: bool = True,
) -> pd.DataFrame:
    """Preço médio por vendedor/produto vs média da equipe (peso como quantidade)."""
    vend_filter = ""
    params: list = [inicio.isoformat(), fim_exclusive.isoformat()]
    if vendedor_id is not None:
        vend_filter = " AND f.vendedor = %s"
        params.append(vendedor_id)

    base = read_sql(
        f"""
        SELECT
            f.vendedor,
            MAX(f.nome) AS nome,
            COALESCE(NULLIF(TRIM(f.descricao), ''), CAST(f.produto AS CHAR)) AS produto,
            SUM(f.valor_produto) AS faturamento,
            SUM(ABS(COALESCE(f.peso, 0))) AS qtd,
            COUNT(DISTINCT CONCAT(f.serie, '-', f.numero)) AS notas
        FROM faturamento_avinor f
        WHERE f.data >= %s AND f.data < %s
          AND f.valor_produto > 0
          AND f.vendedor > 0
          {vend_filter}
        GROUP BY f.vendedor, COALESCE(NULLIF(TRIM(f.descricao), ''), CAST(f.produto AS CHAR))
        HAVING qtd > 0
        """,
        tuple(params),
    )
    if base.empty:
        return base
    base["preco_vendedor"] = base["faturamento"] / base["qtd"]
    equipe = base.groupby("produto", as_index=False).agg(
        fat_eq=("faturamento", "sum"),
        qtd_eq=("qtd", "sum"),
    )
    equipe["preco_equipe"] = equipe["fat_eq"] / equipe["qtd_eq"]
    merged = base.merge(equipe[["produto", "preco_equipe"]], on="produto", how="left")
    merged["desvio_pct"] = (
        (merged["preco_vendedor"] - merged["preco_equipe"]) / merged["preco_equipe"] * 100
    )
    merged = merged.sort_values("desvio_pct")
    if only_below_team:
        merged = merged.loc[merged["desvio_pct"] < -1]
    if vendedor_id is None:
        merged = merged.head(limit)
    return merged[
        [
            "vendedor",
            "nome",
            "produto",
            "preco_vendedor",
            "preco_equipe",
            "desvio_pct",
            "faturamento",
            "notas",
        ]
    ]


@st.cache_data(ttl=3600, show_spinner="Buscando clientes parados…")
def load_clientes_parados(hoje: date, meses: int = 6) -> pd.DataFrame:
    """Uma consulta: compras por cliente/mês nos últimos `meses`.

    Retorna 1 linha por cliente (vendedor = quem fez a última venda) com última compra,
    dias sem comprar e média mensal dos 3 meses até a última compra.
    """
    y, m = hoje.year, hoje.month - meses
    while m <= 0:
        m += 12
        y -= 1
    ini = date(y, m, 1)
    df = read_sql(
        """
        SELECT
            a.vendedor, a.vendedor_nome, a.cliente, a.mi, a.ult, a.fat,
            COALESCE(
                NULLIF(TRIM(bc.`Nome Fantasia`), ''),
                NULLIF(TRIM(bc.Nome), ''),
                CONCAT('Cliente ', a.cliente)
            ) AS cliente_nome,
            UPPER(TRIM(bc.Cidade)) AS cidade
        FROM (
            SELECT
                f.vendedor,
                MAX(f.nome) AS vendedor_nome,
                f.cliente,
                YEAR(f.data) * 12 + MONTH(f.data) AS mi,
                MAX(f.data) AS ult,
                SUM(f.valor_total_faturado) AS fat
            FROM faturamento_avinor f
            WHERE f.data >= %s AND f.data <= %s
              AND f.valor_total_faturado > 0
              AND f.vendedor > 0
            GROUP BY f.vendedor, f.cliente, YEAR(f.data) * 12 + MONTH(f.data)
        ) a
        LEFT JOIN base_clientes_avinor bc ON bc.Cliente = a.cliente
        """,
        (ini.isoformat(), hoje.isoformat()),
    )
    cols = ["vendedor", "vendedor_nome", "cliente", "cliente_nome", "cidade", "ult", "dias", "media_3m"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    df = df.drop_duplicates(["vendedor", "cliente", "mi"])
    df["ult"] = pd.to_datetime(df["ult"]).dt.date
    df["fat"] = df["fat"].astype(float)
    df = df.sort_values("ult")
    last = df.groupby("cliente", as_index=False).last()
    mi_last = last.set_index("cliente")["mi"]
    df["mi_last"] = df["cliente"].map(mi_last)
    janela = df[df["mi"] > df["mi_last"] - 3]
    media = janela.groupby("cliente")["fat"].sum() / 3.0
    last["media_3m"] = last["cliente"].map(media).fillna(0.0)
    last["dias"] = last["ult"].map(lambda d: (hoje - d).days)
    return last[cols].reset_index(drop=True)
